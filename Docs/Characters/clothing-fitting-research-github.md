# 服装→身体自动拟合 / 换装技术调研（GitHub 与开源工具方向）

调研日期：本会话（GitHub REST API 返回的 `pushed_at` 最新可见到 2026-09-22）。
范围：只做检索与评估，不改动任何工程文件与资产。
方法：所有结论来自本次实际 `web_fetch` 抓到的页面。GitHub 仓库的星标数、许可证、最后提交时间取自 `https://api.github.com/repos/<owner>/<repo>`（或 `search/repositories`）返回的 JSON 字段。**凡未能从一手来源核实的，写在文末“不确定/需要验证”，不在此处当作事实陈述。**

> 说明：Epic 官方文档站（`dev.epicgames.com`）中部分页面在本会话可正常抓取（正文完整），部分页面（如 `SetLeaderPoseComponent` API 页、`Chaos Cloth Asset` 概览页）抓取只返回 “Table of Contents”，正文为空——这类页面在本文中不作为证据使用。
> Blender 官方手册站 `docs.blender.org` 对本会话的抓取返回 HTTP 403（Cloudflare 拦截），因此改用**同一官方手册的源文件**（`projects.blender.org/blender/blender-manual` 仓库中的 `.rst` 原文）作为一手来源。

---

## 0. 本项目当前约束（来自仓库文件，已实际读取）

| 约束 | 依据 |
| --- | --- |
| 玩家身体网格 `SKM_Manny_PlayerSkin`，骨架为 UE 标准 Manny（`SK_Mannequin`） | `Content/ColdSteelData/player_body.json` 中 `body_mesh`；`Docs/Characters/player-body-20260921.md` |
| 换装为 **config-driven**，字段 `world_mesh` / `hide_body_materials` / `body_materials` / `first_person_materials`，`outfits` 当前为空对象 `{}` | `Content/ColdSteelData/player_body.json` 第 65 行 `"outfits": {}` |
| 服装条目要求“与 Manny 骨架结构兼容，采用 Leader Pose 跟随全身动作，不跟随第一人称动画” | `Docs/Characters/player-body-20260921.md` 第 50 行 |
| `hide_body_materials` 是**身体材质区索引**，作者已明确写下“不能把隐藏整块材质当成已实现精细遮挡” | `Docs/Characters/player-body-20260921.md` 第 52 行 |
| 未来目标：多体型、捏人、布料模拟 | 任务描述 + 同文档第 53 行“多体型和捏人仍需对应资产与扩展” |
| 引擎版本 UE 5.8.2 | `FPSGAME/AGENTS.md` |
| 团队规模小、要求可重复管线 | 任务描述 |

关键含义：**当前管线已经确定用 Leader Pose 承载服装网格**。因此“服装拟合”在本项目里有两段不同的工作：
1. **离线**：把外部服装网格对齐到 Manny 身体、并把 Manny 的骨骼权重传给服装（否则 Leader Pose 下服装无法正确跟随）。
2. **在线**：运行时用 `world_mesh` 挂成 Leader Pose 的子组件，配合材质替换做遮挡。

---

## 1. Unreal Engine 原生系统

### 1.1 Leader Pose Component（模块化角色）

- **是什么**：`Set Leader Pose Component` 把多个 `SkinnedMeshComponent` 挂到一个 Leader 组件下，动画只在 Leader 上求值，子组件不持有自己的 Bone Transform Buffer。
- **成熟度/来源**：Epic 官方文档《Working with Modular Characters in Unreal Engine》（UE 5.7 版本页面）。
  URL: https://dev.epicgames.com/documentation/en-us/unreal-engine/working-with-modular-characters-in-unreal-engine?application_version=5.7
- **官方给出的三种方案对比（原文表格）**：

| | Leader Pose Component | Copy Pose from Mesh | Skeletal Mesh Merge |
| --- | --- | --- | --- |
| Setup Cost | Min | Medium | High |
| Game Thread Cost | Min | High | Medium |
| Render Thread Cost | High | High | Low |
| Physics | No | AnimDynamics 或 RigidBody | Yes |
| Morph Target | Yes | Yes | No |

- **对本项目的关键硬约束（原文引用）**：
  - “any child mesh object of the Leader Bone has to be a subset with the exact matching structure. You cannot have any other extra joints or skip any joints. Since there is no Bone Buffer data for extra joints, any extra or skipped joints will be rendered using the reference pose.”
  - “Child Mesh objects contained within a Modular Character blueprint cannot run unique animations, or simulate physics independently from the Leader Pose component.”
  - “you can define the Torso as the Leader Pose Component … child meshes can only run animations played on the Leader Pose Component's Bone Transform Buffer.”
  - Leader Pose 只降低 Game Thread 成本，“it does not reduce the render cost … additional draw calls for each additional section”。
- **评估（贴合本项目）**：这就是项目 `world_mesh` 已经在用的机制，不需要换。要点是两条：① 服装网格**必须是 Manny 骨架的严格子集**（不能多骨、不能少骨），这实际上禁止了“带裙摆骨/飘带骨的服装”在 Leader Pose 下正常工作；② 每个服装组件是一个额外 draw call，头和身体分段越多越贵。因此**服装网格的骨骼集合应与身体完全一致**，任何附加骨（布料辅助骨、裙骨）都不能走这条路——这类需求只能走 Copy Pose from Mesh 或 Chaos Cloth，代价是在 Game Thread 上多一套动画图求值。该约束是选择后续所有方案的**第一性约束**。

### 1.2 Copy Pose from Mesh（AnimGraph 节点）

- **是什么**：在子网格自己的 Animation Blueprint 里用 `Copy Pose From Mesh` 节点从另一个 Skeletal Mesh Component 复制姿态。只复制**同名匹配**的骨骼，其余骨骼用 reference pose。
- **来源**：同上文档 “Copy Pose From Mesh” 一节。
- **额外能力（原文）**：可以为每个子组件构建独立动画图，“able to build light physics simulations for each mesh component independently, using the RigidBody or AnimDynamics nodes”；代价是“more performance expensive … because an animation graph evaluation must run on each child”。
- **评估**：这是**唯一**能在“服装独立成组件”的前提下给服装加额外骨骼/独立物理的官方路径。对本项目 5.8 的 C++ 管线可行，但要把 `FPSPlayerBodyAnimInstance` 的逻辑复制/复用到服装的 AnimBP 上，属于中等工作量。若将来要做“披风/裙摆跟随”，这条是官方认可的路线。

### 1.3 Skeletal Mesh Merge（`FSkeletalMeshMerge`）

- **是什么**：运行时把多个 Skeletal Mesh 合成一个。需要启用 **Skeletal Merging** 插件（Other 分类）。
- **来源**：同 1.1 文档 “Skeletal Mesh Merge” 一节。
- **官方限制（原文）**：“requires the most set-up and comes at the cost of not being able to utilize a character's morph targets”；“a merged mesh only run one animation at once”；建议“use one common Material for your merged characters and decide on an atlas for your Textures”。
- **评估**：对本项目**当前阶段不合适**——项目明确保留 Manny 网格 + 材质槽替换 + 未来捏人（morph target），而 merge 会牺牲 morph target 并强制 atlas 化材质。它解决的是 draw call 问题，不是拟合问题。

### 1.4 Chaos Cloth Asset + Dataflow `TransferSkinWeights`（**最相关的 UE 原生自动权重传递**）

- **是什么**：`TransferSkinWeights` 是 Chaos Cloth Asset 的 Dataflow 节点，把某个 Skeletal Mesh 的蒙皮权重传给 cloth collection 里的 sim mesh 和/或 render mesh。
- **成熟度/来源**：Epic 官方节点参考（页面标题为 UE 5.8 Documentation）。Plugin `ChaosClothAssetDataflowNodes`，Category `Cloth`，Type `FChaosClothAssetTransferSkinWeightsNode`。
  URL: https://dev.epicgames.com/documentation/en-us/unreal-engine/node-reference/Dataflow/TransferSkinWeights
- **可核实的关键参数（原文）**：
  - 输入：`SkeletalMesh`（权重来源）、`LodIndex`、`Collection`、可选 `SimCollection`。
  - `TargetMeshType`：仅 simulation / 仅 render mesh / 两者（默认 `All`）。
  - `TransferMethod`：`ClosestPointOnSurface` 或 `InpaintWeights`（默认 **InpaintWeights**，“for better results”）。
  - `RadiusPercentage` 默认 `0.05`（以 sim mesh 包围盒对角线为基准的搜索半径）。
  - `NormalThreshold` 默认 `30`（度）；`LayeredMeshSupport` 默认 `true`（法线反向时翻转重试，用于内外两层贴近的网格）。
  - `NumSmoothingIterations` 默认 `10`，`SmoothingStrength` 默认 `0.1`（仅对自动计算的顶点做平滑）。
  - `InpaintMask`：权重图（默认 WeightMap 名 `InpaintMask`），非零处强制走自动计算而不是直接拷贝源权重——**这是“手工保留部分权重、其余自动补”的正式开关**。
  - `MaxNumInfluences` 默认 `Eight`。
  - 注意（原文）：“When using the simulation mesh as source for the render mesh transfer, the algorithm will always be the ClosestPointOnSurface method”。
- **评估**：这是**UE 内建的“把身体权重传给服装”的正式实现**，而且能力比 Blender 的最近点传递更完整（法线阈值 + 分层支持 + 平滑 + inpaint 掩码 + 最大影响骨数）。对本项目的意义是：如果服装走 Chaos Cloth Asset，就不需要自己写权重传递。但它要求把服装做成 **Chaos Cloth Asset**（Dataflow 资产），而不是普通 Skeletal Mesh，这会影响 `player_body.json` 里 `world_mesh` 的类型假设（当前字段语义是 Skeletal Mesh 路径）。是否能让 Chaos Cloth Asset 直接挂在 Leader Pose 下，见 1.5 的限制。

### 1.5 `BindClothToLeaderPoseComponent`（Cloth 与 Leader Pose 的交叉限制）

- **是什么**：让 follower 组件上的 cloth 直接采用 leader 组件上 cloth 的变换，而不是独立模拟。
- **来源**：Epic API 文档（UE 5.7 页面），`USkeletalMeshComponent::BindClothToLeaderPoseComponent`。
  URL: https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Engine/USkeletalMeshComponent/BindClothToLeaderPoseComponent?application_version=5.7
- **原文（关键）**：“If this component has a valid LeaderPoseComponent then this function makes cloth items on the follower component take the transforms of the cloth items on the leader component instead of simulating separately. @Note This will FORCE any cloth actor on the leader component to simulate in local space. **Also The meshes used in the components must be identical for the cloth to bind correctly**”
- **评估（重要）**：这条**直接冲突**于“服装是独立网格”的架构。要把布料模拟和 Leader Pose 一起用，官方要求 leader/follower 的 mesh 一致；否则就不能用这个绑定，只能让服装走独立的 Copy Pose from Mesh + 自己的物理。也就是说：**“Leader Pose 挂换装网格”与“服装独立布料模拟”在当前官方路径下不能同时白拿**，必须在“服装网格严格子集 + 不做独立模拟”与“Copy Pose from Mesh / Skeletal Mesh Merge + 独立模拟”之间选边。

### 1.6 Chaos Outfit Asset / Parametric Clothing（新资产类型）

- **是什么**：Outfit Asset 是 Chaos Cloth Asset 家族里的新资产类型，可以容纳多个独立衣物件的复杂组合，并带“可随体型缩放（resizable/parametric）”的意图；必须包含一个或多个 cloth asset。
- **来源**：Epic 官方《Getting Started with Parametric Clothing》（UE 5.7 页面）。
  URL: https://dev.epicgames.com/documentation/en-us/unreal-engine/getting-started-with-parametric-clothing?application_version=5.7
- **原文关键点**：
  - 术语区分：**Skeletal Mesh Clothing**（fixed，不可缩放，“creating a clothing model and skinning it to the body”）vs **Outfit Asset**（新资产类型，能处理复杂组合，为 resizing 设计）。
  - **UE 5.6 的限制（原文）**：“In Unreal Engine (UE) 5.6, resizable clothing does not support custom skinning, control rig, or Rigid Body Animation Notes (RBAN) on your clothing. You can have all of that on your clothing, but when it resizes, the clothing does a simple skin weight transfer from the body, and overwrites all of it.” → 即**缩放时会用身体的简单权重传递覆盖掉自定义权重**。
  - Outfit asset 的工作方式（原文）：把服装关联到它的 **source body**，然后“warps the clothing based on the difference between the source body and a new body with different measurements (target body)”；差异过大时会产生 warping，官方**建议“create multiple outfits for multiple source bodies”**，并且“Our system automatically detects which source body is the best match for each new target body”。
- **配套要求**：`Parametric Asset Setup`（MetaHuman 文档分类，5.8 页面）要求启用 **MetaHuman Creator** 插件 + **Chaos Cloth Asset** + **Chaos Cloth Asset Editor**，并从 Epic Games Launcher 勾选下载 **MetaHuman Creator Core Data**，还要配置 **MetaHuman SDK** 的 Packaging Paths（默认 outfits 目录 `/Game/Outfits`）。
  URL: https://dev.epicgames.com/documentation/en-us/metahuman/parametric-asset-setup-for-metahuman?application_version=5.8
- **`MakeOutfit` Dataflow 节点**：Category `Outfit`，包 `ChaosOutfitAssetDataflowNodes`，输出 `UChaosOutfit`。页面明确标注 **Experimental**。
  URL: https://dev.epicgames.com/documentation/en-us/unreal-engine/node-reference/Dataflow/MakeOutfit?application_version=5.7
- **评估（针对本项目）**：这是 UE 官方**唯一**针对“一套服装适配多体型”的正式机制，理论上正对“多体型/捏人”目标。但三条现实问题：
  1. 官方把它写在 **MetaHuman** 文档体系下，并显式要求 MetaHuman Creator 插件与 Core Data；本项目身体是 **Manny**，不是 MetaHuman。**（推断，已标注）**：把这套东西用在非 MetaHuman 骨架上，至少不是官方文档覆盖的场景，需要实测。
  2. `MakeOutfit` 仍标 Experimental。
  3. 5.6 行为说明“resize 时会用身体权重覆盖自定义权重”，与项目想在服装上保留自定义权重/材质分区的做法有冲突风险（该句针对 5.6，5.7/5.8 行为未在本文中核实，见文末）。
  结论：**作为中期目标（多体型）值得跟踪，不建议作为当前换装管线的地基。**

### 1.7 传统 Clothing Tool（在骨骼网格材质区上画布料）

- **是什么**：在 Skeletal Mesh Editor 里按 **Material Section** 选中一块几何，右键 `Create Cloth Asset from Selection`，再画布料权重（Brush / Gradient / Smooth / Fill），用 Mask 调 `Max Distance`、`Backstop Distance`、`Backstop Radius`、`Anim Drive Multiplier`；另有 `Copy Clothing from SkeletalMesh` 在相似网格间复制布料设置。
- **来源**：Epic 官方《Clothing Tool in Unreal Engine》（UE 5.2 页面）。
  URL: https://dev.epicgames.com/documentation/en-us/unreal-engine/clothing-tool-in-unreal-engine?application_version=5.2
- **原文要点**：该工作流“enables developers to work directly with Unreal Engine to author their content without the need for external dependencies”，底层是 “Chaos Cloth solver”。
- **评估**：这条路的特点是**布料必须长在同一个 Skeletal Mesh 的材质区上**，它不解决“外部服装网格如何贴合身体并取得权重”。对本项目而言，它的价值在于：如果将来把某件衣服合并进身体网格（或做成独立网格后仍按材质区管理），可以用它做局部布料参数。**注意**：本会话**未能从一手来源确认 “Clothing Tool 已废弃”**（见文末），因此不在此断言其废弃状态。

### 1.8 UE 内建“蒙皮权重重传”编辑器工具（`SkinWeightsPaintTool`）

- **是什么**：`MeshModelingToolset` 插件中的蒙皮权重绘制工具，带一个“从另一个 Skeletal Mesh 传权重”的管理器。
- **来源**：Epic API 文档（UE 5.7 页面）。
  URL: https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Plugins/MeshModelingToolsEditorOnly/UWeightToolTransferManager?application_version=5.7
  URL: https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Plugins/MeshModelingToolsEditorOnly/USkinWeightsPaintToolProperties?application_version=5.7
- **可核实内容**：
  - 头文件 `/Engine/Plugins/Runtime/MeshModelingToolset/Source/MeshModelingToolsEditorOnly/Public/SkeletalMesh/SkinWeightsPaintTool.h`。
  - `UWeightToolTransferManager`：“This class wraps a **source skeletal mesh** used to transfer skin weights to the tool target mesh”，公开函数含 `bool CanTransferWeights()`、`void TransferWeights()`、`SetSourceMesh(USkeletalMesh*)`。
  - `USkinWeightsPaintToolProperties` 中有 `Category="WeightTransfer"` 的属性：`SourceSkeletalMesh`、`SourceLOD`(`GetSourceLODsFunc`)、`SourceSkinWeightProfile`、`MeshSelectMode`(`EMeshTransferOption`)、`SourcePreviewOffset`；以及 SkinWeightLayer 分类的 `ActiveSkinWeightProfile` / `NewSkinWeightProfile`；编辑操作枚举 `EWeightEditOperation`、`EMeshTransferOption` 等。
- **评估**：**这是 UE 自带、可直接用于“买来的服装 FBX 重绑到目标骨架”的工具**，有 Source LOD、Source Skin Weight Profile 概念，支持“只对选中权重层传递”。对本项目是零新增依赖的方案。**限制**：它是 `MeshModelingToolsEditorOnly` 下的**交互式编辑器工具**，本会话未找到可在 commandlet / Python 批处理里直接调用的公开入口（`TransferWeights()` 是 `UObject` 成员，非蓝图/控制台命令），因此**能否纳入项目的后台脚本管线（`Tools/AssetPipeline/` 那套批次互斥做法）尚未验证**——这一点很关键，建议实测。

### 1.9 `TransferVertexSkinWeights`（同名易混淆，注意）

- 该 Dataflow 节点**不属于 Chaos Cloth**：Module 为 `GeometryCollectionNodes`，Category `GeometryCollection`，用于在 Geometry Collection 之间传递顶点蒙皮权重（`TransformNameSuffix` 默认 `_Tet`，与 `CreateTetrahedron` 节点配套），是**破碎/几何集合**体系的节点。
  URL: https://dev.epicgames.com/documentation/en-us/unreal-engine/node-reference/Dataflow/TransferVertexSkinWeights?application_version=5.8
- **对本项目的意义**：无用。列出仅为避免看到 Dataflow 节点列表时误用。

---

## 2. Blender 侧：拟合与权重传递

Blender 手册正文来源（官方手册源文件）。

### 2.1 Shrinkwrap Modifier（几何贴合）

- **是什么**：把被修改对象的每个顶点移动到目标网格表面最近点。Wrap Method：`Nearest Surface Point`、`Project`、`Nearest Vertex`、`Target Normal Project`。Snap Mode：`On Surface` / `Outside Surface` / `Above Surface` / `Inside` / `Outside`；有 `Offset`、`Vertex Group` 控制逐顶点影响。
- **来源**：https://projects.blender.org/blender/blender-manual/raw/branch/main/manual/modeling/modifiers/deform/shrinkwrap.rst
- **原文两条限制提示**：`Inside`/`Outside` “can be used for very crude collision detection. The inside vs outside determination is done based on the target normal and is not always stable near 90 degree and sharper angles in the target mesh.”；`Project` 模式支持 `Limit`、`Subdivision Levels`、轴向、`Face Cull`、`Auxiliary Target`。
- **评估**：**只做几何贴合，不产生骨骼权重**。适用场景是“把买来的衣服网格用 Offset 贴到 Manny 身体表面，消掉穿插”，作为权重传递前的**预处理**。它不能替代权重传递（服装导入 UE 后仍需要骨骼权重）。对贴身衣物（战术背心、护甲）效果直接；对宽松衣物（外套、长袍）会把布料压扁，需要配合顶点组只对局部生效。

### 2.2 Data Transfer Modifier + Transfer Mesh Data 操作符（**权重传递的事实标准**）

- **是什么**：把一个外部网格的数据（含 **vertex groups**、UV、color attributes、custom normals）传过来，对每个目标元素找源元素并插值。
- **来源**：
  - https://projects.blender.org/blender/blender-manual/raw/branch/main/manual/modeling/modifiers/modify/data_transfer.rst
  - https://projects.blender.org/blender/blender-manual/raw/branch/main/manual/scene_layout/object/editing/link_transfer/transfer_mesh_data.rst
- **可核实的关键机制**：
  - Data Type 说明中明确列出“e.g. **vertex groups**, UV maps...”。
  - **Mapping** 策略（这是精度的关键）：
    - `Topology`：按索引匹配，要求元素数量与顺序一致（“Best suited for a destination mesh that's a deformed copy of the source”）。
    - 一对一：`Nearest Vertex`、`Nearest Edge Vertex`、`Nearest Face Vertex`、`Nearest Edge`、`Nearest Face Edge`、`Nearest Corner and Best Matching Normal`、`Nearest Face`、`Best Normal-Matching`（沿法线投射找源面）。
    - **插值类（服装拟合最常用）**：`Nearest Edge Interpolated`、`Nearest Face Interpolated`、`Projected Face Interpolated`（沿目标顶点法线投到源面上再插值）、`Projected Edge Interpolated`、Face Corner 的两种插值、Face Data 的 `Projected Face Interpolated`。
  - `Generate Data Layers` / `Create Data`：**目标网格上不存在的顶点组必须先生成**，否则传递不生效（“The modifier doesn't do this automatically, so make sure to click this button”）。
  - `Layer Mapping`：目标层按**名称**或按**顺序**匹配。
  - `Only Neighbor Geometry` + `Max Distance`、`Ray Radius`（“use a low radius for dense source meshes and a high one for simple ones”）、`Islands Precision`。
  - `Mix Mode`：Replace / Above Threshold / Below Threshold / Mix / Add / Subtract / Multiply，配 `Mix Factor`。
- **评估**：**这是本项目最应该采用的权重传递方案**。理由：① 它直接产出 Blender 顶点组，Blender 导出 FBX 时就是 UE 的骨骼权重，中间不需要额外工具；② `Projected Face Interpolated` + `Max Distance` 的组合，恰好对应“服装离身体很近”的场景；③ 全部能力都是 Blender 内置，无新增依赖，无许可证问题，可以在 `Tools/PlayerBody/` 下的 Python 脚本里自动化（`bpy` 可驱动 modifier 与 `object.data_transfer` 操作符），符合项目“后台脚本 + 批次互斥”的既有做法。风险点是它对**远离身体表面的部件**（肩甲、腰带外挂）会取到错误的源面，需要配合顶点组和 `Max Distance` 分区处理。

### 2.3 Surface Deform Modifier（代理网格驱动精细网格）

- **是什么**：绑定后，一个网格的形变由另一个网格驱动。
- **来源**：https://projects.blender.org/blender/blender-manual/raw/branch/main/manual/modeling/modifiers/deform/surface_deform.rst
- **原文要点**：
  - 官方推荐用途：“One great use for this is to have a **proxy mesh for cloth simulation**, which will in turn drive the motion of your final and more detailed mesh”。
  - 目标网格有效性约束：**不能有超过两个面的边、不能有凹面、不能有重叠顶点、不能有共线边的面**。
  - `Interpolation Falloff`、`Strength`、`Vertex Group`、`Sparse Bind`（只对绑定时非零权重的顶点记录 bind 数据，之后往组里加顶点需要重新 bind）、`Bind`/`Unbind`。
  - 注意事项：“The meshes are bound with regard to global coordinates, but later transformations on the objects are ignored”；“The further a mesh deviates from the target mesh surface, the more likely it is to get undesirable artifacts … recommended to have reasonably well matching meshes”。
- **评估**：**这是“低模服装 → 高模服装”或“Sim Mesh → Render Mesh”的 Blender 侧对应物**，和 UE 的 Chaos Cloth render/sim mesh 概念一致。对本项目的用法是：先做一件低精度、严格贴合身体的“代理服装”，用 Surface Deform 驱动高精度外观网格；或者用代理网格去承接来自 body 的权重。**注意它不传权重**——它是形变驱动，不是蒙皮传递；不要把它和 Data Transfer 混用为一件事。

### 2.4 RetopoFlow

- **是什么**：Blender 的一套重拓扑工具（不是拟合工具）。
- **成熟度**：`CGCookie/retopoflow`，**3253 stars**，语言 Python，`pushed_at` **2026-09-16**，GitHub API 返回 `license: null`（**API 未识别到许可证**）。
  URL: https://github.com/CGCookie/retopoflow
- **评估**：**与“服装拟合”无关**，只在需要把扫描/生成的高模重拓扑成可蒙皮的低模时有用。列出是为了纠正“用 RetopoFlow 做服装拟合”这一可能的误解——它的描述是“A suite of retopology tools for Blender”。

### 2.5 `Furionk/mesh-data-transfer`（Data Transfer 的自动化封装）

- **成熟度**：**9 stars**，Python，**GPL-3.0**，`pushed_at` **2025-10-19**，仓库主页指向作者 Gumroad 页 `https://mmemoli.gumroad.com/l/tOKEh`；描述 “MeshDataTransfer Blender addon”。
  URL: https://github.com/Furionk/mesh-data-transfer
- **注意**：本会话**未能抓到该仓库 README 原文**（`raw.githubusercontent.com` 抓取失败），因此不对其具体功能做断言，只确认仓库存在与其元数据。
- **评估**：如果它确实是把 Shape Key / 顶点组 / 顶点色在多网格间传递的批量化封装，可以省掉自己写 `bpy` 脚本的功夫；但 9 stars、单人维护、README 未核实，**不建议把它作为管线关键依赖**。内置 Data Transfer 已足够。

### 2.6 `openfashion-labs/ac9_cloth_retopo`（CLO/MD 服装在 2D 版片形态下重拓扑）

- **是什么**：Blender 插件，在**平面版片（2D）形态**下对 CLO3D / Marvelous Designer 的服装网格做重拓扑，再投影到高模 Guide 上。
- **成熟度**：**39 stars**，Python，**GPL-3.0**，`pushed_at` **2026-09-17**，topics 含 `clo3d` / `marvelous-designer` / `retopology` / `garment`。
  URL: https://github.com/openfashion-labs/ac9_cloth_retopo
- **评估**：这是本次检索里**最贴近“服装资产进入引擎前的规范化处理”且仍在活跃维护的开源工具**。但它的定位是**重拓扑**，不是拟合到不同体型。适用场景：从 CLO/MD 拿到版片级网格后，产出干净的四边面服装网格再进 Blender Data Transfer 传权重。属于“可选增强”，不是必需。

### 2.7 其它 Blender 服装插件（存在性已确认，用途需注意）

| 仓库 | 是什么 | stars | license | pushed_at | URL |
| --- | --- | --- | --- | --- | --- |
| `cdrinmatane/Costumy` | 开源原型：把 2D 服装版片转成 3D 服装（基于 freesewing） | 33 | GPL-3.0 | 2025-04-03 | https://github.com/cdrinmatane/Costumy |
| `MarcelloMorettoni/opensew-2` | “Opensource plugin for clothing and garment design on Blender” | 7 | GPL-3.0 | 2026-08-26 | https://github.com/MarcelloMorettoni/opensew-2 |
| `elias-schwarze/bl-md-retopology` | 重拓扑 Marvelous Designer 服装的 Blender 插件 | 2 | GPL-3.0 | 2023-10-20 | https://github.com/elias-schwarze/bl-md-retopology |
| `V0ln0/BG3_Lazy_Tailor` | 名称暗示是 BG3 服装适配工具（**README 未抓取，不做功能断言**） | 1 | GPL-3.0 | 2026-05-20 | https://github.com/V0ln0/BG3_Lazy_Tailor |

**评估**：这些是**版片设计/重拓扑**方向，不是“把一件成衣网格拟合到另一个体型”的工具。`BG3_Lazy_Tailor` 的“Tailor”命名最像服装适配，但仓库 1 star、无描述、README 未取到，**不能作为方案依据**。

### 2.8 Faceform Wrap（原 R3DS Wrap）—— 商用，非开源

- **是什么**：拓扑传递工具。官网原文：“It's the industry leading **topology transfer** tool that helps creating digital characters based on 3D scans of real actors or sculpts”；使用场景包含 “Virtual Try On and Avatars — Wrap is suitable for converting full-body scans into a common topology for further rigging, animation, and **cloth simulation**”。
- **来源**：https://faceform.com/ （站点导航含 `Buy` 页 `https://customer.faceform.com/customer/buy/` 与 `Download` 页，站内 `Download`/`Buy` 明确表示这是**商业授权软件**）
- **评估**：功能上确实覆盖“把不同来源的网格拓扑统一”，是行业常用工具。但它是**闭源商业软件**，不在任务要求的“GitHub / 开源工具”范围内；引入它意味着采购与授权。**本会话未抓到价格与具体授权条款**（页面正文被截断），见文末。对本项目：不必需，Blender Data Transfer 能覆盖同类需求。

### 2.9 Auto-Rig Pro（Blender 商用插件）—— 注意 “Remap” **不是**服装拟合

- **是什么**：Blender 商用插件（作者 Artell，Superhive / 原 Blender Market）。官方产品页描述：“a Blender add-on to rig characters, **retarget animations**, and export to FBX/GLTF, with dedicated settings for Unity, Unreal Engine, Godot”。
- **来源**：https://superhivemarket.com/products/auto-rig-pro
- **“Remap” 的真实用途（原文）**：“The Remap feature allows **retargetting** of any armature **action** to another one, with different bone names and bone orientations, supporting imported .bvh/.fbx armatures… Define the source armature, the target armature, and the animation will retarget according to the bones names matches and bones original orientation.”
- **对本项目直接相关的部分（原文）**：Game Engine Export 中支持 “**Unreal Mannequin**：support Mannequin bones hierarchy, bone axes conversion, bones naming for UE4/UE5”、`Unit conversion`、`Multiple Twist Bones`、`Shape Keys` 导出、动作烘焙。
- **评估**：**纠正一个可能的误解**：Auto-Rig Pro 的 Remap 是**动画重定向（action → action）**，不是蒙皮权重传递，也不是服装拟合。它的价值在本项目是：① 导出到 UE 时对齐 **Unreal Mannequin 骨骼层级与骨骼轴向**，可用来把外部带骨架的服装 FBX 规范化到 Manny 命名；② 自动蒙皮（官方提示 “use water-tight geometry for best auto-skinning results”）。它是**付费闭源**插件，价格与许可条款见文末（本会话未从页面正文取到价格）。

---

## 3. 学术/研究型 garment fitting（含“不存在/名不副实”的澄清）

### 3.1 TailorNet

- **是什么**：CVPR 2020 (Oral)，把服装形变预测为人体姿态、体型与服装风格的函数。
- **成熟度**：`chaitanya100100/TailorNet`，**434 stars**，Python，GitHub API 许可证字段为 `other` / SPDX `NOASSERTION`（**即非标准许可证，需自行读 LICENSE 判断**），`pushed_at` **2022-03-04**（已停止更新约 4 年）。
  URL: https://github.com/chaitanya100100/TailorNet
- **评估**：学术最强项是“给定 pose/shape 预测衣服形变”。但它工作在 **SMPL 人体模型 + 自有服装模板**体系里，输出的是 SMPL 拓扑的顶点位移，**不产出 UE/Manny 骨骼权重，也不产出 UE 资产**。要用在本项目，必须先把 Manny 映射到 SMPL 再反向映射回来，工程量远超收益。**不建议**。

### 3.2 MultiGarmentNetwork

- **是什么**：ICCV'19，“Multi-Garment Net: Learning to Dress 3D People from Images”。
- **成熟度**：`bharat-b7/MultiGarmentNetwork`，**303 stars**，Python，GitHub API `license: null`，`pushed_at` **2022-10-12**，open issues 23。
  URL: https://github.com/bharat-b7/MultiGarmentNetwork
- **评估**：同 TailorNet——SMPL 体系、从图像/扫描重建服装，方向是“从观测得到衣服”，不是“把已有衣服适配到新身体”。**不适用**。

### 3.3 DrapeNet

- **是什么**：CVPR 2023，“Garment Generation and Self-Supervised Draping”。
- **成熟度**：`liren2515/DrapeNet`，**127 stars**，Python，**GPL-3.0**，`pushed_at` **2023-09-06**。
  URL: https://github.com/liren2515/DrapeNet
- **评估**：自监督生成+披挂，产物仍是研究用网格。**注意 GPL-3.0**：如果其代码被并入工具链并分发，会带来传染性许可问题；本项目仅用于**离线生成资产**（不链接进 UE 运行时）时风险较低，但需明确区分。**不推荐作为主线**。

### 3.4 ISP（Implicit Sewing Patterns）

- **是什么**：NeurIPS 2023，“Multi-Layered Garment Draping with Implicit Sewing Patterns”，多层服装披挂。
- **成熟度**：`liren2515/ISP`，**52 stars**，Python，GitHub API `license: null`，`pushed_at` **2025-04-24**。
  URL: https://github.com/liren2515/ISP
- **评估**：多层披挂与“上衣+裤子+外套叠加不穿插”这一实际问题相关，但仍是研究代码、无许可证声明（**无许可证意味着默认保留所有权利，不可直接商用**）。**不建议纳入生产管线**。

### 3.5 ClothWild（3D Clothed Human Reconstruction in the Wild）

- **是什么**：ECCV 2022，从单目图像重建穿衣服的人。
- **成熟度**：`hygenie1228/ClothWild_RELEASE`，**203 stars**，Python，`license: null`，`pushed_at` **2024-04-08**，topics `3d-clothed-human-reconstruction` / `cloth-reconstruction`。
  URL: https://github.com/hygenie1228/ClothWild_RELEASE
- **评估**：任务是**重建**（从图到网格），不是**适配**（服装→新身体）。**不适用**，且无许可证。

### 3.6 ClothCap

- **是什么**：ClothCap（SIGGRAPH 2017 相关工作），4D 扫描下的服装捕获/分割。
- **成熟度**：原始仓库 `jizhu1023/ClothCap`，**19 stars**，语言 **MATLAB**，`license: null`，`pushed_at` **2018-07-21**（**已停更 8 年**）。`xthan/ClothCap` 是 fork（2 stars）。
  URL: https://github.com/jizhu1023/ClothCap
- **评估**：MATLAB、停更多年、无许可证、面向 4D 扫描管线。**与本项目需求无关**。

### 3.7 “GarmentNet”——**澄清：不存在同名服装拟合项目**

- 检索到的 `real-stanford/garmentnets`（**68 stars**，Python，`license: null`，`pushed_at` **2023-03-06**）是 ICCV 2021 “GarmentNets: **Category-Level Pose Estimation** for Garments via Canonical Space Shape Completion”。
  URL: https://github.com/real-stanford/garmentnets
- **结论**：这是**服装位姿估计 / 规范空间形状补全**，与“把衣服拟合到身体”无关。**任务清单里的 “GarmentNet” 若指服装拟合，本会话未找到对应项目**；若指上述仓库，则用途不符。

### 3.8 “DRAPE”——论文存在，**未找到官方代码仓库**

- **论文**：DRAPE: DRessing Any PErson，ACM Transactions on Graphics Vol 31 No 4（2012）。
  URL: https://dlnext.acm.org/doi/10.1145/2185520.2185531
  URL: https://is.mpg.de/de/publications/drape2012
- **代码**：本会话**未找到该论文的官方代码仓库**。检索命中的 `aatishb/drape`（描述 “drape simulation software”）是**同名不同物**，本会话未抓取其 README，不做对应关系断言。
- **评估**：DrapeNet（3.3）是同一研究线的新版本，可用作参考实现。**不要把 DRAPE 当成可用工具。**

### 3.9 “DeepCloth”——论文存在，**未找到官方代码仓库**

- **论文 PDF**：`http://www.liuyebin.com/DeepCloth/files/paper.pdf`（“DeepCloth: Neural Garment Representation for Shape and Style Editing”）。
- **代码**：GitHub 搜索 `deepcloth` 仅返回 5 个无关小仓库（如 `kornellewy/deepcloth` “photo realistic tryon”，0 stars；`Meghaa27/DeepCloth` “Product Recommendation and Virtual Cloth Try-On”，0 stars），**未发现该论文的官方实现**。
- **评估**：无法评估实现可用性。**不作为候选。**

### 3.10 libigl（`bounded biharmonic weights` 等的实现库）

- **是什么**：C++ 几何处理库，tutorial 第 4 章 “Shape Deformation” 包含 `Bounded Biharmonic Weights`、`Dual Quaternion Skinning`、`Fast Automatic Skinning Transformations`、`Direct Delta Mush`、`Biharmonic Coordinates` 等；第 7 章含 `Closest Points`、`Signed Distance`、`Iterative Closest Point`。
  URL: https://libigl.github.io/tutorial/
- **成熟度**：`libigl/libigl`，**5090 stars**，C++，`pushed_at` **2026-09-21**（非常活跃）。**许可证字段有矛盾**：GitHub API 的 `license` 返回 **GPL-3.0**，而仓库 description 写的是 “Simple **MPL-2.0**-licensed C++ geometry processing library”，tutorial 页也提到随附下载的 CoMiSo 是 GPL3 且“does impose restrictions on commercial usage”。
  URL: https://github.com/libigl/libigl
- **评估**：如果将来要做**自研**的权重求解（bounded biharmonic / geodesic voxel binding），libigl 是成熟底座；而且它的 `Fast Automatic Skinning Transformations` 与 `Direct Delta Mush` 是“少骨高质量变形”的现成实现。但对本项目，**当前阶段用 Blender Data Transfer + UE 内建工具已足够，引入 libigl 只增加 C++ 构建与许可复杂度**。若要引入，**必须先读仓库根目录 LICENSE 与其 `LICENSE.GPL`/`LICENSE.MPL2` 文件确认适用条款**（本会话确认 API 与描述不一致，见文末）。

---

## 4. UE 模块化角色 / 换装系统的 GitHub 项目

### 4.1 `asee5g/Character-Customization`

- **是什么**：UE5 的模块化角色自定义系统（C++ + Blueprint），演示动态换网格、UI 驱动定制、相机聚焦过渡、存档读取。
- **成熟度**：**1 star**，C++，`license: null`，`pushed_at` **2026-03-05**。
  URL: https://github.com/asee5g/Character-Customization
- **评估**：思路（mesh swap + UI + 存档）与项目已有做法高度重合，但 1 star、无许可证（**默认不可再分发/商用**）、无可核实文档。**只可作代码参考，不可直接引入。**

### 4.2 `alice-bian/crowd-diversity-pipeline`（**方向最接近的开源管线**）

- **是什么**：描述原文 “A Blender ➔ Unreal Engine 5 pipeline that procedurally generates diverse crowds by automating **USD garment export, skeleton reassignment, and randomized outfit assembly across a shared character rig**”。
- **成熟度**：**0 stars**，Python，`license: null`，`pushed_at` **2026-07-27**，仓库体积仅 186 KB，创建于 2026-06-25。
  URL: https://github.com/alice-bian/crowd-diversity-pipeline
- **注意**：本会话**未能抓到 README**（`raw.githubusercontent.com` 抓取失败），因此只能依据仓库描述字段判断。
- **评估**：概念上**正是本项目需要的形状**——Blender 侧自动化服装导出 + 骨架重指派 + 在共享 rig 上随机组合 outfit。但：0 stars、无许可证、单作者、极新、代码量极小（186 KB，大概率是脚本原型而非成熟管线）。**结论：作为“流程设计参考”阅读，不要作为依赖。** 其中“skeleton reassignment（骨架重指派）”这一环节值得优先看它怎么做的。

### 4.3 `nulla-sutra/unreal-ditto`

- **是什么**：描述 “Combee-powered outfit equipment framework for Unreal Engine”，C++。
- **成熟度**：**0 stars**，**MPL-2.0**，`pushed_at` **2026-07-02**，体积 129 KB。
  URL: https://github.com/nulla-sutra/unreal-ditto
- **评估**：唯一一个在描述里自称 “outfit equipment framework” 的 UE C++ 仓库，且是 MPL-2.0（许可证清晰、可商用）。但 0 star、依赖一个未核实的 “Combee”（topics 里是 `bee`）。**可以花 30 分钟读一下它的组件组织方式，但不建议依赖。**

### 4.4 `Voidware-Prohibited/ALSXT`

- **是什么**：把 ALS-Refactored 扩展成“模块化、GAS 驱动、data-oriented”的 UE5 角色系统插件。
- **成熟度**：**347 stars**，C++，GitHub API 许可证字段 `other` / SPDX `NOASSERTION`，`pushed_at` **2026-04-14**，默认分支 `stable`，open issues 6。
  URL: https://github.com/Voidware-Prohibited/ALSXT
- **评估**：它是**角色/动画系统**，不是换装系统。对本项目唯一价值是“大型模块化角色系统的工程组织方式”参考。许可证非标准，需读仓库内 LICENSE。

### 4.5 `poly-hammer/character-dna-addon`

- **是什么**：把 MetaHuman 的 head/body 组件按 DNA 文件导入 Blender、定制后再送回 MetaHuman Creator。
- **成熟度**：**289 stars**，Python，**GPL-3.0**，`pushed_at` **2026-09-22**（非常活跃），forks 51，open issues 31。
  URL: https://github.com/poly-hammer/character-dna-addon
- **评估**：与服装无关，但它对应项目未来的**脸部建模/捏人**目标（若走 MetaHuman 路线则是关键工具）。若本项目坚持 Manny 而非 MetaHuman，则此工具不适用。列出是为了把“服装拟合”和“捏人”两条线的工具区分清楚。

### 4.6 检索到的负面结果（重要）

以下查询在 GitHub 仓库搜索 API 上返回 **`total_count: 0`**（即在仓库名/描述/主题层面没有匹配项目）：

| 查询 | 结果 |
| --- | --- |
| `unreal modular character outfit` | 0 个仓库 |
| `skin weight transfer unreal` | 0 个仓库 |
| `metaHuman wardrobe` | 0 个仓库 |
| `blender addon cloth fit` | 0 个仓库 |

其它弱结果：`outfit unreal` 仅 3 个仓库，其中 2 个（`Jasmine5220/fashion-show-prototype`、`alice-bian/crowd-diversity-pipeline`）与“服装资产管理”沾边，1 个（`nulla-sutra/unreal-ditto`）是换装框架。

**结论**：**不存在一个“UE 模块化换装 / 服装拟合”的成熟开源插件可以直接拿来用。** 本项目已有的 `FPSPlayerBodyEquipment` + `player_body.json` 配置驱动方案，在开源生态里已经属于做得比较靠前的位置；后续工作的正确方向是**把离线拟合步骤脚本化**，而不是找一个插件替换现有系统。

---

## 5. 推荐路线

按“与现有架构契合度 × 可重复性 × 不引入不可控依赖”排序。

### 路线 A（首选）：Blender 内置 Data Transfer 权重传递 + 现有 Leader Pose 挂载

**管线**
1. **参考网格**：从 UE 导出 Manny 身体网格（`SKM_Manny_PlayerSkin` 或其源网格）为 FBX，作为 Blender 侧的**权重源**。要求：与身体同骨架、同 rest pose（项目已有 `-90°` 朝向与 `-96 cm` 偏移的既定默认值，见 `player-body-20260921.md`，导出时必须保持）。
2. **几何预处理**：外部服装网格导入后，用 **Shrinkwrap**（`Nearest Surface Point` 或 `Project` + `Offset`）修正与 Manny 身体的明显穿插/浮空。宽松衣物只对局部顶点组生效，避免整体压扁。
3. **权重传递**：对服装网格添加 **Data Transfer modifier**：Source = Manny 身体网格，Data Types 勾选 **Vertex Groups**，`Generate Data Layers` 建立缺失顶点组，Mapping 用 **`Projected Face Interpolated`**（贴身件）或 **`Nearest Face Interpolated`**（离体件），开启 **`Only Neighbor Geometry` + `Max Distance`** 防止远距离误匹配，`Mix Mode = Replace`。分区复杂时按部件拆成多个顶点组分别传。
4. **校验与修正**：导出前检查服装是否有**多余的骨骼顶点组**（Leader Pose 要求服装骨架是身体的严格子集，多骨会在 reference pose 下渲染）；用 UE 的 `SkinWeightsPaintTool`（1.8）做少量修正与 `Relax`。
5. **入库**：导出的 `SK_*` 与骨架与 Manny 一致，写入 `player_body.json` 的 `outfits.<id>.world_mesh`，运行时沿用现有 Leader Pose 路径挂载；遮挡继续按现有 `hide_body_materials` 材质区索引处理。

**为什么最适合**
- 完全落在项目**已有的 config-driven 结构**里——不改 `player_body.json` 语义，不加新资产类型，不改运行时挂载方式。
- 全内置工具（Blender 官方 modifier + UE 官方编辑器工具），**无第三方依赖、无许可证风险**。
- **可脚本化**：`bpy` 能驱动 Shrinkwrap / Data Transfer modifier 与 `object.data_transfer` 操作符，符合项目“默认后台脚本完成、不主动开编辑器”的既定做法（`AGENTS.md`）。
- 满足 Leader Pose 的硬约束（网格为骨架严格子集），是**唯一不需要对 1.1 的官方限制做妥协**的方案。

**已知代价**：服装不能有独立布料模拟（1.1 / 1.5 的限制）；遮挡仍是材质区粒度而非几何级（项目文档已如实记录这一点）。UE 的 `SkinWeightsPaintTool` 能否进脚本管线**待验证**（1.8）。

### 路线 B（次选，中期）：Chaos Cloth Asset + Dataflow `TransferSkinWeights`

**管线**：服装做成 Chaos Cloth Asset → 在 Dataflow 图里用 `TransferSkinWeights`（`InpaintWeights` + `RadiusPercentage` 0.05 + `NormalThreshold` 30 + `LayeredMeshSupport`）从身体 Skeletal Mesh 传权重 → 需要手工保留的权重区用 `InpaintMask` 排除 → 渲染网格用 `TargetMeshType` 的 render mesh 分支。

**为什么排第二**
- 它是 **UE 官方、能力最完整的自动权重传递**，参数化程度高于 Blender Data Transfer（法线阈值、分层、平滑、inpaint 掩码、最大 8 影响骨），且产出直接就是引擎内的 cloth 资产，为后续布料模拟铺路。
- 但代价明确：① 引入 `ChaosClothAsset` / `ChaosClothAssetEditor` 插件依赖与新的资产类型，`world_mesh` 字段的语义要扩展；② **与 Leader Pose 的布料绑定冲突**（1.5 原文要求 mesh 一致），意味着挂载方式可能要改成 Copy Pose from Mesh，从而接受 Game Thread 成本上升；③ Dataflow 图的构建与调参对新人是学习成本，且部分是编辑器内交互操作，脚本化程度需实测。

**适用判断**：当“布料模拟”从“以后想要”变成“明确需求”时启动；在此之前不必引入。

### 路线 C（明确不推荐，列出以排除）

- **MetaHuman Parametric Outfit Asset（1.6）**：这是 UE 官方唯一的多体型方案，但要求 MetaHuman Creator 插件 + Core Data + MetaHuman SDK 打包路径，且官方文档整体落在 MetaHuman 体系下；本项目是 Manny 骨架，**是否可用未经验证**（推断），且 `MakeOutfit` 仍标 Experimental，5.6 说明里“resize 时覆盖自定义权重”的行为与项目保留自定义材质的诉求存在冲突风险。**建议只作为多体型阶段的调研对象，不要现在投入。**
- **学术生成式拟合（TailorNet / MultiGarmentNetwork / DrapeNet / ISP / ClothWild，第 3 节）**：全部工作在 SMPL 体系、多数无许可证声明或为 GPL-3.0、多数已停更 2–4 年、**不产出 UE 骨骼权重**。要接入需先建立 Manny↔SMPL 的对应关系，工程量与风险远超收益。
- **Faceform Wrap（2.8）/ Auto-Rig Pro（2.9）**：闭源商业软件。功能可用，但引入采购与授权流程；Blender 内置工具已能覆盖本项目当前需求。Auto-Rig Pro 的 Remap 是**动画重定向**而非权重传递，不能当作拟合工具。
- **Skeletal Mesh Merge（1.3）**：牺牲 morph target（与未来捏人冲突），强制材质 atlas 化，只解决 draw call 不解决拟合。

---

## 6. 不确定/需要验证

以下条目**未能从一手来源证实**，不应作为已确认事实使用。

1. **Chaos Outfit Asset 可否用于非 MetaHuman 骨架（如 Manny）**：官方参数化服装文档位于 MetaHuman 文档分类下，并要求 MetaHuman Creator 插件与 Core Data（1.6）。我据此**推断**它至少不以 Manny 为主要目标场景，但**未能找到任何明确说明“支持/不支持任意骨架”的一手文档**。需实测或查 UE 源码 `ChaosOutfitAssetEngine`。
2. **UE 5.7/5.8 中 resizable clothing 是否仍会在缩放时覆盖自定义权重**：1.6 引用的“simple skin weight transfer from the body, and overwrites all of it”这句话明确限定为 **UE 5.6**。5.7/5.8 的行为我**未核实**。
3. **`TransferSkinWeights` 是否有官方的“手工指定部分权重”之外的分区能力**：我只核实了 `InpaintMask` 这一个开关，未找到更多文档。
4. **Chaos Cloth Asset 是否可直接挂在 Leader Pose 子组件上工作**：1.5 的 `BindClothToLeaderPoseComponent` 明确要求 mesh 一致，因此我推断需要走 Copy Pose from Mesh；但**“Chaos Cloth Asset + Copy Pose from Mesh”的组合是否被官方支持，我未找到文档**。
5. **“Clothing Tool 已废弃（deprecated）”**：任务描述中提到“Clothing Tool (deprecated APEX cloth)”。我抓到的 UE 5.2 官方 Clothing Tool 页面**正文中没有任何 deprecated/废弃字样**，该页面还写明底层是 Chaos Cloth solver（而非 APEX）。**我无法从一手来源确认废弃状态**，也未找到 APEX 相关的官方说明。
6. **“Proxy Mesh / Mesh Clipping”作为 UE 服装遮挡特性**：任务描述中的这一组功能名，我**未找到任何 Epic 官方文档页面**。`USkeletalMeshComponent::BindClothToLeaderPoseComponent`、Clothing Tool、Modular Characters 三处均未出现 “proxy mesh” 或 “mesh clipping”。**不排除是我未检索到，但在本会话内不能确认其存在。**
7. **UE 5.8 版本说明中与 Chaos Cloth / Outfit 相关的条目**：我**没有**逐条枚举 UE 5.8 Release Notes（页面过大，未完整抓取）。因此“UE 5.8 对布料/换装做了什么改动”在本报告中**完全没有覆盖**。若需要，应单独抓取 `unreal-engine-5-8-release-notes` 并搜索 cloth/outfit 关键词。
8. **UE `SkinWeightsPaintTool` 能否纳入后台/脚本管线**：1.8 只确认了 C++ 类与函数存在（`TransferWeights()`、`CanTransferWeights()`、`SetSourceMesh()`）。**是否可通过 Python/commandlet 调用，未验证**。
9. **`libigl` 的实际许可证**：GitHub API 返回 `GPL-3.0`，仓库描述写 `MPL-2.0`，tutorial 页提到随附的 CoMiSo 为 GPL3。**三者不一致，我未读仓库内 LICENSE 文件**。在决定使用前必须自行确认。
10. **`Furionk/mesh-data-transfer` 的实际功能**：仓库存在性与元数据已确认，但 **README 抓取失败**，其“传递哪些数据类型、是否支持顶点组/形态键”的具体能力**未核实**。
11. **`alice-bian/crowd-diversity-pipeline` 的具体实现**：仓库描述命中需求，但 **README 抓取失败**，其“skeleton reassignment”的实际做法**未核实**。
12. **`V0ln0/BG3_Lazy_Tailor` 的功能**：无仓库描述，**README 未抓取**，只能确认它是一个 1 star、GPL-3.0、2026-05-20 更新的 Python 仓库。**不能断言它是服装拟合工具。**
13. **Faceform Wrap 的价格与具体授权条款**：官网抓取正文被截断，只确认它为商业软件（有 Buy/Download 页与 “Request Trial”/“Request Academic License” 入口）。**价格、授权模式未核实。**
14. **Auto-Rig Pro 的价格与授权**：产品页正文被截断，未取到价格数值与许可证条款文本。
15. **“Cloth Fitting” / “Fit Clothes” Blender 插件**：任务清单里点名的这两个名字，**我未能找到任何对应的仓库或产品**；GitHub 搜索 `blender addon cloth fit` 返回 0 结果。**不排除其存在于付费平台（如 BOOTH/Gumroad）而未被 GitHub 检索覆盖**——检索中确实出现了一个日文 BOOTH 商品 “VRC衣装フィッティングツール / Outfit Fitter - HatoTools”（`https://booth.pm/en/items/8035665`），但**我未抓取该页面，不对其能力/授权做任何断言**。
16. **“learning to fit garments”**：该精确短语未对应到任何一个我确认存在的项目/论文，**未做进一步断言**。
17. **Blender 官方手册网页直连失败**：`docs.blender.org` 返回 HTTP 403（Cloudflare）。本报告中的 Blender 依据来自**同一官方手册的 `.rst` 源文件**（`projects.blender.org/blender/blender-manual`）。内容权威性等同，但**页面结构与在线版本可能有差异**。

---

## 附录：本报告实际抓取（`web_fetch` 成功且正文可用）的来源清单

**Epic 官方（dev.epicgames.com）**
- Working with Modular Characters in Unreal Engine (5.7) — https://dev.epicgames.com/documentation/en-us/unreal-engine/working-with-modular-characters-in-unreal-engine?application_version=5.7
- TransferSkinWeights (Dataflow, 5.8) — https://dev.epicgames.com/documentation/en-us/unreal-engine/node-reference/Dataflow/TransferSkinWeights
- MakeOutfit (Dataflow, 5.7) — https://dev.epicgames.com/documentation/en-us/unreal-engine/node-reference/Dataflow/MakeOutfit?application_version=5.7
- TransferVertexSkinWeights (Dataflow, 5.8) — https://dev.epicgames.com/documentation/en-us/unreal-engine/node-reference/Dataflow/TransferVertexSkinWeights?application_version=5.8
- Getting Started with Parametric Clothing (5.7) — https://dev.epicgames.com/documentation/en-us/unreal-engine/getting-started-with-parametric-clothing?application_version=5.7
- Parametric Asset Setup for MetaHuman (5.8) — https://dev.epicgames.com/documentation/en-us/metahuman/parametric-asset-setup-for-metahuman?application_version=5.8
- Clothing Tool in Unreal Engine (5.2) — https://dev.epicgames.com/documentation/en-us/unreal-engine/clothing-tool-in-unreal-engine?application_version=5.2
- USkeletalMeshComponent::BindClothToLeaderPoseComponent (5.7) — https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Engine/USkeletalMeshComponent/BindClothToLeaderPoseComponent?application_version=5.7
- UWeightToolTransferManager (5.7) — https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Plugins/MeshModelingToolsEditorOnly/UWeightToolTransferManager?application_version=5.7
- USkinWeightsPaintToolProperties (5.7) — https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Plugins/MeshModelingToolsEditorOnly/USkinWeightsPaintToolProperties?application_version=5.7

**Blender 官方手册源文件（projects.blender.org）**
- Shrinkwrap Modifier — https://projects.blender.org/blender/blender-manual/raw/branch/main/manual/modeling/modifiers/deform/shrinkwrap.rst
- Surface Deform Modifier — https://projects.blender.org/blender/blender-manual/raw/branch/main/manual/modeling/modifiers/deform/surface_deform.rst
- Data Transfer Modifier — https://projects.blender.org/blender/blender-manual/raw/branch/main/manual/modeling/modifiers/modify/data_transfer.rst
- Transfer Mesh Data（操作符） — https://projects.blender.org/blender/blender-manual/raw/branch/main/manual/scene_layout/object/editing/link_transfer/transfer_mesh_data.rst

**GitHub API（元数据）**
`liren2515/DrapeNet`、`liren2515/ISP`、`jizhu1023/ClothCap`、`chaitanya100100/TailorNet`、`bharat-b7/MultiGarmentNetwork`、`hygenie1228/ClothWild_RELEASE`、`real-stanford/garmentnets`、`libigl/libigl`、`CGCookie/retopoflow`、`Furionk/mesh-data-transfer`、`V0ln0/BG3_Lazy_Tailor`、`MarcelloMorettoni/opensew-2`、`openfashion-labs/ac9_cloth_retopo`（经 `search/repositories`）、`cdrinmatane/Costumy`（同上）、`elias-schwarze/bl-md-retopology`（同上）、`asee5g/Character-Customization`、`alice-bian/crowd-diversity-pipeline`、`nulla-sutra/unreal-ditto`（经 `search/repositories`）、`Voidware-Prohibited/ALSXT`、`poly-hammer/character-dna-addon`。

**商业产品页**
- Faceform Wrap — https://faceform.com/
- Auto-Rig Pro — https://superhivemarket.com/products/auto-rig-pro
- libigl tutorial — https://libigl.github.io/tutorial/
- DRAPE 论文条目 — https://is.mpg.de/de/publications/drape2012
