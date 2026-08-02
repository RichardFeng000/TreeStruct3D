#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PORT="${MODEL_PLAYGROUND_PORT:-8765}"
OPEN_BROWSER="${MODEL_PLAYGROUND_OPEN:-1}"
URL="http://127.0.0.1:$PORT/"

if ! command -v python3 >/dev/null 2>&1; then
  echo "错误：找不到 python3。" >&2
  exit 1
fi

if [[ ! -f "$SCRIPT_DIR/model_playground.py" ]]; then
  echo "错误：找不到 $SCRIPT_DIR/model_playground.py" >&2
  exit 1
fi

if command -v curl >/dev/null 2>&1 \
  && curl --fail --silent --max-time 1 "${URL}api/sources" >/dev/null 2>&1; then
  echo "模型参数编辑器已经在运行：$URL"
  if [[ "$OPEN_BROWSER" != "0" ]] && command -v open >/dev/null 2>&1; then
    open "$URL"
  fi
  exit 0
fi

args=(--host 127.0.0.1 --port "$PORT")
if [[ "$OPEN_BROWSER" != "0" ]]; then
  args+=(--open)
fi

echo "启动 Blender 模型参数编辑器：$URL"
cd "$SCRIPT_DIR"
exec python3 model_playground.py "${args[@]}" "$@"
