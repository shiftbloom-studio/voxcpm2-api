from __future__ import annotations

import asyncio
import importlib.util
import logging
import platform
import threading
import time
from typing import AsyncIterator

import numpy as np

from voxcpm2_api.audio import to_numpy_audio
from voxcpm2_api.config import Settings
from voxcpm2_api.runtime.base import (
    BackendAvailability,
    StreamChunk,
    SynthesisBackend,
    SynthesisResult,
)
from voxcpm2_api.schemas import SynthesisRequest
from voxcpm2_api.service import PreparedAudioAssets

logger = logging.getLogger("voxcpm2_api.voxcpm")


class VoxCPMBackend(SynthesisBackend):
    name = "voxcpm"

    def __init__(self, settings: Settings):
        self._settings = settings
        self._model = None
        self._load_lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        if self._load_lock is None:
            self._load_lock = asyncio.Lock()
        return self._load_lock

    def availability(self) -> BackendAvailability:
        if not self._settings.allow_voxcpm:
            return BackendAvailability(False, "Disabled by configuration")
        if importlib.util.find_spec("voxcpm") is None:
            return BackendAvailability(
                False, "Install optional dependency: pip install -e .[voxcpm]"
            )
        return BackendAvailability(True, "Ready")

    def supports_request(self, request: SynthesisRequest) -> bool:
        return True

    async def warmup(self) -> None:
        await self._ensure_model()

    async def synthesize(
        self, request: SynthesisRequest, assets: PreparedAudioAssets
    ) -> SynthesisResult:
        model = await self._ensure_model()
        kwargs = self._build_generation_kwargs(request, assets)

        logger.info(
            "synthesis start - text=%d chars, timesteps=%s, cfg=%s, "
            "has_prompt=%s, has_reference=%s, denoise=%s, retry_badcase=%s",
            len(request.text),
            kwargs.get("inference_timesteps"),
            kwargs.get("cfg_value"),
            kwargs.get("prompt_wav_path") is not None,
            kwargs.get("reference_wav_path") is not None,
            kwargs.get("denoise"),
            kwargs.get("retry_badcase"),
        )

        def _run() -> np.ndarray:
            t0 = time.perf_counter()
            logger.info("generate() called on thread %s", threading.current_thread().name)
            waveform = model.generate(**kwargs)
            elapsed = time.perf_counter() - t0
            logger.info("generate() completed in %.2fs", elapsed)
            return to_numpy_audio(waveform)

        t_start = time.perf_counter()
        waveform = await asyncio.to_thread(_run)
        total = time.perf_counter() - t_start
        duration_s = len(waveform) / self._detect_sample_rate(model)
        logger.info(
            "synthesis done - %.2fs wall, %.2fs audio, RTF=%.2f",
            total,
            duration_s,
            total / max(duration_s, 0.01),
        )

        return SynthesisResult(
            backend=self.name,
            device=self._detect_device(model),
            sample_rate=self._detect_sample_rate(model),
            waveform=waveform,
        )

    async def stream(
        self,
        request: SynthesisRequest,
        assets: PreparedAudioAssets,
    ) -> AsyncIterator[StreamChunk]:
        model = await self._ensure_model()
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[StreamChunk | Exception | None] = asyncio.Queue(maxsize=4)
        kwargs = self._build_generation_kwargs(request, assets)

        logger.info("streaming start - text=%d chars", len(request.text))

        def _worker() -> None:
            try:
                t0 = time.perf_counter()
                for sequence, chunk in enumerate(
                    model.generate_streaming(**kwargs)
                ):
                    elapsed = time.perf_counter() - t0
                    logger.info("stream chunk %d at %.2fs", sequence, elapsed)
                    payload = StreamChunk(
                        backend=self.name,
                        device=self._detect_device(model),
                        sample_rate=self._detect_sample_rate(model),
                        sequence=sequence,
                        waveform=to_numpy_audio(chunk),
                    )
                    future = asyncio.run_coroutine_threadsafe(queue.put(payload), loop)
                    future.result()
                total = time.perf_counter() - t0
                logger.info("streaming done - %.2fs total", total)
                future = asyncio.run_coroutine_threadsafe(queue.put(None), loop)
                future.result()
            except Exception as exc:
                logger.error("streaming failed: %s", exc, exc_info=True)
                asyncio.run_coroutine_threadsafe(queue.put(exc), loop).result()

        threading.Thread(target=_worker, daemon=True).start()

        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield item

    async def _ensure_model(self):
        if self._model is not None:
            return self._model

        async with self._get_lock():
            if self._model is not None:
                return self._model

            from voxcpm import VoxCPM

            logger.info(
                "loading model - source=%s, optimize=%s, denoiser=%s",
                self._settings.model_source,
                self._settings.optimize_model,
                self._settings.load_denoiser,
            )

            import torch

            optimize = self._settings.optimize_model
            if optimize and not torch.cuda.is_available():
                logger.warning(
                    "optimize=True but no CUDA - disabling torch.compile. "
                    "Set VOXCPM2_OPTIMIZE_MODEL=false to suppress."
                )
                optimize = False

            logger.info(
                "torch device check: cuda=%s, mps=%s → model will use CPU",
                torch.cuda.is_available(),
                getattr(torch.backends.mps, "is_available", lambda: False)(),
            )

            def _load():
                t0 = time.perf_counter()
                m = VoxCPM.from_pretrained(
                    hf_model_id=self._settings.model_source,
                    cache_dir=self._settings.model_cache_dir,
                    local_files_only=self._settings.local_files_only,
                    load_denoiser=self._settings.load_denoiser,
                    optimize=optimize,
                )
                elapsed = time.perf_counter() - t0
                device = str(getattr(getattr(m, "tts_model", None), "device", "unknown"))
                logger.info("model loaded in %.2fs on device=%s, optimize=%s", elapsed, device, optimize)
                return m

            if platform.system() == "Darwin":
                logger.info(
                    "loading VoxCPM2 inline on macOS to avoid libomp/PyTorch segfaults during initialization"
                )
                self._model = _load()
            else:
                self._model = await asyncio.to_thread(_load)
            return self._model

    def _build_generation_kwargs(
        self,
        request: SynthesisRequest,
        assets: PreparedAudioAssets,
    ) -> dict[str, object]:
        """Build kwargs matching VoxCPM2's generate() signature exactly.

        Only passes parameters documented in the VoxCPM2 API:
        text, prompt_text, prompt_wav_path, reference_wav_path,
        cfg_value, inference_timesteps, normalize, denoise, retry_badcase.

        Filters out None values to let VoxCPM use its own defaults.
        """
        raw = {
            "text": request.text,
            "prompt_text": request.prompt_text,
            "prompt_wav_path": assets.prompt_audio_path,
            "reference_wav_path": assets.reference_audio_path,
            "cfg_value": request.cfg_value,
            "inference_timesteps": request.inference_timesteps,
            "normalize": request.normalize_text
            if request.normalize_text is not None
            else self._settings.default_normalize_text,
            "denoise": request.denoise_conditioning_audio
            if request.denoise_conditioning_audio is not None
            else self._settings.default_denoise_conditioning_audio,
            "retry_badcase": request.retry_badcase
            if request.retry_badcase is not None
            else self._settings.default_retry_badcase,
        }
        # Filter None values so VoxCPM uses its defaults
        return {k: v for k, v in raw.items() if v is not None}

    def _detect_sample_rate(self, model) -> int:
        tts_model = getattr(model, "tts_model", None)
        return int(getattr(tts_model, "sample_rate", self._settings.sample_rate_fallback))

    def _detect_device(self, model) -> str:
        tts_model = getattr(model, "tts_model", None)
        return str(getattr(tts_model, "device", "cpu"))
