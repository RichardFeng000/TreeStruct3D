#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repository_dir="$(cd -- "$script_dir/.." && pwd -P)"
pipeline_output_dir="$repository_dir/TreeStruct3D/outputs"
legacy_results_dir="$repository_dir/stage_results"
legacy_pipeline_output_dir="$legacy_results_dir/stage7_output"

usage() {
  printf '%s\n' \
    "用法：bash run_dataset.sh <数据集名|目录|单个seed目录> [...] [-- 服务端参数]" \
    "" \
    "示例：" \
    "  bash run_dataset.sh stage1_output" \
    "  bash run_dataset.sh ../TreeStruct3D/outputs" \
    "  bash run_dataset.sh ../TreeStruct3D/outputs/Chameleon_seed0" \
    "  bash run_dataset.sh Chameleon_seed0" \
    "  bash run_dataset.sh /完整路径/outputs/Chameleon_seed0" \
    "  bash run_dataset.sh first_output second_output -- --render-timeout 120"
}

if [[ $# -lt 1 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
  usage
  [[ $# -ge 1 ]] && exit 0
  exit 2
fi

selectors=()
while [[ $# -gt 0 ]] && [[ "$1" != "--" ]] && [[ "$1" != --* ]]; do
  selectors+=("$1")
  shift
done
if [[ $# -gt 0 ]] && [[ "$1" == "--" ]]; then
  shift
fi
if [[ ${#selectors[@]} -eq 0 ]]; then
  usage
  exit 2
fi

dataset_paths=()
for selector in "${selectors[@]}"; do
  dataset_path=""
  if [[ -e "$selector" ]]; then
    dataset_path="$selector"
  elif [[ -e "$script_dir/datasets/$selector" ]]; then
    dataset_path="$script_dir/datasets/$selector"
  elif [[ -e "$pipeline_output_dir/$selector" ]]; then
    dataset_path="$pipeline_output_dir/$selector"
  elif [[ -e "$legacy_results_dir/$selector" ]]; then
    dataset_path="$legacy_results_dir/$selector"
  elif [[ -e "$legacy_pipeline_output_dir/$selector" ]]; then
    dataset_path="$legacy_pipeline_output_dir/$selector"
  else
    printf '错误：找不到数据集或 seed：%s\n' "$selector" >&2
    printf '已检查 validation_test/datasets、TreeStruct3D/outputs 和旧版输出目录。\n' >&2
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
  dataset_paths+=("$dataset_path")
done

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

args=(
  --host 127.0.0.1
  --port "$port"
)
for index in "${!dataset_paths[@]}"; do
  dataset_path="${dataset_paths[$index]}"
  dataset_label="$(basename -- "$dataset_path")"
  if [[ "$index" == "0" ]] && [[ -n "${MODEL_PLAYGROUND_DATASET_LABEL:-}" ]]; then
    dataset_label="$MODEL_PLAYGROUND_DATASET_LABEL"
  fi
  args+=(--dataset "$dataset_path" --dataset-label "$dataset_label")
done
if [[ "${MODEL_PLAYGROUND_OPEN:-1}" != "0" ]]; then
  args+=(--open)
fi

for dataset_path in "${dataset_paths[@]}"; do
  printf '数据集：%s\n' "$dataset_path"
done
printf '启动前端：http://127.0.0.1:%s/\n' "$port"
cd "$script_dir"
exec python3 algorithm/model_playground.py "${args[@]}" "$@"
