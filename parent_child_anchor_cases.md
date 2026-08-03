# 三个数据集的父子关系与锚点案例

统计口径：

- **父子边**：运行时分析确认存在方向的父 → 子关系。
- **共享锚点**：同时具备明确父子方向、显式共享锚点证据、几何接触和坐标对齐；网页中显示为绿色。
- **断裂连接**：代码声明了父子方向，但连接未通过几何与锚点验证。
- 纯几何接触但没有方向的边不计入父子关系。

## Benchmark 验证集（212）

共有 6 个 seed 检测到明确父子方向，其中 4 个同时具有确认共享锚点。

| Seed | 父子边 | 确认共享锚点 | 断裂连接 |
|---|---:|---:|---:|
| Bed_seed0 | 5 | 0 | 4 |
| Bird_seed0 | 11 | 9 | 0 |
| Crab_seed0 | 12 | 10 | 2 |
| Lobster_seed0 | 14 | 12 | 2 |
| Sink_seed0 | 1 | 0 | 1 |
| SpinyLobster_seed0 | 14 | 14 | 0 |

严格满足“父子关系 + 确认共享锚点”的 4 个 seed：

1. `Bird_seed0`
2. `Crab_seed0`
3. `Lobster_seed0`
4. `SpinyLobster_seed0`

## Stage 1 Output（212）

共有 14 个 seed 检测到明确父子方向，但没有任何 seed 具有确认共享锚点。

| Seed | 父子边 | 确认共享锚点 | 断裂连接 |
|---|---:|---:|---:|
| BeverageFridge_seed0 | 3 | 0 | 3 |
| Bird_seed0 | 39 | 0 | 31 |
| Chameleon_seed0 | 26 | 0 | 20 |
| Dishwasher_seed0 | 2 | 0 | 2 |
| Fish_seed0 | 9 | 0 | 2 |
| FoodBox_seed0 | 127 | 0 | 127 |
| FruitCoconutgreen_seed0 | 1 | 0 | 0 |
| FruitStrawberry_seed0 | 3 | 0 | 0 |
| LeafGinko_seed0 | 1 | 0 | 0 |
| Lid_seed0 | 1 | 0 | 1 |
| MaizeMonocot_seed0 | 6 | 0 | 0 |
| ReedMonocot_seed0 | 14 | 0 | 0 |
| Sink_seed0 | 4 | 0 | 4 |
| Tap_seed0 | 4 | 0 | 4 |

`FoodBox_seed0` 达到了探针的 128 节点上限，因此检测到的 127 条断裂连接可能仍是下限。

## Stage 1 · GPT-5.6-sol（46）

没有任何 seed 检测到明确父子方向或确认共享锚点。部分模型存在大量无方向几何接触边，但这些关系不能作为父子方向或共享锚点证据。

## 汇总

| 数据集 | Seed 数 | 有父子方向 | 有确认共享锚点 | 两者同时具备 |
|---|---:|---:|---:|---:|
| Benchmark 验证集 | 212 | 6 | 4 | 4 |
| Stage 1 Output | 212 | 14 | 0 | 0 |
| Stage 1 · GPT-5.6-sol | 46 | 0 | 0 | 0 |
| 合计 | 470 | 20 | 4 | 4 |

三个数据集合计有 20 个数据集案例带有明确父子方向；只有 Benchmark 中的 `Bird_seed0`、`Crab_seed0`、`Lobster_seed0` 和 `SpinyLobster_seed0` 同时具备确认共享锚点。
