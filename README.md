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

两个启动脚本都会调用 `algorithm/model_playground.py`。前端由本地服务从
`frontend/` 提供，不能直接双击 HTML。项目仍固定使用 Blender 5.0。

运行时父子和共享锚点分析所需的 `blender_probe.py` 已包含在
`algorithm/runtime/`，不再依赖外部 `SR_F1_Structural_Metric` 目录。

详细功能说明见 [MODEL_PLAYGROUND.md](MODEL_PLAYGROUND.md)。
