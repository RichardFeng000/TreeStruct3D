#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "$0")" && pwd -P)"
port="${MODEL_PLAYGROUND_PORT:-8765}"
if [[ $# -gt 0 ]] && [[ "$1" =~ ^[0-9]+$ ]]; then
  port="$1"
  shift
fi
printf '启动模型参数编辑器：http://127.0.0.1:%s/\n' "$port"
exec python3 "$script_dir/algorithm/model_playground.py" \
  --port "$port" \
  --open \
  "$@"
