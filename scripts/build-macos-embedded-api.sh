#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ROOT="$ROOT_DIR/build/macos-embedded-api"
VENV_DIR="$BUILD_ROOT/venv"
WORK_DIR="$BUILD_ROOT/pyinstaller"
RESOURCE_DIR="$ROOT_DIR/voxcpm2-ui/src-tauri/resources/api-macos"
APP_DIR="$RESOURCE_DIR/voxcpm2-api"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script only builds the embedded API bundle on macOS." >&2
  exit 1
fi

mkdir -p "$BUILD_ROOT" "$RESOURCE_DIR"
rm -rf "$APP_DIR" "$WORK_DIR"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python3 -m venv --system-site-packages "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

export KMP_DUPLICATE_LIB_OK=TRUE
export OMP_NUM_THREADS=1
export OMP_THREAD_LIMIT=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

python -m pip install --upgrade pip pyinstaller
# Keep the venv self-sufficient for CI/release builds while still allowing
# already-installed local packages to satisfy requirements via system-site-packages.
python -m pip install -e ".[voxcpm,asr]"

pyinstaller \
  --noconfirm \
  --clean \
  --onedir \
  --name voxcpm2-api \
  --paths "$ROOT_DIR/src" \
  --collect-all voxcpm \
  --collect-all faster_whisper \
  --collect-all ctranslate2 \
  --collect-all av \
  --collect-all modelscope \
  --collect-all funasr \
  --collect-all torchaudio \
  --copy-metadata voxcpm \
  --copy-metadata faster-whisper \
  --copy-metadata ctranslate2 \
  --copy-metadata modelscope \
  --copy-metadata transformers \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.loops.asyncio \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.protocols.websockets.auto \
  --hidden-import uvicorn.lifespan.on \
  --distpath "$RESOURCE_DIR" \
  --workpath "$WORK_DIR/build" \
  --specpath "$WORK_DIR/spec" \
  "$ROOT_DIR/src/voxcpm2_api/__main__.py"

[[ -x "$APP_DIR/voxcpm2-api" ]]
echo "Embedded macOS API bundle ready at $APP_DIR"
