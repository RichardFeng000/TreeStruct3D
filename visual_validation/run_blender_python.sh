#!/usr/bin/env bash

set -euo pipefail

usage() {
  printf '用法: %s <blender_python.py> [脚本参数...]\n' "$(basename "$0")"
  printf '\n'
  printf '示例:\n'
  printf '  %s ./datasets/benchmark/categories/Bird_seed0/Bird_seed0.py\n' "$(basename "$0")"
  printf '  %s ./scene.py --seed 0 --output ./result.blend\n' "$(basename "$0")"
  printf '\n'
  printf '使用 TREESTRUCT3D_BLENDER、仓库工具目录、macOS 应用目录或 PATH 中的 Blender 5.0。\n'
}

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

if [[ "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  exit 0
fi

input_script="$1"
shift

if [[ ! -f "$input_script" ]]; then
  printf '错误：找不到 Python 脚本：%s\n' "$input_script" >&2
  exit 1
fi

app_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
script_dir="$(cd -- "$(dirname -- "$input_script")" && pwd -P)"
script_path="$script_dir/$(basename -- "$input_script")"

resolve_blender() {
  local candidate
  if [[ -n "${TREESTRUCT3D_BLENDER:-}" ]]; then
    printf '%s\n' "$TREESTRUCT3D_BLENDER"
    return
  fi
  candidate="$app_dir/../tools/Blender-5.0.app/Contents/MacOS/Blender"
  if [[ -x "$candidate" ]]; then
    printf '%s\n' "$candidate"
    return
  fi
  candidate="/Applications/Blender.app/Contents/MacOS/Blender"
  if [[ -x "$candidate" ]]; then
    printf '%s\n' "$candidate"
    return
  fi
  if command -v blender >/dev/null 2>&1; then
    command -v blender
    return
  fi
  return 1
}

if ! blender_bin="$(resolve_blender)" || [[ ! -x "$blender_bin" ]]; then
  printf '错误：找不到 Blender 5.0；请设置 TREESTRUCT3D_BLENDER。\n' >&2
  exit 1
fi

printf 'Blender: %s\n' "$blender_bin"
printf '执行脚本: %s\n' "$script_path"

# 从输入脚本所在目录启动，方便脚本读取相对路径资源。
cd "$script_dir"

# 不使用 --background：Blender 会打开 GUI，并在启动后执行传入的 Python。
# “--”之后的参数会原样传递给 Blender Python 脚本。
exec "$blender_bin" --python "$script_path" -- "$@"
