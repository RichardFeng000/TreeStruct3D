# Stage7：3DV 2027 投稿就绪度与创新性检索审计

日期：2026-08-06  
审计对象：`/Users/fengruiding/Downloads/3d_code/Stage7` 及其现有 Stage 7 输出  
结论等级：**当前不建议以 full paper 状态投稿 3DV 2027；主题适配，但创新主张与实验证据均未达到主会标准。**

## 1. 一句话结论

Stage7 的研究问题是好的：让 LLM 生成的开放类别 Blender 程序不仅“看起来连着”，而且在部件参数变化后仍保持表面连接与层级一致性。这个方向符合 3DV。但是，当前系统最显眼的两个上层创新——“先生成层级结构蓝图再生成代码”和“用可执行几何测试反馈修复”——已经被 2025–2026 年工作大范围覆盖；尚可能成立的窄创新是：

> **针对开放类别 Blender mesh 程序，定义并验证“部件参数变化后的真实表面连接完整性”。**

目前代码还没有真正证明这项性质，原因是验证器允许“辅助圆盘/孤立顶点/脱离主体的小几何岛”充当锚点，旧结果又早于当前更严格的 validator。现有实验只有 3 个最新类别、单 seed、少量模型，没有独立视觉指标、人评、强基线、消融、统计显著性和验证器有效性研究。因此当前更像一个有潜力的研究原型，不是已经完成的 3DV paper。

## 2. Stage7 实际贡献拆解

当前实现包含以下组件：

1. 从文本中抽取 category-neutral 的层级部件蓝图；
2. 将蓝图作为 user context 注入，保持 3DCodeBench system prompt 不变；
3. 要求每个非根部件只有一个 parent，并声明成对的 parent/child surface anchor；
4. 生成 Blender Python、`PART_PARAMS` 和参数化重建逻辑；
5. 用运行时 validator 检查层级、接触、共享锚点世界坐标一致性；
6. 对部件参数施加变化，重建后再次检查锚点；
7. 将确定性失败信息送回 LLM 修复，然后再进入视觉反馈。

这是一个完整的工程链条，但论文新颖性必须按“最小可声明 claim”拆开，而不能把组件组合本身直接等同于创新。

## 3. 全网检索后的逐项创新判断

| Stage7 候选主张 | 最接近工作 | 判断 | 当前可否声称“首次” |
|---|---|---:|---:|
| 文本先转层级部件/约束图，再规划 Blender 代码 | [Graph-CAD](https://arxiv.org/abs/2604.10075)、[HierCAD](https://arxiv.org/abs/2607.11339)、[LAM](https://openreview.net/forum?id=OQIMv0WBig) | 高度重合 | **否** |
| 用 parent-child attachment/port/mate 表示装配关系 | [AssemCAD](https://arxiv.org/abs/2607.05123)、Graph-CAD | 高度重合 | **否** |
| 确定性几何/拓扑测试，并将失败反馈给 LLM 修复 | [CADTests](https://arxiv.org/abs/2605.07807)、[CADCodeVerify](https://openreview.net/forum?id=BLWaTeucYX)、[LL3M](https://arxiv.org/abs/2508.08228) | 已有明确先例 | **否** |
| 通过参数扰动检验程序的参数完整性/可编辑性 | [CADEngBench](https://openreview.net/pdf?id=hIKrX5XpuN)、HierCAD | 核心思想已有 | **否** |
| 发现 LLM 3D 程序存在浮空、断连部件 | [3DCodeBench](https://arxiv.org/abs/2606.01057) | 已被基准明确指出 | **否** |
| LLM 规划、生成 Blender 代码并自动调试 | [3D-GPT](https://openreview.net/forum?id=n04Dbq4Y8J)、LL3M | 成熟方向 | **否** |
| 参数变化后，成对锚点必须重新落到父子最终 mesh 的真实表面并继续连接 | AssemCAD、CADEngBench、HierCAD 均有相邻概念，但检索中未发现完全相同的开放类别 Blender mesh 协议 | 有窄差异 | **暂可作为待验证 novelty，不可按现状声称已完成** |

### 最关键的撞车工作

#### Graph-CAD（ICLR 2026）

[Graph-CAD](https://arxiv.org/abs/2604.10075) 已经把自然语言转为包含部件、组件和显式几何约束的层级 decomposition graph，再生成 action plan 和 `bpy` 程序；它还提供约 12K 数据、1.4K 类别、280 个评测样本、几何一致性指标及消融。它与 Stage7 “结构蓝图 → Blender 代码”的前半段几乎同题，因此这一层不能再作为主要 novelty。

#### AssemCAD（2026-07）

[AssemCAD](https://arxiv.org/abs/2607.05123) 使用 typed parts、由真实 B-Rep 几何支持的 ports、可执行 mates、封闭式变换求解、确定性多层验证和有界 LLM repair。它与 Stage7 的 paired anchors、装配关系、几何验证和修复高度相邻。Stage7 的剩余区别主要在：开放类别/有机形状、Blender mesh，以及对编辑后锚点的动态重算。

#### CADTests 与 CADEngBench

[CADTests](https://arxiv.org/abs/2605.07807) 已经系统研究“可执行几何/拓扑测试 → 失败日志 → planner 修复”，并用 mutation analysis 和 human study 验证测试质量。[CADEngBench](https://openreview.net/pdf?id=hIKrX5XpuN) 则把 parameter perturbation robustness 用于评价 CAD 程序的 parametric integrity。Stage7 可以把这两者结合到“attachment integrity”，但不能声称发明了 executable test 或 parameter perturbation。

## 4. 当前实验审计

### 4.1 有利证据

- pipeline 和结构约束已经落到可执行代码，不只是概念稿；
- 运行 `python -m unittest discover -s tests -v`，53 个单元测试全部通过；
- 最新一组保存结果中，GPT-5.5 的 Crab/Fish/Lobster 初次结构检查均为 100；Gemini 3.1 的三个样本均能由首次失败修复到 100；
- 视觉样例总体可辨识，表明结构约束没有完全破坏生成能力；
- system prompt 保持了 3DCodeBench 原版，结构信息主要经 user context 注入。

这些证据足以说明“原型可运行”，但不足以说明“方法优于现有技术”。

### 4.2 会直接导致审稿人拒稿的问题

#### A. 结果与当前代码版本不一致

Stage7 当前仓库只有两个提交，最新的严格验证逻辑仍是未提交改动。现有结构分数文件缺少新版 validator 的字段，说明保存的 100 分是在旧规则下得到的。

将旧结果按当前 `PART_PARAMS`/blueprint ID 规则做静态一致性复核：

| 保存结果 | blueprint 部件数 | native parameter IDs | 与当前语义单元规则一致 |
|---|---:|---:|---:|
| GPT-5.5 Crab | 7 | 7 | 是 |
| GPT-5.5 Fish | 9 | 9 | 是 |
| GPT-5.5 Lobster | 7 | 8 | 否 |
| Gemini 3.1 Crab | 5 | 13 | 否 |
| Gemini 3.1 Fish | 7 | 10 | 否 |
| Gemini 3.1 Lobster | 7 | 15 | 否 |
| Kimi K3 Crab | 5 | 13 | 否，且旧规则下也失败 |

因此旧结果中的 6 个“最终 100 分”只有 2 个可以静态证明满足当前 exact-ID gate。必须冻结 commit 后全部重跑。

#### B. 验证器存在严重 construct-validity 漏洞

当前 runtime probe 会检查锚点是否靠近最终 Mesh 的某个 vertex，但不会证明该 vertex：

- 属于主体最大连通分量；
- 位于父子实际接触界面；
- 不是专门添加的隐藏小圆盘、孤立顶点或分离 mesh island；
- 在视觉上或拓扑上真的连接了两个主体。

项目内的 `analysis_reports/stage71_anchor_surface_analysis/anchor_surface_analysis.md` 已经观察到 `add_disc` 式辅助锚点；GPT Lobster 脚本也包含类似结构。也就是说，当前指标可能把“为了通过测试而添加的几何”误判为真实连接。这会成为审稿人最强的攻击点。

#### C. 指标与方法协议循环定义

Stage7 明确要求生成 `stage7_part_id`、`PART_PARAMS` 和 anchor helper；普通 3DCodeBench baseline 没有这些注解，因此即便几何上连接良好，也无法在 Stage7 指标上得分。若直接报告“Stage7 共享锚点率远高于 baseline”，只能证明它更遵守自己的输出协议，不能证明它生成了更好的 3D 结构。

需要增加与表示无关的外部指标，例如连通分量、接触面积/间隙、GCS、独立编辑成功率和人工几何判断。

#### D. 规模远不足以支持论文结论

当前较新的 v2 结果只有 Crab、Fish、Lobster 三个类别，每类一个 seed，7 个完成运行。总目录里的 14 个日志也只覆盖 4 个唯一类别，并混合了不同模型、prompt 和 validator 版本。没有：

- 训练/测试或 held-out 类别设计；
- 同配置多 seed；
- 公平 baseline；
- 组件消融；
- 置信区间或统计检验；
- 视觉质量量化和人评；
- 验证器 false-positive/false-negative 审计；
- 时间、token 和修复成本比较。

## 5. 模拟 3DV 审稿结论

以下不是 3DV 官方评分，只是按主会审稿标准做的内部估计：

| 维度 | 当前评价 |
|---|---|
| 3DV 主题契合度 | 8.5/10，属于 3D representation、generative 3D、CAD/code generation |
| 整体方法新颖性 | 3.5/10，上层设计被 Graph-CAD/AssemCAD/CADTests 覆盖 |
| 最窄 attachment-integrity claim | 5.5/10，有差异但尚未被可靠实现和验证 |
| 技术可信度 | 3/10，验证器存在可被投机通过的漏洞 |
| 实验证据 | 2/10，样本和比较都不够 |
| 可复现性 | 3/10，代码可运行但版本与结果不对齐 |
| 当前总体建议 | **Weak Reject / Reject** |

[3DV 2027 CFP](https://3dvconf.github.io/2027/call-for-papers/) 的主题范围与本工作相符，且 3DV 2025 接收过 [3D-GPT](https://openreview.net/forum?id=n04Dbq4Y8J)，所以问题不是 venue fit。问题是 2026-08-28 截止前只剩 22 天，而当前仍缺一整套论文级实验。

## 6. 最值得保留的论文定位

不建议继续把论文中心写成“Structure-Aware Blender Generation”。这个名字会正面撞上 Graph-CAD 和 HierCAD。

更有机会的定位是：

> **Dynamic Attachment Integrity for Open-Vocabulary Procedural 3D Programs**  
> 核心命题：静态 render/接触正确不等于参数化编辑后的装配完整性；提出与生成协议尽量解耦的动态连接评价、对抗 mutation suite，以及可执行修复方法。

可考虑的标题：

- *Beyond Static Validity: Dynamic Attachment Integrity for Text-to-3D Programs*
- *Do Generated 3D Programs Stay Assembled? Evaluating Parametric Attachment Integrity*
- *Surface-Grounded Attachments for Editable Open-Vocabulary Blender Programs*

这一改写把 Graph-CAD 视为结构规划前置工作，把 CADTests/CADEngBench 视为测试与参数完整性前置工作，然后主张：现有方法没有针对开放类别 mesh 生成系统地测量“编辑后连接是否仍成立”。该 claim 仍需下一节的实验证明。

## 7. 达到主会标准的最低实验包

### 7.1 先修验证器

1. 锚点必须位于最大或指定主体连通分量；
2. 不能用新增 helper geometry 充当 anchor；
3. 父子锚点必须落在真实接触 patch，而非任意最近顶点；
4. 同时检查接触间隙、穿插、孤岛数量和主体连通性；
5. 独立扰动 parent 和 child，覆盖尺度、长宽高、局部形状参数；
6. 建立 mutation suite：helper disc、孤立 vertex、浮空小岛、只更新一侧 anchor、硬编码 world coordinate、视觉接触但拓扑不接触；这些变体必须被拒绝；
7. 由至少 3 名标注者审查一批样本，报告 validator 的 precision/recall 和一致性。

### 7.2 公平消融

在相同模型、采样参数、token、repair 轮数和视觉反馈预算下比较：

1. 原始 3DCodeBench direct generation；
2. `+ blueprint only`；
3. `+ anchor contract only`；
4. `+ blueprint + anchor contract`，无 validator repair；
5. `+ static validator repair`；
6. `+ parameter-invariance validator repair`（完整 Stage7）；
7. 去掉父端扰动、去掉子端扰动、去掉真实表面限制等关键消融。

### 7.3 数据规模与指标

- 强版本：覆盖 3DCodeBench 全部 212 类别；最低可辩护版本：至少 100 类别；
- 每类别至少 3 seeds，至少 3 个有代表性的闭源/开源模型；
- 报告 executability、视觉质量、静态接触、连通分量/浮空率、dynamic attachment survival、编辑任务成功率；
- 视觉指标与人类 pairwise preference 必须独立于 Stage7 协议；
- 二值结果使用 paired bootstrap 或 McNemar 类检验，并报告置信区间；
- 报告 token、运行时间、修复次数和失败类型分布。

### 7.4 复现要求

- 提交当前改动并冻结 exact commit；
- 每个结果记录 commit、prompt SHA、模型版本、采样参数和 Blender 版本；
- 旧 validator 结果与新结果完全分开；
- 发布 blueprints、生成脚本、扰动配置、validator 原始日志和人评标注。

## 8. 投稿决策

### 对 3DV 2027

**按当前成果，不建议直接投 full paper。** 22 天内若无法完成验证器重构、百类以上重跑、公平消融、人评和论文写作，仓促投稿的拒稿风险很高。

### 更合理的路线

1. 把当前版本整理为技术报告/项目页面，明确标为 prototype；
2. 先把“动态连接完整性”做成可信 benchmark 与 adversarial validator；
3. 再证明结构蓝图和 repair 对该独立指标有稳定增益；
4. 完成后投后续 3DV/CVPR/ICCV 或相关 CAD/graphics venue；若必须赶当前周期，更适合 workshop/demo，而不是把现有结果包装成完整主会论文。

## 9. 检索范围与边界

检索围绕以下 claim 组合展开：text-to-CAD/Blender、hierarchical part graph、assembly graph、surface anchor、port/mate、constraint-based generation、geometry verifier、LLM repair、parameter perturbation、parametric integrity、editable procedural 3D、floating/disconnected parts。重点检查了 arXiv、OpenReview、会议论文页和 3DV 官方 CFP，并追踪到 2026-08-06 可见的最新相邻工作。

“全网检索”不能数学上证明绝对无人做过；本报告给出的是公开可检索文献范围内的高置信判断。若用于专利 novelty 或正式法律意见，还需要独立的专利数据库检索。

## 10. 核心参考工作

- [Graph-CAD: Learning Hierarchical and Geometry-Aware Graph Representations for Text-to-CAD](https://arxiv.org/abs/2604.10075)
- [ASSEMCAD: Production-Ready CAD Assembly Generation from Natural Language](https://arxiv.org/abs/2607.05123)
- [CADTests: Text-to-CAD Evaluation with CADTests](https://arxiv.org/abs/2605.07807)
- [CADEngBench: Can AI Systems Co-Author Engineering Designs?](https://openreview.net/pdf?id=hIKrX5XpuN)
- [HierCAD: Hierarchical Text-to-CAD Design via Structure Alignment and Parameter Grounding](https://arxiv.org/abs/2607.11339)
- [3DCodeBench](https://arxiv.org/abs/2606.01057)
- [LL3M: Large Language 3D Modelers](https://arxiv.org/abs/2508.08228)
- [CADCodeVerify](https://openreview.net/forum?id=BLWaTeucYX)
- [3D-GPT](https://openreview.net/forum?id=n04Dbq4Y8J)
- [3DV 2027 Call for Papers](https://3dvconf.github.io/2027/call-for-papers/)

