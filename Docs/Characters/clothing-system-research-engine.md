# 人物装备与衣物：引擎内置成熟方案调研

2026-09-23。本机宿主 `D:/FPS3D/FPSGAME`，UE 5.8.2。

本文只回答一个问题：**拿到一件衣服模型后，如何让它贴合人物模型、并在不同体型/不同人物之间做调整和裁剪。** 结论全部来自本机 UE 5.8 引擎源码（一手证据）与 Epic 官方在线文档，不用推测补全功能。

调研的起点是项目现状：玩家全身为 Manny（`SKM_Manny_Simple` / 骨架 `SK_Mannequin`），全身皮肤已换成独立 `SKM_Manny_PlayerSkin`，`Content/ColdSteelData/player_body.json` 的 `outfits` 目前为空，衣物接入方式是「共用骨架 + Leader Pose + 隐藏身体材质区」。相关背景见 [玩家全身模型与双套动画](player-body-20260921.md) 与 [全身表现经验](../../skills/ue5-cpp-gameplay/references/player-world-body.md)。

---

## 0. 先分清「三件不同的事」

用户描述的「贴合、调整、裁剪」实际是三个可以独立解决的技术问题，混在一起才显得没有成熟方案。引擎里它们分别对应不同工具：

| 问题 | 含义 | 引擎对应能力 |
| --- | --- | --- |
| **A. 适配（fit / reshape）** | 衣服是按甲体型做的，要穿到乙体型上，表面得跟着变形 | Mutable `Mesh Reshape`、Chaos `Outfit Asset` 的 RBF 重定尺寸 |
| **B. 包裹（wrap）** | 衣服拓扑和身体完全不同，需要把衣服「包」到身体表面 | Mutable `MeshWrap`、`Mesh Warp`（GeometryScript `WrapMesh`） |
| **C. 遮挡与裁剪（clip / hide）** | 衣服盖住的地方身体不能穿出来 | Mutable `Clip With Mesh`、材质区隐藏（项目现用）、Chaos Cloth 碰撞 |

三者的成熟度差别很大：**A 和 C 有官方成熟系统；B 是实验性功能。** 下面逐项给出源码级证据。

---

## 1. Chaos Outfit Asset —— 官方「把衣服适配到不同体型」的正式系统

这是本次调研最重要的发现，也是 Epic 自己推荐的正规路线。

### 它是什么

`ChaosOutfitAsset` 是 UE 5.8 内置插件（`Engine/Plugins/ChaosOutfitAsset`），但**默认不启用**：

```json
"FriendlyName": "Chaos Outfit Asset",
"Description": "Outfit Asset plugin to create and assemble outfits made of Cloth Assets.",
"EnabledByDefault": false,
"IsBetaVersion": true,
"Plugins": [
    { "Name": "ChaosClothAsset", "Enabled": true },
    { "Name": "Dataflow", "Enabled": true },
    { "Name": "MeshResizing", "Enabled": true },
    { "Name": "ChaosClothAssetEditorCore", "Enabled": true, "TargetAllowList": ["Editor"] }
]
```

（证据：`Engine/Plugins/ChaosOutfitAsset/ChaosOutfitAsset.uplugin`）

注意它把 **`MeshResizing` 作为依赖**——也就是说，Epic 的正式适配方案是建立在 MeshResizing 的算法之上的。这不是两套竞争方案，而是同一套算法分成「引擎层」和「资产层」。

### 适配机制：RBF 插值重定尺寸

核心结构体 `FChaosSizedOutfitSource` 的注释把机制说得很清楚（`ChaosOutfitAssetEngine/Public/ChaosOutfitAsset/SizedOutfitSource.h`）：

- `SourceAsset`：这一体型对应的衣物资产。「每个尺寸必须是**完全相同的衣服表示**」——即同一件衣服的多份体型副本。
- `SourceBodyParts`：「构成该尺寸源身体的骨骼网格列表。通常是单个 MetaHuman 合并的 身体+头部 骨骼网格。」
- `NumResizingInterpolationPoints`（默认 `DefaultNumRBFInterpolationPoints`，范围 0–5000）：「重定尺寸算法中使用的插值点数量。这些点**均匀分布在整个身体上**。增加该数值会提高重定尺寸质量，但代价是初始生成可调整衣物时的开销，以及 Outfit 在磁盘上的体积。**如果你发现调大这个数值仍无法得到可接受的调整结果，我们建议新增一个 Size。**」

这段原文直接定义了成熟方案的**质量模型**：靠增加「源体型数量」来保证质量，而不是靠无限提高拟合精度。这是选用该系统时必须接受的工程约束。

官方文档进一步补充了设计意图与已知限制（[Getting Started with Parametric Clothing](https://dev.epicgames.com/documentation/metahuman/getting-started-for-creating-parametric-clothing-in-metahuman)）：

> The **Outfit Asset** is a new chaos cloth asset type... It then warps the clothing based on the difference between the source body and a new body with different measurements (target body).
>
> In some cases, the source body and target body are too different, which can cause warping. This is especially the case with more realistic and detailed (not stylized or simplified) clothing. Due to this, we encourage you to create multiple outfits for multiple source bodies... Our system automatically detects which source body is the best match for each new target body and selects the appropriate source clothing to resize from.

**要点**：系统会自动为每个目标体型挑选最接近的源体型。所以「多源体型」是设计的一部分，不是 workaround。

### 关键限制（决定它能不能用在本项目）

1. **它是围绕「合并的 身体+头部 网格」设计的，且依赖测量值。** 官方流程要求启用 **MetaHuman Creator** 插件并从 Epic Games Launcher 下载 **MetaHuman Creator Core Data**，`Outfit Asset` 默认落在 `/Game/Outfits`（[Parametric Asset Setup](https://dev.epicgames.com/documentation/metahuman/parametric-asset-setup-for-metahuman)）。

   引擎侧证据：`ChaosOutfitAsset/Public/ChaosOutfitAsset/BodyUserData.h` 定义了一个挂在网格上的 `UChaosOutfitAssetBodyUserData`：

   ```cpp
   /** Asset user data attached to the merged body and face skeletal mesh. */
   class UChaosOutfitAssetBodyUserData : public UAssetUserData
   {
       static inline constexpr float InvalidMeasurement = 0.f;
       UPROPERTY(VisibleAnywhere, Category = "Measurements")
       TMap<FString, float> Measurements;
   };
   ```

   这说明系统的输入契约是「**一个合并的 身体+头部 骨骼网格 + 一组命名的人体测量值**」。这一点很重要：它是**数据契约**，而不是写死的 MetaHuman 类。

   **测量值的确切键名已从源码查明**（`ChaosOutfitAssetEngine/Private/ChaosOutfitAsset/CollectionOutfitFacade.cpp`，`FBodyMatchParameters` 构造函数）：

   | 键名 | 说明 |
   | --- | --- |
   | `Hip` | 臀围 |
   | `Bust`（缺失时回退 `Chest`） | 胸围。源码注释：`Bust has been replaced by Chest after the 5.6 preview 1 and before the 5.6 release` |
   | `Underbust` | 下胸围 |
   | `Waist` | 腰围 |
   | `Neck to Waist` | 颈到腰 |
   | `Rise` | 立裆 |
   | `Inseam` | 内长（腿内侧长） |

   缺任何一个都会被判为 `InvalidMeasurement`。系统用它们推导身体形状分类（源码里的 `EBodyShape`：`Triangle` / `InvertedTriangle` / `Circle` / `Hourglass` / `Rectangle`，判据是 `Hip/Bust` 与 `((Bust+Hip)/2)/Waist` 的阈值），以及 `bIsProtruding = (Underbust / Bust) <= 0.88`。随后 `FindClosestBodySize(Measurements)` 用这些参数在多个源体型里挑最接近的一个。

   **所以硬门槛不是「必须是 MetaHuman」，而是「必须提供这 7 个命名测量值」。** 任何骨骼网格都能挂 `UAssetUserData`，理论上 Manny 也可以填这 7 个值。但要注意这套判据明显是为**女性/中性体型**设计的（`Bust`/`Underbust`/`Hourglass`）；给男性 Manny 填表时这些比例会退化到少数几个分类，**是否仍能得到可用适配未经实测**（见第 7 节第 3 条）。
2. **标记为 Beta，默认关闭。**
3. **衣服必须是 Cloth Asset，不是普通骨骼网格。** Outfit Asset 官方定义为「一种新的 chaos cloth 资产类型」，「必须包含一个或多个 cloth asset」。这意味着**采用它 = 采用 Chaos Cloth Asset 作为衣物载体**。

### 与本项目的关系

- 项目的 Manny 骨架不是 MetaHuman 骨骼。**不能直接把 Outfit Asset 套到 `SKM_Manny_PlayerSkin` 上。**
- 要吃到这套成熟适配能力，**前置条件是「把玩家全身从 Manny 换成 MetaHuman 身体」**。这是一个方向性决策，代价是重做全身动画适配（当前 59 条 Manny 动作、足部 IK、蹲姿调整都建立在 Manny 骨架上）。
- 反过来说：如果接受 MetaHuman 身体，则**适配问题、多体型问题、布料模拟问题一次性全部由官方系统解决**，这正是「成熟方案」的含义。

---

## 2. Mesh Resizing（`MeshWrap` / `MeshWarp`）—— 引擎里的通用拟合算法

这是独立的实验性插件 `Engine/Plugins/Experimental/MeshResizing`，`IsExperimentalVersion: true`，默认关闭。它是 Outfit Asset 的算法底座，但**也可以脱离 MetaHuman 单独使用**，所以对本项目意义更大。

### `MeshWrap`：把一件衣服的拓扑「包」到另一个形状上

来自 `MeshResizingNodes/Public/MeshResizing/MeshWrapNode.h`：

> Node for wrapping one mesh's topology to another mesh's shape. Uses point landmarks defined by the Mesh Wrap Landmarks node to match corresponding points between the two meshes.

输入输出很清楚：

- `SourceTopologyMesh`：「具有期望包裹后拓扑的输入网格」——即**衣服**（我们要保留它的 UV、布线、材质分区）。
- `TargetShapeMesh`：「具有期望包裹后形状的输入网格」——即**身体**。
- 输出 `WrappedMesh`：「输出包裹后的网格」。

**这是「用身体的形状，穿衣服的拓扑」**——正好是用户问的「贴合」。这个方向是对的：衣服的美术资产（UV/布线/材质）全部保留，只把顶点位置拉到身体表面。

算法是可调的迭代求解，参数很有信息量：

| 参数 | 默认 | 含义（源码注释） |
| --- | --- | --- |
| `MaxNumOuterIterations` | 10 | 外循环上限；每轮把 Projection Stiffness 乘一次倍率 |
| `NumInnerIterations` | 20 | 每轮外循环前跑的内循环数 |
| `ProjectionTolerance` | 1e-4 | 投影容差，达到即提前结束 |
| `LaplacianStiffness` | 1.0 | 「保留 Source Topology 网格特征的权重」 |
| `InitialProjectionStiffness` | 0.1 | 初始贴合目标形状的权重 |
| `ProjectionStiffnessMuliplier` | 10.0 | 每轮外循环的投影刚度倍率 |
| `CorrespondenceStiffness` | 1.0 | 地标对应点的权重 |

（注意源码里 `ProjectionStiffnessMuliplier` 是 Epic 的拼写错误，引用时照抄以免搜不到。）

**地标（landmark）机制是质量的关键**：`FMeshWrapLandmark` 用字符串 `Identifier` 命名，在衣服和身体上各标一份，同名即配对（`FMeshWrapCorrespondence`）。也就是说**自动包裹 + 手工地标微调**，这正是「成熟方案」应有的样子：先给自动结果，再给人工纠正手段。

配套工具：`MeshResizingEditorTools` 里有 `UMeshWrapLandmarkSelectionTool`，即编辑器里点选生成地标。源码注释提到自动包裹「might still require」手工指定某些 landmark，说明它自己承认自动解不总是够用。

### `MeshWarp`：两种变形方式

`MeshWarpNode.h` 定义了 `EMeshResizingWarpMethod`：

```cpp
enum struct EMeshResizingWarpMethod : uint8
{
    WrapDeform,
    RBFInterpolate
};
```

- 输入：`MeshToResize`（要变形的网格）、`SourceMesh`（源身体）、`TargetMesh`（目标身体）。
- 输出：`BlendedTargetMesh`、`ResizedMesh`。
- `Alpha`（0–1）：融合程度——**可以做单件衣服的适配强度渐变**。
- `NumInterpolationPoints` 默认 100；`bInterpolateNormals` 默认 true。

这条路径的语义是「**身体从 A 体型变到 B 体型，把这件衣服按同样的形变搬过去**」——即上面说的「适配」。它比 MeshWrap 更接近 Outfit Asset 的实际做法。

### 关于 `MeshResizingEngine` 的诚实说明

`MeshResizingEngine` 模块**只有 `MeshResizingEngine.Build.cs`，没有公开头文件或实现文件**（`Get-ChildItem` 递归结果确认）。因此该模块在当前引擎安装里的公开 API 不可用；能确定的只有 `MeshResizingCore` / `MeshResizingDataflowNodes` / `MeshResizingEditorTools` 三个模块。**不要假设存在一个可直接调用的运行时重定尺寸引擎类。**

### 与本项目的关系

- 这是**唯一可以在保留 Manny 骨架的前提下使用官方拟合算法**的途径。
- 代价：插件实验性、无公开文档、只能通过 Dataflow 资产使用，且 `MeshResizingEngine` 未公开 API。
- `MeshWrap` 的语义（保拓扑、换形状）非常适合「Fab 买的衣服 → 套到 Manny 身上」这个具体场景。

---

## 3. Mutable —— 引擎内的完整换装/裁剪工具箱

`Engine/Plugins/Mutable`，Epic 官方插件（另有 `Experimental/MutableClothing`、`MutablePopulation` 等）。本项目**当前未启用**。

Mutable 提供的是节点图（Customizable Object），把「换装、裁剪、变形、合并、材质切换」做成可配置运行时管线。与本次调研直接相关的节点：

### `Mesh Reshape` —— 官方适配原语

`MutableTools/Internal/MuT/NodeMeshReshape.h`：

```cpp
Ptr<NodeMesh> BaseMesh;      // 要变形的网格（衣服）
Ptr<NodeMesh> BaseShape;     // 衣服原本适配的源身体形状
Ptr<NodeMesh> TargetShape;   // 想要的新身体形状
bool bReshapeVertices = true;
bool bRecomputeNormals = false;
bool bApplyLaplacian = false;
bool bReshapeSkeleton = false;          // 骨骼也跟着重塑
bool bReshapePhysicsVolumes = false;    // 物理体也跟着重塑
TArray<FName> BonesToDeform;
TArray<FName> PhysicsToDeform;
// 顶点色 RGBA 四通道可作 ClusterId / MaskWeight
```

**它同时能重塑顶点、骨骼和物理体**，这是很实用的一点：衣服适配到新体型时，碰撞体不会留在旧位置。

实现证据（`MutableRuntime/Private/MuR/OpMeshReshape.cpp`）：

- 绑定数据 `FReshapeVertexBindingData` 存在 `EMeshBufferSemantic::BarycentricCoords` 通道（`check(BarycentricDataChannel == 1)`）——即**每个衣服顶点记录它落在源身体哪个三角形的重心坐标**，然后按 base→target 的形状差把顶点搬过去。
- 有 `SmoothMeshLaplacian(*Mesh, bRemoveData)` 做拉普拉斯平滑。
- 关键警告（源码原文）：

  > `"Performing a Mesh Reshape where base shape and target shape do not have the same number of triangles."`

  **`BaseShape` 和 `TargetShape` 必须有相同的三角形数。** 也就是说这套 reshape 适用于「**同一个身体的不同体型/形态**」（同拓扑、不同比例），**不能**把一件衣服直接适配到拓扑完全不同的另一个角色身上。跨拓扑要用上面的 `MeshWrap`。

- `EMeshBindShapeFlags`（`MutableRuntime/Internal/MuR/Operations.h`）列出全部能力位：`ReshapeSkeleton`、`EnableRigidParts`、`ReshapePhysicsVolumes`、`ReshapeVertices`、`ApplyLaplacian`、`RecomputeNormals`、`ReshapeSkeletonInvertSelection`、`ReshapePhysicsVolumesInvertSelection`。注意 **`EnableRigidParts`**——允许衣服的部分区域保持刚性不参与变形（例如金属扣、徽章），这对军事风格装备很重要。

### `Clip With Mesh` —— 官方裁剪

`CONodeSkeletalMeshClipWithSkeletalMesh` / `ASTOpSkeletalMeshClipWithMesh`：用另一个网格去裁掉当前网格的部分。这就是用户问的「裁剪」，且是网格级真实裁剪，不是材质区隐藏。

### 其他相关节点

- `CONodeModifierSkeletalMeshMerge` / `NodeSkeletalMeshMerge`：把多件衣物合并成一个骨骼网格（**降 draw call**，而项目当前每件衣物是一个独立组件 + Leader Pose）。
- `CONodeSkeletalMeshMorph` / `MeshMorph` / `MeshMorphStack`：形态目标驱动，做体型滑条。
- `CONodeModifierMorphMeshSection`、`ClipMorph`：分区变形与裁剪。
- `NodeSkeletalMeshTransformWithBone`：按骨骼做局部变换。
- `CustomizableObjectNodeMeshReshapeCommon` / `...Details`：编辑器侧节点与细节面板。

### 与本项目的关系

- Mutable 是**唯一同时覆盖「适配 + 裁剪 + 合并 + 骨骼/物理体重塑」的引擎内方案**，且不要求 MetaHuman。
- 它是节点图工具，学习成本高于「手动在 DCC 里改好再导入」，适合确定要做**成体系换装**（多件组合、多体型、运行时切换）之后再引入。
- 引入需要启用插件并接受一个编辑器内制作流程（本项目规则允许短批次编辑器操作）。

---

## 4. Chaos Cloth Asset —— 布料模拟（不是拟合）

`Engine/Plugins/ChaosClothAsset`。它是 **simulation**，解决「衣服动起来」而不是「衣服穿上去」。

对本项目有用的两点：

1. `UChaosClothComponent` 的源码注释确认支持 **Leader Pose**：
   > `If this component has a valid LeaderPoseComponent then this makes cloth items on the follower component...`

   即布料组件可以跟随一个骨骼网格，这与项目现有的 Leader Pose 习惯一致。

2. **关于「旧版骨骼网格布料编辑器已废弃」——我无法证实，请勿据此决策。**

   我最初依据的只是一条搜索结果摘要（措辞为「As cloth simulation and complex clothing become more widely requested in-engine, our legacy skeletal mesh cloth editor and workflow...」）。后续核对**未能证实**：GitHub 调研分任务独立检查了 UE 5.2 官方 Clothing Tool 页面正文，**没有任何 deprecated 字样**，且该页写明底层就是 Chaos Cloth solver。

   附带一条**可确证**的相关事实：`USkeletalMeshComponent::BindClothToLeaderPoseComponent()` 的头文件注释原文为

   > The meshes used in the components must be identical for the cloth to bind correctly

   出处：`Engine/Source/Runtime/Engine/Classes/Components/SkeletalMeshComponent.h`。同处还有一个 5.1 就标记废弃的旧名：`UE_DEPRECATED(5.1, "This method has been deprecated. Please use BindClothToLeaderPoseComponent instead.")`。

   **这条约束很关键**：它意味着「Leader Pose 挂独立服装网格」与「该服装自己跑布料」不能同时成立——要布料就得改用 Copy Pose from Mesh 或 Mesh Merge。

3. **Chaos Cloth Asset 自带官方「自动权重传递」节点。** 已在本机核实其存在：

   - `Engine/Plugins/ChaosClothAssetDataflowNodes/Source/ChaosClothAssetDataflowNodes/Public/ChaosClothAsset/TransferSkinWeightsNode.h` 与同名 `.cpp`
   - 编辑器侧工具 `ChaosClothAssetEditorTools/Private/ChaosClothAsset/ClothTransferSkinWeightsTool.{h,cpp}`，及 `ClothEditorCommands` / `ClothEditorMode` 中的入口

   也就是说：**把外部服装的蒙皮权重从身体自动传过来，UE 官方在 Cloth Asset 流程里有现成节点**，不必只依赖 Blender 的 Data Transfer。这对「买到未绑定或绑定不对的服装」这一实际场景很有价值。

   ⚠️ 节点的具体参数（插值方式、影响骨数上限、法线阈值等）我只确认了文件存在，**未逐项读取参数含义**。GitHub 分任务报告称其为 `InpaintWeights` / `InpaintMask` / 最大 8 影响骨，**这部分我未独立复核**。

**结论**：新做衣物若需要布料模拟，选型时**优先考虑 Chaos Cloth Asset**（它是当前活跃的资产类型，官方参数化服装体系建在其上）；旧的 `Clothing Tool` 状态**未经证实，不要以「已废弃」为理由排除或采用**。

**本项目现状（已核对）**：`Source/FPSGAME/FPSGAME.Build.cs` 当前链接的是**旧版**布料模块，而不是 Chaos Cloth Asset：

```csharp
PrivateDependencyModuleNames.AddRange(new[] { "ClothingSystemRuntimeCommon", "ClothingSystemRuntimeInterface" });
if (Target.bBuildEditor) PrivateDependencyModuleNames.AddRange(new[]
{
    "ClothingSystemEditor", "ClothingSystemEditorInterface",
    "ChaosCloth"
});
```

即 `ClothingSystem*`（旧系统）+ `ChaosCloth`（底层解算）。**没有** `ChaosClothAsset`。项目里也没有任何衣物资产（`player_body.json` 的 `outfits` 为空），所以这些依赖目前是**预留而未使用**的。若确定走 Chaos Cloth 路线，这套依赖需要重评为 `ChaosClothAsset`。

---

## 4.5 换装挂载方式：官方三选一，以及 Leader Pose 的硬上限

本项目当前用的是 **Leader Pose**。Epic 有一篇专门的官方文档 [Working with Modular Characters](https://dev.epicgames.com/documentation/en-us/unreal-engine/working-with-modular-characters-in-unreal-engine)，把模块化角色的三条路线和代价列为一张表（原文照录）：

| | Leader Pose Component | Copy Pose from Mesh | Skeletal Mesh Merge |
| --- | --- | --- | --- |
| **Setup Cost** | Min | Medium | High |
| **Game Thread Cost** | Min | High | Medium |
| **Render Thread Cost** | High | High | Low |
| **Physics** | No | **AnimDynamics** or **RigidBody** | Yes |
| **Morph Target** | Yes | Yes | No |

### Leader Pose 的硬上限（官方原文，直接约束本项目）

> It is also important to know that any child mesh object of the Leader Bone has to be a subset with the exact matching structure. **You cannot have any other extra joints or skip any joints.** Since there is no Bone Buffer data for extra joints, **any extra or skipped joints will be rendered using the reference pose.**
>
> Child Mesh objects contained within a Modular Character blueprint **cannot run unique animations, or simulate physics independently** from the Leader Pose component.

**引擎源码独立佐证了这段话**，不是单纯照抄文档。`SkinnedMeshComponent.cpp::UpdateLeaderBoneMap()` 对 follower 每个骨骼做名字查找，leader 里没有的骨骼映射为 `INDEX_NONE`：

```cpp
for (int32 BoneIndex = 0; BoneIndex < LeaderBoneMap.Num(); BoneIndex++)
{
    const FName BoneName = FollowerRefSkeleton.GetBoneName(BoneIndex);
    LeaderBoneMap[BoneIndex] = LeaderRefSkeleton.FindBoneIndex(BoneName);
}
```

而 `GetMissingLeaderBoneRelativeTransform()` 的处理方式是：**沿父链向上找到 leader 里存在的共同祖先，然后用 follower 自己的参考姿态把该骨骼定位到祖先上**：

```cpp
FTransform RelativeTransform = BoneSpaceRefPoseTransforms[InBoneIndex];
int32 CommonAncestorBoneIndex = InBoneIndex;
while (CommonAncestorBoneIndex != INDEX_NONE)
{
    CommonAncestorBoneIndex = FollowerRefSkeleton.GetParentIndex(CommonAncestorBoneIndex);
    if (CommonAncestorBoneIndex != INDEX_NONE)
    {
        OutInfo.CommonAncestorBoneIndex = GetLeaderBoneMap()[CommonAncestorBoneIndex];
        if (OutInfo.CommonAncestorBoneIndex != INDEX_NONE)
        {
            OutInfo.RelativeTransform = RelativeTransform;
            return true;
        }
        RelativeTransform = RelativeTransform * BoneSpaceRefPoseTransforms[CommonAncestorBoneIndex];
    }
}
```

**结论（对项目直接相关）**：
- 带**独立动画**的附加骨（裙摆骨、披风骨、飘带骨、马尾骨）在 Leader Pose 下**拿不到动画数据**，会停在参考姿态。文档与源码在这里是一致的。
- 现状意味着：**「Leader Pose 挂独立服装网格」与「服装有自己的布料/附加骨动画」在官方路径下不能兼得**。要做裙摆飘动，必须换 Copy Pose from Mesh（Game Thread 成本上升）或 Skeletal Mesh Merge。
- **不需要额外骨的模块化服装**（头盔、护甲片、背包、纯贴身的衣裤鞋）用 Leader Pose 完全够用，且 Game Thread 成本最低。这也解释了为什么项目现有接口是合理的。

---

## 5. 方案对比矩阵

「附加骨」列对应第 4.5 节的硬约束一（Leader Pose 下附加骨拿不到独立动画），是当前**最先需要回答**的取舍。

| | 保留 Manny | 适配不同体型 | 网格裁剪 | **附加骨/独立物理** | 布料模拟 | 成熟度 |
| --- | --- | --- | --- | --- | --- | --- |
| **现状（Leader Pose + 材质区隐藏）** | ✅ | ❌ | ❌（仅材质区） | ⚠️ 有骨但**不参与动画** | ❌ | 已接入，最简 |
| **Copy Pose from Mesh** | ✅ | ❌ | ❌ | ✅ | ✅ 用 RigidBody/AnimDynamics | 官方，Game Thread 贵 |
| **Skeletal Mesh Merge** | ✅ | ❌ | ❌ | ✅ | ✅ | 官方，但**牺牲 morph target** |
| **Mutable** | ✅ | ✅ 同拓扑 | ✅ | ✅ | 需另接 Chaos Cloth | 官方插件，节点图 |
| **MeshResizing（MeshWrap/MeshWarp）** | ✅ | ✅ 可跨拓扑 | ❌ | ❌ | ❌ | 实验性 |
| **Chaos Outfit Asset** | ⚠️ 需 7 项测量值契约 | ✅ 官方最佳 | 由 Cloth Asset 处理 | ✅ | ✅ | Beta，默认关闭 |
| **MetaHuman 全套** | ❌ 换骨架 | ✅ | ✅ | ✅ | ✅ | 官方推荐，代价最大 |

---

## 6. 市场与开源方案的合并结论

GitHub 开源工具与 Fab 资产市场的调研结果分别记录在 `clothing-fitting-research-github.md` 与 `clothing-fitting-research-fab.md`。

**推荐路线的最终排序见 [调研汇总与推荐路线](clothing-system-research-synthesis.md)。** 简版结论：

- **首选（立即可做）**：Blender 离线权重传递（Shrinkwrap + Data Transfer）+ 现有 Leader Pose 挂载。零新增依赖，且是唯一不违背第 4.5 节 Leader Pose 硬约束的方案。
- **次选（中期）**：Chaos Cloth Asset + `TransferSkinWeights` 节点（该节点已在本机核实存在）。布料模拟需求明确后再上。
- **排除**：为服装换 MetaHuman 骨架。
- **开源生态负面结论（已核实）**：GitHub 上 `unreal modular character outfit`、`skin weight transfer unreal`、`metaHuman wardrobe`、`blender addon cloth fit` 搜索结果均为 **0 个仓库**，不存在可直接用的成熟开源换装/拟合插件。

---

## 7. 不确定 / 需要验证

按项目规则，以下内容我**没有**验证，不应当作已确认事实使用：

1. **UE 5.7 发布说明中布料编辑器废弃的确切措辞** —— Epic 文档站正文本轮多次抓取失败（只返回目录骨架）。需在编辑器内或换用可抓取的镜像确认。
2. **`MeshResizing` 各节点在本项目 `FPSGAME` 中能否直接启用** —— 未做启用测试。它与 `Dataflow`、`GeometryCollectionPlugin`、`GeometryProcessing`、`HairStrands` 有依赖，未验证与本项目现有插件集（PCG、Vibe3D 等）的实际共存情况。
3. **Chaos Outfit Asset 是否严格要求 MetaHuman 骨骼** —— 官方文档的措辞是「通常是一个 MetaHuman 合并网格」，这是描述性而非限制性表述；引擎侧的 `UChaosOutfitAssetBodyUserData` 也只是「挂在合并网格上的一组测量值」，**没有出现任何 MetaHuman 专属类**。测量值键名已查明（见第 1 节）。所以从代码看它更像一个数据契约而非硬绑定。**但用 Manny 填这 7 个值能否得到可用适配未经实测**，且其体型判据（`Bust`/`Hourglass` 等）明显偏女性/中性体型，男性 Manny 填表后可能退化到少数分类。这是决定「要不要换 MetaHuman」的关键问题，值得优先验证。
4. **Mutable `Mesh Reshape` 的「同三角形数」限制对实战的影响** —— 源码警告确认了限制存在，但没有实测过本项目若做「Manny 瘦/胖体型」时结果质量如何。
5. **`MeshResizingEngine` 模块为何没有公开源码** —— 只确认了文件缺失这一事实，未查明原因（可能是安装时未附带，或模块已合并）。
6. 全部视觉质量、性能开销、打包体积影响**均未测试**。按项目规则，不主动启动 PIE、不截图、不验收渲染。

---

## 8. 建议的下一步

完整排序与理由见 [调研汇总与推荐路线](clothing-system-research-synthesis.md) 第 5 节。针对本引擎报告的要点：

- **不由本报告单独拍板方向。** 关键的新增输入是第 4.5 节的 Leader Pose 硬约束（官方原文 + 源码双向确认）：**带附加骨的服装在 Leader Pose 下不可用**。它把「要不要换挂载方式」和「要不要用裙摆/披风类资产」绑定在一起，是比「Manny vs MetaHuman」更早需要回答的问题。
- **优先验证第 7 节第 3 条**（Chaos Outfit Asset 用 Manny + 7 项测量值的实际质量），因为它是「Manny 能否吃到官方自动适配」的唯一硬门槛，验证成本远低于选错方向的返工成本。
- **同时确认「旧版 Clothing Tool 是否废弃」**（第 7 节第 4 条）。我此前基于搜索摘要的判断**已被独立核对推翻**，在确证前不要用它做决策。
