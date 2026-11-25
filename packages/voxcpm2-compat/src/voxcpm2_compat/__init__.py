from __future__ import annotations

import logging
import os
import platform
from typing import Any

__all__ = ["apply_torch_compat_patches", "prepare_process_environment", "__version__"]

__version__ = "0.3.1"

logger = logging.getLogger("voxcpm2_compat")

_ENV_PREPARED = False


def prepare_process_environment() -> None:
    global _ENV_PREPARED
    if _ENV_PREPARED:
        return

    if platform.system() == "Darwin":
        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
        os.environ.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.0")
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

    _ENV_PREPARED = True


def _normalize_sdpa_mask(attn_mask: Any, query, key):
    if attn_mask is None or not hasattr(attn_mask, "dim"):
        return attn_mask

    if attn_mask.dim() != 1 or query.dim() < 3 or key.dim() < 3:
        return attn_mask

    key_len = key.shape[-2]
    if attn_mask.shape[0] != key_len:
        return attn_mask

    target_shape = (1,) * (query.dim() - 1) + (key_len,)
    return attn_mask.reshape(target_shape)


def apply_torch_compat_patches() -> None:
    prepare_process_environment()

    try:
        import torch
    except ImportError:
        return

    if platform.system() == "Darwin" and hasattr(torch.backends, "mps"):
        torch.backends.mps.is_available = lambda: False
        torch.backends.mps.is_built = lambda: False

    original_sdpa = torch.nn.functional.scaled_dot_product_attention
    if getattr(original_sdpa, "_voxcpm2_api_compat", False):
        return

    def _patched_sdpa(query, key, value, *args, **kwargs):
        devices = [getattr(tensor, "device", None) for tensor in (query, key, value)]
        if any(device is None or device.type != "cpu" for device in devices):
            return original_sdpa(query, key, value, *args, **kwargs)

        squeezed_query = query.dim() == 3
        if squeezed_query:
            query = query.unsqueeze(-2)
        if key.dim() == 3:
            key = key.unsqueeze(-2)
        if value.dim() == 3:
            value = value.unsqueeze(-2)

        attn_mask = kwargs.get("attn_mask")
        normalized_mask = _normalize_sdpa_mask(attn_mask, query, key)
        if normalized_mask is not attn_mask:
            kwargs = dict(kwargs)
            kwargs["attn_mask"] = normalized_mask

        result = original_sdpa(query, key, value, *args, **kwargs)
        if squeezed_query:
            result = result.squeeze(-2)
        return result

    _patched_sdpa._voxcpm2_api_compat = True
    torch.nn.functional.scaled_dot_product_attention = _patched_sdpa

    logger.info("applied VoxCPM2 compatibility patches")
