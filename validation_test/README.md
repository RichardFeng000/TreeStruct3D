# Validation Test

这个项目把网页视觉层和 Blender Python 转换算法分开维护，同时保留根目录的一键启动方式。

## 目录结构

```text
validation_test/
├── frontend/                    # 网页界面、树图、锚点图、Three.js 预览
│   ├── model_playground.html
│   ├── interactive_tree_template.html
│   └── vendor/
├── algorithm/                   # Blender Python 解析、执行、GLB 导出和关系分析
│   ├── model_playground.py      # 本地 API 服务与任务调度
│   ├── blender_live_export.py   # Blender 5.0 内执行源码并导出 GLB
│   ├── code_structure_tree.py   # 定义树、调用图、零件父子树静态分析
│   ├── runtime/                 # 本地运行时父子/共享锚点 Blender probe
│   └── achieve/                 # 网页不依赖的审计与 QA 工具
├── datasets/                    # 三个统一管理的数据源
│   ├── benchmark/               # Benchmark 验证集
│   ├── stage1_output/           # Stage 1 Output
│   └── stage1_output_openai5.6sol/ # Stage 1 GPT-5.6-sol
├── achieve/                     # 与正常运行无关的旧输出和审计报告
│   ├── audit_reports/
│   └── Bird_seed0_structure_tree/
└── *.sh                         # 用户入口脚本
```

## 启动

```bash
cd /Users/fengruiding/Downloads/3d_code/validation_test
./start_model_playground.sh
```

也可以使用：

```bash
./run_model_playground.sh
```

指定一个数据集或单个 seed，并让前端启动后直接选中它：

```bash
bash run_dataset.sh stage1_output
bash run_dataset.sh stage7_output
bash run_dataset.sh Chameleon_seed0
```

也可以同时加载多个数据集，它们会作为独立代码源出现在同一个前端下拉框中，
第一个数据集默认选中：

```bash
bash run_dataset.sh stage7_output stage7.1_output
```

参数也可以是完整路径，例如：

```bash
bash run_dataset.sh \
  /Users/fengruiding/Downloads/3d_code/stage_results/stage7_output/Chameleon_seed0
```

脚本会依次识别当前路径、`datasets/`、`stage_results/` 和
`stage_results/stage7_output/`。既可以传整个输出目录、同时传多个输出目录，也可以
只传其中一个 seed 文件夹；启动后第一个数据源会被直接选中。目录缺少同名 Python 时会明确报错，
不会退回到其他数据源。已有服务占用 8765 时，脚本会自动选择下一个空闲端口。

这些启动脚本都会调用 `algorithm/model_playground.py`。前端由本地服务从
`frontend/` 提供，不能直接双击 HTML。项目仍固定使用 Blender 5.0。

Stage7 新代码使用顶层字面量 `PART_PARAMS` 作为原生参数协议。网页只修改这些
源参数，然后从空场景完整执行代码，让几何和共享锚点一起重算。旧代码没有该
协议时仍可预览，但部件滑块会明确显示为“旧代码近似缩放”，不能作为共享锚点
随参数变化的证明。运行时验证会分别放大父节点和子节点；三种执行都通过后，
关系才会显示为共享锚点。

运行时父子和共享锚点分析所需的 `blender_probe.py` 已包含在
`algorithm/runtime/`，不再依赖外部 `SR_F1_Structural_Metric` 目录。

详细功能说明见 [MODEL_PLAYGROUND.md](MODEL_PLAYGROUND.md)。
