#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "$0")" && pwd -P)"
blender_bin="/Users/fengruiding/Downloads/3d_code/tools/Blender-5.0.app/Contents/MacOS/Blender"

if [[ ! -x "$blender_bin" ]]; then
  printf '错误：找不到项目固定的 Blender 5.0：%s\n' "$blender_bin" >&2
  exit 1
fi

port="${1:-8765}"
printf '启动模型参数编辑器：http://127.0.0.1:%s/\n' "$port"
exec python3 "$script_dir/algorithm/model_playground.py" \
  --blender "$blender_bin" \
  --port "$port" \
  --open
