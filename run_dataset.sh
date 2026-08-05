#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
workspace_dir="$(cd -- "$script_dir/.." && pwd -P)"
stage_results_dir="$workspace_dir/stage_results"
stage7_output_dir="$stage_results_dir/stage7_output"

usage() {
  printf '%s\n' \
    "用法：bash run_dataset.sh <数据集名|目录|单个seed目录> [服务端参数]" \
    "" \
    "示例：" \
    "  bash run_dataset.sh stage1_output" \
    "  bash run_dataset.sh stage7_output" \
    "  bash run_dataset.sh Chameleon_seed0" \
    "  bash run_dataset.sh /完整路径/stage7_output/Chameleon_seed0"
}

if [[ $# -lt 1 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
  usage
  [[ $# -ge 1 ]] && exit 0
  exit 2
fi

selector="$1"
shift

dataset_path=""
if [[ -e "$selector" ]]; then
  dataset_path="$selector"
elif [[ -e "$script_dir/datasets/$selector" ]]; then
  dataset_path="$script_dir/datasets/$selector"
elif [[ -e "$stage_results_dir/$selector" ]]; then
  dataset_path="$stage_results_dir/$selector"
elif [[ -e "$stage7_output_dir/$selector" ]]; then
  dataset_path="$stage7_output_dir/$selector"
else
  printf '错误：找不到数据集或 seed：%s\n' "$selector" >&2
  printf '已检查 validation_test/datasets、stage_results 和 stage7_output。\n' >&2
  exit 2
fi

if [[ -d "$dataset_path" ]]; then
  dataset_path="$(cd -- "$dataset_path" && pwd -P)"
elif [[ -f "$dataset_path" ]]; then
  dataset_parent="$(cd -- "$(dirname -- "$dataset_path")" && pwd -P)"
  dataset_path="$dataset_parent/$(basename -- "$dataset_path")"
else
  printf '错误：目标不是普通文件或目录：%s\n' "$dataset_path" >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  printf '错误：找不到 python3。\n' >&2
  exit 1
fi

if [[ -n "${MODEL_PLAYGROUND_PORT:-}" ]]; then
  port="$MODEL_PLAYGROUND_PORT"
else
  port=8765
  while ! python3 -c 'import socket, sys; s=socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); rc=s.connect_ex(("127.0.0.1", int(sys.argv[1]))); s.close(); raise SystemExit(0 if rc != 0 else 1)' "$port"; do
    port=$((port + 1))
    if (( port > 8799 )); then
      printf '错误：8765-8799 没有可用端口。\n' >&2
      exit 1
    fi
  done
fi

dataset_label="${MODEL_PLAYGROUND_DATASET_LABEL:-$(basename -- "$dataset_path")}"
args=(
  --host 127.0.0.1
  --port "$port"
  --dataset "$dataset_path"
  --dataset-label "$dataset_label"
)
if [[ "${MODEL_PLAYGROUND_OPEN:-1}" != "0" ]]; then
  args+=(--open)
fi

printf '数据集：%s\n' "$dataset_path"
printf '启动前端：http://127.0.0.1:%s/\n' "$port"
cd "$script_dir"
exec python3 algorithm/model_playground.py "${args[@]}" "$@"
