# 人物装备与衣物：调研汇总与推荐路线

2026-09-23。宿主 `D:/FPS3D/FPSGAME`，UE 5.8.2。

三份调研报告的合并结论与最终建议：

| 报告 | 范围 | 取证等级 |
| --- | --- | --- |
| [引擎内置方案](clothing-system-research-engine.md) | UE 5.8 本机引擎源码 + Epic 官方文档 | **一手源码/官方** |
| [GitHub 与开源工具](clothing-fitting-research-github.md) | Blender 工具链、开源项目、学术方案 | 一手（GitHub API / Blender 手册 `.rst`） |
| [Fab 资产市场](clothing-fitting-research-fab.md) | 可购买的服装资产与许可 | **受限**：`fab.com` 全站对本会话 403，无价格经页面核实 |

> **采信提醒**：Fab 报告**没有任何价格与逐商品许可标签是读到的**，全部标注未核实。其中"MetaHuman 服装必须用 MetaHuman 骨架"来自 Epic 官方文档（A 级），可信；商品推荐来自开发者社区卖家帖（B 级），可作线索不可作采购依据。

---

## 1. 先纠正一个前提

用户问的是"找到衣服模型后，如何贴合人物模型进行调整或裁剪"。调研后发现：**这个问题的答案在很大程度上取决于「要不要保留 Manny 骨架」，而后者又由一个引擎硬约束决定。** 所以先把约束讲清楚。

### 硬约束一：Leader Pose 禁止附加骨（**最高优先级，是本项目的第一性约束**）

本项目 `world_mesh` 用的就是 Leader Pose。Epic 官方原文（[Working with Modular Characters](https://dev.epicgames.com/documentation/en-us/unreal-engine/working-with-modular-characters-in-unreal-engine)）：

> any child mesh object of the Leader Bone has to be a subset with the exact matching structure. **You cannot have any other extra joints or skip any joints.** Since there is no Bone Buffer data for extra joints, **any extra or skipped joints will be rendered using the reference pose.**
>
> Child Mesh objects contained within a Modular Character blueprint **cannot run unique animations, or simulate physics independently** from the Leader Pose component.

我在引擎源码里独立复核了这条（`SkinnedMeshComponent.cpp`）：`UpdateLeaderBoneMap()` 对 follower 骨骼按名字查 leader，缺失的映射为 `INDEX_NONE`；`GetMissingLeaderBoneRelativeTransform()` 沿父链找共同祖先，用 follower 自己的**参考姿态**定位该骨骼。**文档与源码一致。**

→ **裙摆骨、披风骨、飘带骨、马尾骨在 Leader Pose 下拿不到独立动画。** 这不是可以绕过的细节，它决定了服装资产能不能用。

### 硬约束二：服装自己跑布料，与 Leader Pose 挂载不兼容

`USkeletalMeshComponent::BindClothToLeaderPoseComponent()` 头文件注释原文（`SkeletalMeshComponent.h`）：

> The meshes used in the components must be identical for the cloth to bind correctly

→ **「独立服装网格 + Leader Pose 挂载」与「该服装独立布料模拟」不能兼得。** 要布料就得换 Copy Pose from Mesh 或 Mesh Merge。

### 硬约束三：MetaHuman 服装不能直接用在 Manny 上

Fab 报告从 Epic 官方文档核到：MetaHuman 骨骼服装（`.mhpkg` / ChaosOutfitAsset）"must use the MetaHuman base skeleton, or a very close variant"，且骨骼不得重新父级化，衣柜校验会主动拒绝骨架不符的条目。

**但**：两套骨架骨骼语义相同（卖家原文 "they use the same bone structure"）。差距在**网格与绑定归属**，不在骨骼命名。所以 —— **资产不能直接拿来用，权重和源文件可以。**

---

## 2. 引擎三条挂载路线的官方代价表

Epic 官方原文表格（上文链接）：

| | Leader Pose Component | Copy Pose from Mesh | Skeletal Mesh Merge |
| --- | --- | --- | --- |
| **Setup Cost** | Min | Medium | High |
| **Game Thread Cost** | Min | High | Medium |
| **Render Thread Cost** | High | High | Low |
| **Physics** | No | AnimDynamics / RigidBody | Yes |
| **Morph Target** | Yes | Yes | No |

对应到本项目的选择：

- **Leader Pose**（现状）—— 适合**不需要额外骨**的模块化装备：头盔、护甲片、背包、贴身衣裤鞋。Game Thread 最省。**这是绝大多数 FPS 装备的实际需求。**
- **Copy Pose from Mesh** —— 唯一能在"服装独立成组件"前提下给服装加**附加骨或独立物理**的官方路径。代价是每件服装都要跑一套动画图求值。要做披风/裙摆跟随，走这条。
- **Skeletal Mesh Merge** —— 降 draw call 用，但**牺牲 morph target**，而项目明确规划了捏人。**当前阶段不合适。**

---

## 3. 最终推荐路线

### 路线 A（首选，立即可做）：Blender 离线权重传递 + 现有 Leader Pose

**流程**：
1. 从 UE 导出 Manny 身体网格 FBX 作为权重源
2. 外部服装用 **Shrinkwrap** 修正穿插
3. **Data Transfer** 修改器（Data Types = Vertex Groups，`Generate Data Layers`，Mapping 用 `Projected Face Interpolated` / `Nearest Face Interpolated`，开 `Only Neighbor Geometry` + `Max Distance`）把 Manny 权重传给服装
4. UE 内建 `SkinWeightsPaintTool` 做少量人工修正
5. 写进 `player_body.json` 的 `outfits.<id>.world_mesh`，运行时沿用现有 Leader Pose

**理由**：全部内置工具、**零新增依赖与许可风险**、`bpy` 可脚本化（契合项目"后台批次"规则）、**唯一不违背 Leader Pose 硬约束的方案**。改动面最小，不动已认可的第一人称手臂与 Manny 动作基线。

**代价与边界**：这套流程只解决"衣服跟随身体动作"，**不解决换体型、不解决精细遮挡、不支持附加骨**。`hide_body_materials` 仍是材质区级的粗糙遮挡（作者原话已承认）。

### 路线 B（次选，中期）：Chaos Cloth Asset + `TransferSkinWeights`

**已在本机核实该节点存在**：`ChaosClothAssetDataflowNodes/.../TransferSkinWeightsNode.{h,cpp}`，编辑器工具 `ClothTransferSkinWeightsTool`。GitHub 报告从官方节点参考核到参数：`TransferMethod` 默认 `InpaintWeights`（"for better results"）、`RadiusPercentage` 0.05、`NormalThreshold` 30°、`LayeredMeshSupport` true、`NumSmoothingIterations` 10、`InpaintMask` 可手工保留部分权重。

**何时上**：布料模拟需求明确之后。注意它触发**硬约束二**——要布料就不能继续用 Leader Pose 挂载，得同步改挂载方式。**这是把它放中期而非首期的原因。**

### 路线 C（明确排除）：为服装换 MetaHuman 骨架 / 引入 MetaHuman 衣柜

理由：MetaHuman 服装系统明确要求 MetaHuman 骨架（官方）；采用它等于重做当前 59 条 Manny 动作的适配、足部 IK、蹲姿调整和已认可的全身皮肤材质路线。**收益（自动适配多体型）不足以抵消当前阶段的重做成本。**

### 关于 Chaos Outfit Asset 的正确定位

我在引擎报告里查明：它的硬门槛**不是"必须 MetaHuman"，而是一份 7 项测量值契约**（`Hip`、`Bust`/`Chest`、`Underbust`、`Waist`、`Neck to Waist`、`Rise`、`Inseam`，源码 `FBodyMatchParameters`）。骨架侧只有 `UChaosOutfitAssetBodyUserData` 这个挂在网格上的 `TMap<FString,float>`，**没有任何 MetaHuman 专属类**。

**但要注意**：Fab 报告核到 MetaHuman 服装**资产**受骨架校验限制（`.mhpkg` 系）。引擎能力与资产策略是两件事：
- **引擎能力**上，Outfit Asset 更像数据契约，理论上可喂非 MetaHuman 网格 —— **但男性 Manny 填 `Bust`/`Underbust`/`Hourglass` 这套偏女性体型的判据会退化，实际质量未经实测。**
- **资产策略**上，市面上标注 MetaHuman 的服装走的是骨架校验路径，不能直接用于本项目。

→ **建议列为"值得小成本验证的备选"，不作为当前主线。**

---

## 4. 市场供给：不会卡住路线 A

Fab 报告核到**多家卖家在同一商品里同时交付 MetaHuman + UE5 Mannequin 双绑定**，其中 **Lumelle Studio** 明确交付 **FBX / Blender / glTF 源文件** —— 这正是路线 A 需要的原料，且**绕开"商品工程没有 5.8 版本"的问题**（源文件不依赖引擎版本）。

推荐顺位（均为 **B 级**证据，采购前须自行核对）：
1. **Lumelle Studio — Short Sleeve Hoodie 01** —— 双骨架 + FBX/Blender/glTF 源文件，**用它的源文件先跑通管线**（产出是**管线**，不是衣服）
2. **Davlet — Sci-Fi Clothing Pack 01–04** —— 明确适配 original male Manny rig，题材最贴 FPS。⚠️ 工程停在 5.6–5.7，**不要直接迁移到 5.8**
3. **Yusuf Y.Y — LE_Characters_Pack** —— UE5 Manny 骨架、模块化、写明面向 FPS/TPS。⚠️ 含 40+ 附加骨，**购买前需问卖家服装网格引用了哪些骨**（触及硬约束一）

**负面结论（已核实，避免重复检索）**：GitHub 上 `unreal modular character outfit`、`skin weight transfer unreal`、`metaHuman wardrobe`、`blender addon cloth fit` 搜索结果**均为 0 个仓库**。**不存在可直接用的成熟开源 UE 换装/拟合插件** —— 项目现有 `player_body.json` + `FPSPlayerBodyEquipment` 在开源生态里已属靠前。

**采购前 5 项核对清单**：骨架 / 骨骼引用 / 是否含源文件 / UE 版本 / 许可标签。

---

## 5. 建议的执行顺序

1. **先验证一件事**（低成本）：拿 Lumelle 的 FBX 源文件，在 Blender 里对 `SK_Mannequin` 跑通「重蒙皮 → Shrinkwrap 修正 → 回导 UE → Leader Pose 挂载」。**产出是一条可复用管线**，之后任何服装都走它。
2. **同时做一项法务确认**：玩家角色用的是 `SKM_Manny_Simple`，"人体模型本身能否随商业游戏发行"存在**冲突的社区说法**，Epic Content EULA 原文页本次 403 未读到。**建议由用户直接读原文确认** —— 低成本、高影响。
3. **管线跑通后**再按题材采购 Davlet / Yusuf 的服装。
4. **布料模拟需求明确时**，再评估路线 B（Chaos Cloth Asset），并接受挂载方式变更。
5. **暂不引入** Mutable / Chaos Outfit Asset / MetaHuman 衣柜 —— 它们是"成体系换装 + 多体型"阶段的工具，当前没有衣物资产，引入为时过早。

---

## 6. 不确定 / 需要验证（三份报告合并后的关键项）

1. **`SkinWeightsPaintTool`（`UWeightToolTransferManager::TransferWeights()`）能否经 Python/commandlet 调用** —— 类存在（`MeshModelingToolsEditorOnly` 插件）已确认，**能否进后台脚本管线未验证**。这直接决定路线 A 第 4 步能否自动化。**建议优先实测。**
2. **Chaos Outfit Asset 用 Manny + 7 项测量值的实际质量** —— 引擎侧无 MetaHuman 硬绑定已查明，但男性 Manny 填表后的分类退化程度未实测。
3. **`MeshResizing`（MeshWrap/MeshWarp）能否在本项目启用** —— 与 `Dataflow`、`GeometryCollectionPlugin`、`GeometryProcessing`、`HairStrands` 有依赖，未验证与现有插件集共存。
4. **"旧版 Clothing Tool 已废弃"无法证实** —— GitHub 报告独立检查 UE 5.2 官方页面正文**无 deprecated 字样**，且写明底层是 Chaos Cloth solver。**不要以"已废弃"为理由决策。**
5. **UE "Proxy Mesh / Mesh Clipping" 查无此物** —— 在 BindClothToLeaderPoseComponent、Clothing Tool、Modular Characters 三处官方文档中均未出现，本会话无法确认该特性存在。
6. **Fab 全部价格、逐商品许可标签未核实**（站点 403）。`uecandy.com` 是 Fab 的**未授权分发镜像站**，已排除在验证来源之外 —— **不要用它。**
7. **UE 5.8 Release Notes 未逐条覆盖**（页面过大未完整抓取），"5.8 对布料/换装的具体改动"本报告未覆盖。
8. **全部视觉质量、性能开销、打包体积、morph target 影响均未测试。** 按项目规则，未启动编辑器、未启用任何插件、未修改 `.uproject`、未验收渲染。

---

## 7. 本次调研的产出文件

- `clothing-system-research-engine.md` —— 引擎内置方案（源码级）
- `clothing-fitting-research-github.md` —— GitHub / 开源工具 / 学术方案
- `clothing-fitting-research-fab.md` —— Fab 资产市场与许可
- 本文 —— 合并结论与推荐路线
