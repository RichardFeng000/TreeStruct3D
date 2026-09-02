# CCS 最初 Idea 与 Stage7 路线复盘

日期：2026-08-06  
原始文件日期：2026-07-28  
原始文件：`CCS_REFERENCE_STYLE_SCORING_SYSTEM.md`

## 结论

最初的 CCS idea 不是 Stage7 的一个早期、较弱版本。恰恰相反：**它是比当前 Stage7 更完整、更可辩护的研究问题定义。**

Stage7 把 CCS 中的一部分思想产品化为生成协议和 validator：层级、共享锚点、参数化重建和扰动检查。但在这个过程中，它把原本“与实现方式尽量解耦的行为评价”收窄成“必须生成指定 ID、`PART_PARAMS` 和 authored-anchor helper 的协议符合性检查”。这造成了当前最严重的 metric circularity：Stage7 自己要求一种代码格式，再用只识别这种格式的指标证明 Stage7 更好。

因此，推荐关系应当反过来：

> **CCS 是论文的研究主线和独立 benchmark；Stage7 是一个试图提高 CCS 的被评方法。**

而不是把 CCS 当作 Stage7 的内部 validator。

## 1. 原始 CCS 真正有价值的地方

### 1.1 它评价的是动态构造性质

原始 CCS 的核心问题非常明确：默认参数下看起来连接，不等于代码形成了可传播、可修改的构造系统。它同时关心：

- 父子依赖；
- 共享或等价派生锚点；
- 坐标的数据来源；
- 上游参数改变后的下游传播；
- 接触、穿透和方向保持；
- 零件内部连续性。

这比单纯的 render success、视觉相似度或默认状态接触更接近“程序化 3D 代码质量”的本质。

### 1.2 它本来就考虑了实现无关性

文档第 9、11 节明确规定：

- 未识别的 helper 不能直接判零分；
- 静态分析不懂，但扰动后正确跟随，可以获得行为证据；
- `unknown`、`failed`、`passed` 必须区分；
- ground truth 只标注父子语义关系、连接区域和扰动对象；
- 不规定函数名和具体实现方式。

这是原始 idea 最成熟的一点，也正是当前 Stage7 validator 丢失最多的一点。

### 1.3 它把静态解释和运行验证结合起来

原始设计不是只做 AST 分析，也不是只测最终 Mesh：

- 静态依赖用于解释“为什么能够跟随”；
- 参数扰动用于验证“是否真的跟随”；
- 默认几何用于检查接触、穿透和局部连续；
- 最差扰动进入总分，避免平均值掩盖灾难性失败。

这种 code provenance + runtime behavior 的双证据设计，比 Stage7 目前只检查声明锚点世界坐标相等更完整。

## 2. CCS 到 Stage7 的演化

| 原始 CCS | Stage7 当前实现 | 结果 |
|---|---|---|
| 评价任意实现的父子依赖 | 要求生成特定 blueprint 和 part IDs | 自动化更容易，但协议依赖增强 |
| 共享锚点或等价参数派生均可得分 | 主要奖励 authored shared-anchor contract | 判据更硬，但会漏掉等价正确实现 |
| 静态不可解析时可依靠扰动行为 | 缺少指定 annotation/helper 时难以评分 | baseline 天然吃亏 |
| 检查接触、穿透、方向和锚点跟随 | 当前重点是锚点 world gap 和最近 vertex | 覆盖范围明显收窄 |
| 多倍率扰动，并同时关注 Mean 与 Min | 当前主要是固定 scale rebuild gate | 实验维度减少 |
| GT 不规定被测代码实现 | blueprint/`PART_PARAMS` 与生成协议绑定 | 出现 metric circularity |
| CCS 是评价体系 | validator 同时是生成约束和成功指标 | 方法与指标未独立 |

Stage7 的优势是已经把一部分思想做成可运行 pipeline；它的缺陷不是方向错，而是把独立评价器和特定生成协议混在了一起。

## 3. 为什么原始 CCS 比当前 Stage7 更适合作为论文中心

在 2026 年已有文献背景下，以下宽主张都比较拥挤：

- 层级结构图再生成 CAD/Blender 代码：[Graph-CAD](https://arxiv.org/abs/2604.10075)、[HierCAD](https://arxiv.org/abs/2607.11339)；
- ports/mates 和装配约束：[AssemCAD](https://arxiv.org/abs/2607.05123)；
- executable tests 和反馈修复：[CADTests](https://arxiv.org/abs/2605.07807)；
- 参数扰动评价 parametric integrity：[CADEngBench](https://openreview.net/pdf?id=hIKrX5XpuN)。

所以 Stage7 若作为“又一个结构规划与修复 pipeline”，差异不够大。

CCS 更好的切口不是声称首次使用参数扰动，而是研究：

> **现有 text-to-3D code 模型的静态视觉/几何正确性，是否能够预测其编辑后的构造一致性？如何在开放类别、不同编码风格下，对每条语义父子关系进行 code-plus-runtime 的动态评价？**

这个问题可以产生独立 benchmark、指标有效性研究、模型横向结论和新的 failure taxonomy。即使 Stage7 最终没有显著提升，CCS benchmark 本身仍可能形成论文贡献；这比把整篇论文押在 Stage7 repair 成功率上更稳。

## 4. 推荐的新论文结构

建议题目：

> *Do Generated 3D Programs Remain Assembled? Evaluating Construction Coherence under Parametric Edits*

推荐的四项贡献：

1. **任务定义**：区分 default-state geometry validity 与 edit-time construction coherence；
2. **CCS benchmark**：开放类别对象的语义父子关系、连接区域和安全参数扰动标注；
3. **混合评价器**：静态因果/数据流证据加 Blender 黑盒扰动结果，输出 relation-level 状态与 evidence coverage；
4. **系统研究**：比较多个模型和生成方法，并用 Stage7 作为一个提高 CCS 的方法或 case study。

最有价值的实验结论应当是以下一种或多种：

- 视觉分数高并不代表扰动后结构稳定；
- 默认接触率高并不代表存在正确的参数传播；
- 不同模型可能具有相近视觉质量，却有显著不同的 CCS；
- Stage7 可以提高动态构造一致性，同时量化它对视觉质量、代码长度和成本的影响。

## 5. 原始 CCS 仍需修正的地方

原始文档不是可以直接投稿的完成指标，仍有以下问题：

1. `25/25/20/25/5` 权重和各封顶阈值是人工设定，必须用人类判断、mutation study 或学习式校准证明；
2. hierarchy、anchor、derivation、perturbation 之间高度相关，不能把它们当作完全独立证据；
3. 必须明确“安全参数”的发现方式，不能任意修改源码数字；
4. 接触、穿透和方向的阈值需要按对象尺度归一化；
5. ground truth 的 semantic region 标注和左右/重复部件匹配成本较高；
6. Reference 风格不能被预设成天然满分，reference 本身也应接受几何与扰动审计；
7. 需要专门攻击评价器：helper disc、孤立 vertex、分离 mesh island、硬编码但在少量倍率下碰巧通过等。

因此，论文中最好报告一组分解指标和 relation-level logs，不要只给一个 CCS 总分。

## 6. 最小可行实验

第一阶段不必立刻跑 212 类别，可以先做一个评价器有效性实验：

1. 选 20–30 个类别，每类 3–8 条关键关系；
2. 每个正确程序人工构造 5–8 种 mutation：断开依赖、固定世界坐标、只更新父端、helper island、严重穿透、方向翻转；
3. 由 3 名标注者独立判断每条关系在默认与扰动后的状态；
4. 测量各 CCS 子项与人评的一致性、precision/recall、错误类型；
5. 再扩展到至少 100 类别、3 seeds、3 个生成模型；
6. 最后比较 direct generation 与 Stage7 的动态 CCS 增益。

如果第 4 步不能可靠区分真实传播和投机通过，先不要扩大生成实验；评价器本身是整篇论文的地基。

## 7. 最终判断

- 原始 idea 的研究价值：**高于当前 Stage7 pipeline 叙事**；
- 当前公开文献下的宽口径 novelty：中等，不能声称首次 executable test 或 parameter perturbation；
- 窄口径 novelty：**开放类别 text-to-3D 程序的 relation-level、code-plus-runtime 动态构造一致性 benchmark**，具有继续深挖价值；
- 最优组织方式：**CCS 是主线，Stage7 是方法/应用，不是反过来。**

## 8. 文件核验

用户提供的微信临时文件与仓库中的以下文件完全相同：

`/Users/fengruiding/Downloads/3d_code/SR_F1_Structural_Metric/CCS_REFERENCE_STYLE_SCORING_SYSTEM.md`

两者 SHA-256：

`0452a6aff4e1d627662eec005a4da7ee5bd0d825a4d3ceb7220f81ed6e661459`

