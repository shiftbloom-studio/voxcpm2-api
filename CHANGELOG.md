# Changelog

## 0.3.1 - unreleased

- PyPI releases now use trusted publishing (OIDC) with attestations instead of a stored API token.
- `__version__` in both Python packages now matches the published version.
- Package metadata has been reviewed: no personal contact data, and security reports go to `safety@shiftbloom.studio`.
- The Docker image now runs as the non-root user `voxcpm` (uid 10001). Volumes mounted for the model cache must be writable by uid 10001.
- Third-party GitHub Actions are pinned to commit SHAs and kept current by Dependabot.

## 0.3.0 - 2026-09-02

- Added a standalone macOS embedded API bundle (`voxcpm2_api_macos-<tag>-<arch>.tar.gz`) and a drag-and-drop `.dmg` installer for the Tauri desktop client, both published with every tagged release.
- Packaged macOS desktop builds now auto-start a bundled local API on `http://127.0.0.1:4000` and no longer require a preinstalled Python environment; the `Connect` field still allows switching to any other API endpoint.
- Fixed macOS compatibility for the embedded runtime (asyncio event loop selection, inline model load, and updated compatibility patches).
- Moved the test client dev dependency from `httpx` to `httpx2`, resolving the Starlette test client deprecation.
- Hardened GitHub Actions with least-privilege workflow permissions and refreshed action majors (checkout v7, setup-python v7, artifact actions, action-gh-release v3).
- Docker image now builds on `python:3.14-slim`.
- Added CONTRIBUTING.md, Dependabot for pip and cargo, and expanded testing documentation.

## 0.2.0 - 2026-04-11

- Fixed VoxCPM2 generation on macOS and CPU-only hosts by disabling unstable MPS usage and patching the CPU `scaled_dot_product_attention` path used by VoxCPM2 incremental decoding.
- Added a standalone `voxcpm2-compat` Python artifact so the compatibility wrapper can be reused without the full API package.
- Hardened request validation for base64 audio payloads and converted invalid payloads from generic 500s into explicit 422 validation errors.
- Improved packaging metadata, Docker defaults, local bootstrap behavior, CI, and release automation.
- Added versioned release outputs for the API package, compatibility wrapper, and macOS Tauri desktop application.
