# Achieve

这里保存正常网页启动和模型生成流程不依赖的手动检查工具：

- `audit_runtime_graphs.py`：批量审计运行时父子和锚点关系。
- `audit_bird_source_execution.py`：检查 Benchmark Bird 的专用执行逻辑。
- `audit_glb_geometry.py`：读取 GLB 并输出几何统计。
- `qa_render_glb.py`：把 GLB 渲染为 PNG 供人工检查。

核心运行代码仍在上一级 `algorithm/`。移动这些文件不会改变网页算法。
