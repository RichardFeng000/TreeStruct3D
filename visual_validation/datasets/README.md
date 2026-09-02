# Datasets

网页可切换的三个代码数据源统一放在这里：

- `benchmark/categories/`：Benchmark 验证集，212 个模型。
- `stage1_output/`：Stage 1 Output，212 个模型。
- `stage1_output_openai5.6sol/`：Stage 1 GPT-5.6-sol，46 个模型。

每个模型目录中的正式入口都是与目录同名的 Python 文件。网页服务默认从这些固定位置建立模型目录。
