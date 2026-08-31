# VoxCPM2 API

[![CI](https://github.com/shiftbloom-studio/voxcpm2-api/actions/workflows/ci.yml/badge.svg)](https://github.com/shiftbloom-studio/voxcpm2-api/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/shiftbloom-studio/voxcpm2-api)](https://github.com/shiftbloom-studio/voxcpm2-api/releases)

Production-ready FastAPI and WebSocket service for [VoxCPM2](https://huggingface.co/openbmb/VoxCPM2), with:

- REST synthesis via `/v1/speech`
- streaming synthesis via `/v1/stream`
- optional transcription via `/v1/transcribe`
- Linux CUDA auto-selection for `nano-vllm-voxcpm`
- official `voxcpm` backend support for prompt and reference audio
- macOS Apple Silicon compatibility patches for VoxCPM2 CPU inference
- a matching Tauri desktop client released alongside the API

## Release Artifacts

Every tagged release publishes three separate artifact families:

- `voxcpm2_api-<version>-py3-none-any.whl`
  The API package with FastAPI, WebSocket endpoints, Docker support, and the built-in compatibility layer.
- `voxcpm2_compat-<version>-py3-none-any.whl`
  The standalone compatibility wrapper for custom Python integrations that need the macOS and CPU safety patches without the API service.
- `voxcpm2_api_macos-<tag>-<arch>.tar.gz`
  A standalone macOS embedded API bundle for local packaging or custom launchers.
- `VoxCPM2-ui-macos-<tag>-<arch>.zip`
  The macOS `.app` bundle for the Tauri desktop client.
- `VoxCPM2-ui-macos-<tag>-<arch>.dmg`
  The drag-and-drop macOS installer for the desktop client.

## Installation

### From a GitHub release wheel

Install the API directly from a release asset:

```bash
pip install "voxcpm2-api[voxcpm] @ https://github.com/shiftbloom-studio/voxcpm2-api/releases/download/v0.2.0/voxcpm2_api-0.2.0-py3-none-any.whl"
```

If you only want the compatibility wrapper for your own VoxCPM2 code:

```bash
pip install "voxcpm2-compat @ https://github.com/shiftbloom-studio/voxcpm2-api/releases/download/v0.2.0/voxcpm2_compat-0.2.0-py3-none-any.whl"
```

### From source

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev,voxcpm]"
cp .env.example .env
voxcpm2-api
```

The helper scripts do the same:

```bash
./scripts/bootstrap.sh
./scripts/run-dev.sh
```

### Docker

The default Docker image now installs the official `voxcpm` backend automatically.

```bash
cp .env.example .env
docker compose up --build
```

## Backend Strategy

The service keeps one API surface and swaps runtimes underneath it:

- Linux + NVIDIA CUDA: prefers `nano-vllm-voxcpm` for plain text synthesis
- macOS, Windows, generic Linux, or conditioned requests: uses the official `voxcpm` Python package
- prompt or reference audio requests: always route to the official `voxcpm` backend

### macOS / Apple Silicon

VoxCPM2 is currently safest on macOS when it runs on CPU:

- MPS is disabled because VoxCPM2 uses `bfloat16` and the public runtime is not stable on Apple MPS
- the API patches PyTorch `scaled_dot_product_attention` for the exact CPU decoding path used by VoxCPM2
- OpenMP duplicate-library crashes are suppressed for mixed native dependency stacks

These patches are built into `voxcpm2-api` and published separately as `voxcpm2-compat`.

## Configuration

All runtime configuration is environment-driven.

Important variables:

- `VOXCPM2_MODEL_ID`
- `VOXCPM2_MODEL_PATH`
- `VOXCPM2_MODEL_CACHE_DIR`
- `VOXCPM2_PREFER_BACKEND`
- `VOXCPM2_LOAD_DENOISER`
- `VOXCPM2_OPTIMIZE_MODEL`
- `VOXCPM2_LOCAL_FILES_ONLY`
- `VOXCPM2_STARTUP_LOAD_MODEL`
- `VOXCPM2_HF_ENDPOINT`
- `VOXCPM2_CORS_ORIGINS`
- `VOXCPM2_NANOVLLM_DEVICES`

See [`./.env.example`](./.env.example) for the full template.

## API

### Health

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/status
curl http://localhost:8000/v1/runtime
```

### Synthesis

Return WAV:

```bash
curl -X POST http://localhost:8000/v1/speech \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hello from VoxCPM2","response_format":"wav"}' \
  --output out.wav
```

Return base64:

```bash
curl -X POST http://localhost:8000/v1/speech \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hello from VoxCPM2","response_format":"base64"}'
```

Prompt continuation:

```json
{
  "text": "Continue this in the same voice.",
  "prompt_text": "Earlier context",
  "prompt_audio_base64": "<wav-as-base64>",
  "reference_audio_base64": "<optional-reference-wav>",
  "response_format": "base64"
}
```

### Streaming

Connect to `/v1/stream`, send one JSON request, then read:

- `session.started`
- repeated `audio.chunk`
- `audio.completed`

Example payload:

```json
{
  "text": "Stream this sentence.",
  "chunk_format": "pcm16"
}
```

### Transcription

```bash
curl -X POST http://localhost:8000/v1/transcribe \
  -H 'Content-Type: application/json' \
  -d '{"audio_base64":"<wav-as-base64>"}'
```

## Desktop Client

The repository also contains a Tauri desktop app in [`./voxcpm2-ui`](./voxcpm2-ui).

On packaged macOS builds:

- the app auto-starts its bundled local API on `http://127.0.0.1:4000`
- the top `Connect` field still lets you switch to any other API, for example a manually started development server on `http://127.0.0.1:8000`
- the desktop bundle does not require a preinstalled Python environment

For local packaging or release verification, build the embedded API bundle first:

```bash
./scripts/build-macos-embedded-api.sh
```

Local development:

```bash
cd voxcpm2-ui/src-tauri
cargo tauri dev
```

## Testing and Release

```bash
. .venv/bin/activate
pytest
ruff check .
./scripts/build-release.sh
```

The default `pytest` run stays **offline**: it does not download the VoxCPM2
model and does not require CUDA or a GPU.

- `tests/test_app.py` — uses a `FakeRuntime`; no model, no network
- `tests/test_audio.py` — pure audio helpers; no model, no network
- `tests/test_hardware.py` — mocks the hardware probe; no model, no network
- `tests/test_compat.py` — needs `torch` installed (`pytest.importorskip("torch")`)
  but runs on CPU; it is skipped automatically when torch is absent

Tests that exercise the real `voxcpm` backend, model download, or CUDA paths are
**not** part of the default suite. To keep unit tests hermetic, leave these
`.env.example` values at their defaults (unset or `false`):

- `VOXCPM2_STARTUP_LOAD_MODEL=false` — do not load the model at startup
- `VOXCPM2_LOCAL_FILES_ONLY=false` — allow tests to stay on mocked runtimes
- `VOXCPM2_PREFER_BACKEND=auto` — do not force a backend that requires a GPU

CI runs on GitHub Actions for Linux and macOS. Tagged releases automatically publish:

- the API wheel and sdist
- the standalone compatibility wheel and sdist
- the standalone macOS embedded API bundle
- the macOS Tauri desktop `.app` ZIP
- the macOS Tauri desktop `.dmg`

## License

AGPL-3.0-only. See [`./LICENSE`](./LICENSE).
