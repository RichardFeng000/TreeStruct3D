# Benchmark 验证集（212）运行时锚点审计结论

## 审计范围

- 代码源：Benchmark 验证集（212）
- Blender：固定 Blender 5.0.0
- 主批次：每个 seed 最长 60 秒
- 慢模型复查：每个 seed 最长 180 秒
- 最终完整明细：`runtime_anchor_benchmark_final.md`

## 最终结果

| 类型 | seed 数 | 说明 |
|---|---:|---|
| 运行时分析成功 | 210 | 包括 6 个提高超时后成功的慢模型 |
| 源代码/生成结果失败 | 2 | ElkhornCoral、FanCoral |
| 只保留 1 个最终 Mesh、0 条关系 | 199 | 无法从运行时恢复合并前的零件身份 |
| 保留多个运行时节点 | 11 | 其中只有 4 个 seed 有确认共享锚点 |
| 有确认共享锚点 | 4 | Bird、Crab、Lobster、SpinyLobster |
| 有明确断裂父子连接 | 4 | Bed、Crab、Lobster、Sink |
| 有锚点候选坐标不对齐 | 6 | Bed、Bird、Crab、Lobster、Sink、SpinyLobster |

## 两个真正执行失败的 seed

### ElkhornCoral_seed0

原始 Blender Python 能执行到结束，但最终输出为：

```text
Tree mesh: 41874 vertices
ElkhornCoralFactory ready: v=0 f=0
```

最终对象是 0 顶点、0 面的空 Mesh，所以锚点探针没有任何可观察几何。这不是网页图的问题，也不是 Blender 版本问题；该 seed 的几何处理流程把几何全部消掉了。

### FanCoral_seed0

原始脚本在 SciPy 稀疏矩阵构造处失败：

```text
Disc mesh: 3241 verts, 9560 edges
Graph: 3241 verts, 9560 edges
Endpoints: 1
ValueError: all index and data arrays must have the same length
```

代码动态计算出 `n_ep = 1`，但 `endpoints` 被写死为 5 个元素。随后 `ext_row`、`ext_col` 和 `ext_data` 使用了不同数量的 endpoint，导致三者长度不一致。错误位于 `FanCoral_seed0.py` 第 154–168 行。

## 6 个慢模型

这些 seed 在第一次 60 秒审计中超时，但 180 秒复查全部成功：

| Seed | 复查时间 | 最终结果 |
|---|---:|---|
| AgaveMonocot_seed0 | 63.369 秒 | 1 Mesh、0 关系 |
| Bush_seed0 | 59.790 秒 | 1 Mesh、0 关系；处于 60 秒临界区，运行时间有波动 |
| ColumnarCactus_seed0 | 83.612 秒 | 1 Mesh、0 关系 |
| Fern_seed0 | 134.480 秒 | 1 Mesh、0 关系 |
| Mushroom_seed0 | 122.706 秒 | 1 Mesh、0 关系 |
| Tree_seed0 | 168.766 秒 | 2 节点、1 条无方向接触关系、0 共享锚点 |

网页默认 60 秒不足以覆盖这些模型。Tree 尤其接近 180 秒，且最终只得到一条无方向接触关系。

## 11 个保留多节点的 seed

| Seed | 节点 | 边 | 父子方向 | 确认共享 | 明确断裂 | 坐标不对齐 | 主要问题 |
|---|---:|---:|---:|---:|---:|---:|---|
| Bed_seed0 | 6 | 12 | 5 | 0 | 4 | 7 | BedFrame→Sheet、两个 Pillow、Towel 的声明连接断裂 |
| Bird_seed0 | 12 | 23 | 11 | 9 | 0 | 8 | 9 条共享锚点可信；另外 8 条普通关系的最近点不对齐，不能叫共享锚点 |
| Crab_seed0 | 13 | 16 | 12 | 10 | 2 | 6 | 主体到 BézierCurve.002、Icosphere.001 的声明连接断裂 |
| LeafPine_seed0 | 2 | 1 | 0 | 0 | 0 | 0 | Needle 与 Twig 只有无方向接触，不能确定父子 |
| LiteDoor_seed0 | 3 | 0 | 0 | 0 | 0 | 0 | 有 3 个对象，但没有任何可证明连接 |
| Lobster_seed0 | 15 | 26 | 14 | 12 | 2 | 6 | 主体到 BézierCurve.018、BézierCurve.010 的声明连接断裂 |
| PanelDoor_seed0 | 3 | 0 | 0 | 0 | 0 | 0 | 有 3 个对象，但没有任何可证明连接 |
| Sink_seed0 | 2 | 1 | 1 | 0 | 1 | 1 | Plane→Cube 声明连接断裂，锚点距离约 0.289 |
| SpatulaOnHookBase_seed0 | 2 | 1 | 0 | 0 | 0 | 0 | 只有无方向接触，不能确定父子或共享锚点 |
| SpinyLobster_seed0 | 15 | 27 | 14 | 14 | 0 | 2 | 14 条共享锚点可信；2 条额外普通关系不对齐 |
| Tree_seed0 | 2 | 1 | 0 | 0 | 0 | 0 | TreeFactory 与 TreeFruits_apple 只有无方向接触；最近点约 0.735，不应解释成共享锚点 |

## 最大的系统性问题

199/212（约 93.9%）的 seed 在脚本结束时只留下一个最终合并 Mesh。对这些模型，运行时探针只能证明“当前场景有一个整体对象”，不能证明它们在概念上没有零件，也不能可靠恢复合并前的父子关系。

因此网页应严格区分：

1. **确认共享锚点**：必须同时具备明确父子方向、显式锚点证据、几何接触和坐标对齐。
2. **普通父子锚点**：方向存在，但没有共享锚点证据。
3. **无方向接触**：只能证明几何接近或接触，不能猜父子方向。
4. **单最终 Mesh**：只能显示整体节点，不能把静态函数调用层级伪装成运行时父子或共享锚点。
5. **空几何或源代码异常**：直接显示真实错误，不回退成“无父子关系”。

## 报告文件

- `runtime_anchor_benchmark_final.md`：212 个 seed 的逐项表格
- `runtime_anchor_benchmark_final.json`：完整机器可读结果
- `runtime_anchor_benchmark_timeout_retry.md`：6 个慢模型的复查数据
