# Door System（Fab 6e79a6ea）接入评估与方案（2026-09-17）

用户已下载并放入本地：`D:\FPS3D\DoorSystem`（独立 UE **5.5** 工程，约 1 GB），同一份也在 Vault 缓存 `D:\FPS3D\VaultCache\FabLibrary\Door_System-6e79a6ea`。本文只做只读评估与接入方案，未复制、未修改任何资产。

## 1. 包内实际内容

| 目录 | 内容 | 接入需要 |
| --- | --- | --- |
| `Content/DoorSystem/Blueprints/Doors` | 11 个门 Actor 蓝图（AutoDoor、DragDoor、KeyDoor、KeyDoorAutoClose、PhysicsDoor、PhysicsDoubleDoor、RotatingDoor(s)、RotatingPhysicsDoors、SlidingDoors、WrongSideDoor）＋枚举 `E_DoorStates`、`E_WrongDoorSideStates` | 是（核心） |
| `Content/DoorSystem/Blueprints/Key` | `BP_Key`、`BP_AutoCloseDoorKey` ＋钥匙网格／材质贴图 | 视是否要钥匙门 |
| `Content/DoorSystem/Player/Blueprints` | `BI_Interact`／`BI_GrabObjects`（蓝图接口）、`BP_ThirdPersonCharacter`（交互驱动）、GameMode | 接口必需；角色不需要 |
| `Content/DoorSystem/Player/Input` | Enhanced Input：`IA_Interact`、`IA_DragDoor`、`IA_Move/Look/Jump/Sprint`、`IMC_Default` | 拖门／物理门需要 |
| `Content/DoorSystem/Player/Widgets` | `WBP_MainHud`、`WBP_WrongSide` | 仅 WrongSideDoor 需要 |
| `Content/DoorSystem/Demo` | 人体模型动画（≈900 MB）＋ StarterContent；**门的网格 `SM_Door`／`SM_DoorFrame` 就在这里**（键门直接引用 `Demo/StarterContent/Props/*`） | 不能整包丢弃，至少领这两个网格及其材质贴图 |

门的实现方式（读资产字符串得到，未进编辑器反编译）：

- 全部是 `AActor` 蓝图，各自带 SCS 组件（`DefaultSceneRoot`、`Box`、`Door`／`DoorFrame` 网格），实现蓝图接口 `BI_Interact` 的 `OnInteraction`。
- 自动门／滑动门：`Box` 的 Begin／EndOverlap 触发，`FInterpTo`／`Lerp` ＋ Timeline 曲线（`OpenDoor__UpdateFunc`、`Door_Timer`）驱动旋转／位移。
- 键门：`Keys` 数组 ＋ `HasKey?` 判定，Timeline 开合；`BP_Key` 用 `GetAllActorsOfClass` 把钥匙登记进门。
- 拖门／物理门：`bSimulatePhysics`、角阻尼／角偏移 ＋ Enhanced Input `IA_DragDoor`（角色里做视线追踪抓取，`GrabbedActor`）。
- **关键依赖**：门的 `OnInteraction` 流程里把传入玩家 `Cast` 成 `BP_ThirdPersonCharacter`（自动门里可见 `K2Node_DynamicCast_AsBP_Third_Person_Character` ＋ `CastFailed`），并调用它自己的 `IsInteracting?` 之类节点；换句话说，**交互入口与玩家侧追踪都在包的角色里**。

## 2. 我们工程现状（接入落点）

- 交互：`ColdSteelWorldInteraction::TraceTarget(PC, 250 cm)` 返回准星命中的 Actor；`AFPSGAMEPlayerController::InputKey` 的 E 分支现在只处理仓库箱、地面拾取与传送门，反馈走 `UColdSteelStatusModel::PostNotice`。没有通用的「E 交互提示」控件。
- 建造：构件（`FVoxelBuildPrefab`）只有 `Mesh`＋`Footprint`＋`Surface`＋`PivotOffsetCm`＋`Material`，落地是 `AVoxelBuildPrefabActor`（单个 StaticMeshComponent ＋ 碰撞），存档只记 `Id／Cell／Yaw／Footprint`，读档按调色板定义重新生成。**带逻辑／动画的门无法作为现有构件**。
- 地图：`GameMaps/DayNight_Lighting` 等主地图目前没有任何门（也无 EBS 引用）。
- 已有但闲置：`Content/EasyBuildingSystem/**` 里已有一套门（`BP_EBS_Building_Door`、门框、门锁、音效），纯蓝图、引用它自己的框架资产，只在 EBS 自带 Demo 地图中使用过。它更适合「整套基地建造框架」，与本次 Doore System 那套「现成可交互门」定位不同。

## 3. 方案（可增量，按代价从低到高）

### A. 只搬「重叠触发」门（最快可见）
移植 `BP_AutoDoor`／`BP_SlidingDoors`（＋其网格材质），直接放进世界或房子门口。它们靠 `Box` 重叠开合，对任何 Pawn 生效，**不需要**我们的角色实现包的接口。适合先看效果。

外观建议：包里的门网格取自它自己的 `Demo/StarterContent`（默认灰模），风格与本项目不符。我们工程里已有可用的门网格，移植时把门的 `Door` 组件换成它们即可，既统一风格又少带 StarterContent：

- `UnrealNormandy/StaticMeshes/SM_Door_00A`（村屋木门）、`SM_H_OldWall_Door_00A`（带门洞的老墙）、`Blockout/SM_WallBlock_Door_00A`；
- `SD_Art/Industrial_Infrastructure/Assets/Wall_Panels/SM_Door`、`SM_Door_Windowed`、`SM_Door_Fake`（工业／金属门，含 `MI_Windows_Doors_01*` 与 PBR 贴图）。

### B. E 键接上门的 `OnInteraction`（推荐主线）
1. 迁移 `Blueprints/{Doors,Key}`、`Player/Blueprints/BI_Interact`、被引用的 `Demo/StarterContent/Props` 网格与其材质贴图（保持 `/Game/DoorSystem/...` 路径）。
2. 把各门 `OnInteraction` 里的「Cast 成 `BP_ThirdPersonCharacter`」改成 Cast 到我们的 `AFPSGAMECharacter`（或改成不依赖具体角色），删／替换它调用的包角色函数（`IsInteracting?` 等）。
3. 控制器 E 分支新增一支：命中的 Actor 若实现了 `BI_Interact`（C++ 侧用 `UClass::ImplementsInterface`／`FindFunction("OnInteraction")` 判断，不需要 C++ 依赖蓝图类）→ 调用它、消耗输入，并在提示栏播报「已开门／需要钥匙」。
4. 同时给准星或提示栏加「E 开门」提示（沿用现有提示栏，不新建控件）。

### C. 让门能「建造」（建筑面板里放门）
给 `FVoxelBuildPrefab` 加可空 `TSoftClassPtr<AActor> ActorClass`；`AVoxelBuildWorld::SpawnPrefab` 里若 `ActorClass` 有效就生成门的 BP（否则维持现在的静态网格路径）。占用／拆除／存档沿用现有 `PrefabCells`／`Prefabs`（存 `Id/Cell/Yaw/Footprint`，旧档无需迁移）；调色板里加木／石门条目（占格按门框 1×2×2 或实测尺寸）。这样建筑面板「其他构造」里就能放门、拆门、随建筑一起保存。

### D. 拖门／物理门（建议最后做或不做）
需要把 `IA_DragDoor` 与抓取（`BI_GrabObjects`）接进我们的 Enhanced Input 与角色逻辑（我们的角色已有武器／互动占用状态，需处理互斥）。工作量最大。

### 钥匙的两种口径
- 沿用包内做法：钥匙是场景里可捡的 `BP_Key`，登记到门的 `Keys` 后即可开门（不需要我们背包）。
- 打通冷钢背包：把门里 `HasKey?` 改成查我们的档案（`UColdSteelStatusModel` 的物品／`CountMaterial`），钥匙变成 `items.json` 里的正式物品（含图标、堆叠、存档）。这属于扩展，包本身不提供。

## 4. 迁移与来源记录

- 机械步骤：用 5.8 编辑器打开 `DoorSystem.uproject`（会提示转换 5.5→5.8）或在其 Content Browser 里 **Migrate** 选定资产到 `FPSGAME`，保持 `/Game/DoorSystem/...` 路径以免引用断裂；只带需要的目录，跳过 `Demo/Characters`（≈900 MB）与 Demo 地图。
- 许可与来源：Fab 素材按 Fab EULA 在工程内使用；按项目惯例需在 `Docs/AssetSetup.md` 或随资产 `provenance.json` 记录来源（listing `6e79a6ea`）、获取日期、引擎版本 5.5→5.8、用途与是否改动。本地无法读取 Fab 页面（HTTP 403），具体许可条款需在页面确认后照录。

来源与去向（2026-09-17 迁移，用户明确要求接入）：

| 来源 | 去向 | 数量／体积 |
| --- | --- | --- |
| `D:\FPS3D\DoorSystem\Content\DoorSystem\Blueprints\Doors\**` | `D:\FPS3D\FPSGAME\Content\DoorSystem\Blueprints\Doors\**` | 13 个（11 门＋2 枚举） |
| `…\Player\Blueprints\{BI_Interact,BPI_Interact,BI_GrabObjects,BPI_GrabObjects,BP_ThirdPersonCharacter}` | `…\Content\DoorSystem\Player\Blueprints\` | 5 个（接口＋包角色；角色只用于满足门的参数类型，不参与玩法） |
| `…\Player\Widgets\{WBP_MainHud,WBP_WrongSide}`、`…\Player\Input\{IMC_Default,Actions\*}` | 同路径 | 9 个 |
| `…\Demo\StarterContent\{Props\SM_Door,Props\SM_DoorFrame,Props\Materials\M_Door,Props\Materials\M_Frame,Materials\M_Glass,Textures\T_Door_M/N,Textures\T_Frame_M/N}` | 同路径 | 9 个（门的默认外观；后续可换成 `UnrealNormandy/SM_Door_00A` 等自有网格） |
| **未复制** | — | `Demo/Characters`（≈900 MB 人体动画）、`Demo` 地图与其余 StarterContent、`Blueprints/Key`（先不做钥匙） |

原始下载仍完整保留：`D:\FPS3D\DoorSystem`（UE5.5 工程）与 `D:\FPS3D\VaultCache\FabLibrary\Door_System-6e79a6ea`（Fab 缓存）。许可条款待用户在 Fab 页面确认后补录到本文与 `Docs/AssetSetup.md`。

## 5. 待用户决定

1. 门用在哪里：只做世界／房子里可交互的门（A＋B），还是玩家建造基地时能放门（＋C），或两者都要？
2. 钥匙是否与冷钢背包打通（正式钥匙物品），还是沿用包内「场景捡钥匙」？
3. 是否需要拖门／物理门（D，代价最大）。

选定范围后按阶段实施：先做 A/B 的可见效果，再按需加 C/D。

## 6. 用户决定与实施进度（2026-09-17）

用户决定：**A＋B＋C，先不做钥匙**（Key 目录与钥匙物品暂不接入，键门资产保留备用）。D（拖门／物理门输入）暂缓。

已完成：

| 项 | 内容 | 证据 |
| --- | --- | --- |
| A/B 资产迁移 | 复制 29 个文件（11 个门蓝图＋2 个枚举、4 个蓝图接口、包角色、2 个门网格／3 个材质／4 张贴图）＋7 个 Enhanced Input 资源到 `Content/DoorSystem/**`，共 5.4 MB；未带 `Demo/Characters`（≈900 MB）与 Demo 地图 | `-run=pythonscript` 只读核对：11 个门全部 `bp=True class=True`，随后整体加载 0 error |
| B 接线（代码） | 新增 `Source/FPSGAME/Building/ColdSteelDoorInteraction.h/.cpp`（`UWorldSubsystem`）：准星命中的 Actor 实现 `BI_Interact` 或带约定入口（`OnInteraction`／`AutoDoorActivated`／`OpenDoor`…）即视为门；按入口函数的参数类型传玩家对象——参数是包自己的角色时，生成一个隐藏代理并同步玩家位置／朝向顶替；控制器 E 分支调用它并在提示栏播报 | `FPSGAMEPlayerController.cpp` E 分支新增一支 |
| C 逻辑构件（代码） | `FVoxelBuildPrefab` 新增可空 `ActorClass`＋`ActorOffsetCm`：留空仍是静态网格构件；填了就在 20 cm 格上生成该 Actor 并挂在占位记录下，占格／拆除／存档沿用原路径（旧建筑存档无需迁移） | `VoxelBuildPalette.h`、`VoxelBuildWorldPrefab.cpp`（`SpawnPrefab`／`CanPlacePrefab`／`RemovePrefab`）、`VoxelBuildPrefabActor.h` |
| 编译验证 | `FPSGAME Win64 Development` → **Result: Succeeded**，产物 `Binaries/Win64/FPSGAME.exe`，日志 `Saved/BuildEditor/door-game-build2.log` | 期间修正自身一处编译错误（`RemovePrefab` 里占位记录是 `AActor`）与一处遮蔽警告 |

编辑器关闭后完成的两步：

1. **编辑器模块构建**：`Tools/Build/Build-Editor.ps1` → `Result: Succeeded`，日志 `Saved/BuildEditor/build-20260917-095308.log`（新增 `UCLASS` 与结构体字段，必须原生构建，不能热补丁）。
2. **调色板登记两扇门**（C 的数据）：`add_door_prefab_entries_20260917.py` → `saved=True`，读回确认调色板现在有 4 个构件：`roman_column`(marble)、`baluster_small`(stone)、`door_auto`→`BP_AutoDoor_C`(wood)、`door_physics`→`BP_PhysicsDoor_C`(wood)。门框包围盒 24.8×114×212 cm → 占格 **(2, 6, 11)**（＝40×120×220 cm，含门框），`Mesh` 用 `SM_Door` 只做抽屉缩略图。

复现命令（编辑器关闭时）：

```
powershell -File D:\FPS3D\FPSGAME\Tools\Build\Build-Editor.ps1
"E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript -Script=D:/FPS3D/FPSGAME/SourceAssets/RomanColumn20260915/add_door_prefab_entries_20260917.py -unattended -nop4 -nosplash -NullRHI
```

实测提示（B 的兜底）：第一次按 E 操作某个门类时，子系统会把该类**所有可调用入口名**写进日志（`ColdSteelDoors: <类> 的可调用入口: ...`）。若某个门没有反应，把日志里那一行发我，我按真实函数名补进入口表即可——不需要改门的蓝图。

## 6.2 实测反馈与处置（2026-09-17 第二轮）

用户反馈：**交互门靠近按 E 打不开，只有提示栏有提示**。

日志证据（`Saved/Logs/FPSGAME.log`，PIE 会话）：

```
LogTemp: Display: ColdSteelDoors: 生成隐藏玩家代理 BP_ThirdPersonCharacter_C（门要求的参数类型）
PIE: Error: 蓝图运行时错误："尝试读取 /Game/DoorSystem/Blueprints/Doors/BP_AutoDoor.BP_AutoDoor_C
            中的 (real) 属性 Player Ref 时，结果为无"。节点：分支  图表：EventGraph
            函数：Execute Ubergraph BP Auto Door  蓝图：BP_AutoDoor      ← 每帧刷屏
```

结论：**E 键的调用确实到达了门**（代理生成日志 + 提示栏），但这扇门的逻辑里写死了包自己的角色：

- 资产里同时存在 `K2Node_Event_Player_Ref`／`K2Node_CustomEvent_Player_Ref`（接口参数 `Player Ref`）、
  `GetPlayerCharacter`、`K2Node_DynamicCast_AsBP_Third_Person_Character` 与 `PlayerIndex`；
- 换成我们的 `AFPSGAMECharacter` 后，门内部 Cast 失败、事件参数读不到，于是 Tick 里每帧报
  “读取 Player Ref 结果为无”，门自然不动。

也就是说：**包的交互门不能靠“从外部调用 OnInteraction”直接复用**，要么逐扇改门的蓝图图（把参数与
`GetPlayerCharacter` 换成我们的角色），要么由我们自己的门承担交互。本轮采用后者：

1. 新增 `Source/FPSGAME/Building/ColdSteelDoor.h/.cpp`（`AColdSteelDoor`）：单扇平开门＋门框，
   带 `ToggleDoor / OpenDoor / CloseDoor / IsDoorOpen` 入口，Tick 里按 `OpenSeconds` 线性转动铰链，
   可选 `AutoCloseSeconds` 自动关闭；门板／门框默认用包里的 `SM_Door`／`SM_DoorFrame`（换外观只改两个默认路径）。
2. `UColdSteelDoorInteraction` 的入口表把 `ToggleDoor` 提到最前（本工程的门优先，开关语义），并新增
   一次性日志：记录命中的入口名与参数签名，便于判断外来门是否又写死角色。
3. 调色板撤掉 `door_auto`（`BP_AutoDoor`，实测不可用），改为：
   `door_wood` → `/Script/FPSGAME.ColdSteelDoor`（木门·E 键开关）、`door_physics` → `BP_PhysicsDoor_C`
   （铁门·身体撞开，包的门不依赖角色接口，可直接用）。占格仍是 (2,6,11)。
4. 编辑器模块构建：`Tools/Build/Build-Editor.ps1` → `Result: Succeeded`（`build-20260917-104849.log`），
   调色板脚本重跑并读回：4 个构件 = 罗马柱／矮栏杆／`door_wood`(ColdSteelDoor)／`door_physics`(BP_PhysicsDoor)。

注意：**已在世界里放过的 `door_auto`（旧自动门）不会在下次读档时重新生成**（调色板里已无该条目），
拆除后按新条目重放即可。

## 6.3 门几何修复：悬空与门板/门框错位（2026-09-17 第三轮）

用户反馈：放置的交互门**悬空**，而且**门板与门框错位**。

原因（读代码 + 资产包围盒即可定位，不需要跑游戏）：

- `AColdSteelDoor` 起初按“组件 pivot = 包围盒中心”摆放：门框 `SetRelativeLocation(0,0,+BoxExtent.Z)`、
  门板放在铰链的 `(0,+45,+100)`。但 StarterContent 的 `SM_DoorFrame`／`SM_Door` 的 pivot 在**包围盒边缘**
  （门框在底边、门板在角上），于是：
  - 门框被整体抬高一个半高（≈106 cm）→ **悬空**；
  - 门板的包围盒中心相对铰链多偏了半个门宽（≈45 cm）→ **门板与门框错位**。

修复（[ColdSteelDoor.cpp](../../Source/FPSGAME/Building/ColdSteelDoor.cpp) 的 `AlignGeometry()`）：

- 一律以**包围盒**为基准、与 pivot 无关：
  - 门框：`Frame 相对位置 = (-Bounds.Origin.X, -Bounds.Origin.Y, Bounds.BoxExtent.Z - Bounds.Origin.Z)`
    → 包围盒在 X／Y 居中、底面正好在 z=0；
  - 门板：铰链放在门板左边缘 `(0, -BoxExtent.Y, 0)`，门板相对铰链
    `(-Bounds.Origin.X, BoxExtent.Y - Bounds.Origin.Y, BoxExtent.Z - Bounds.Origin.Z)`
    → 门板包围盒居中于门框洞口、底面与门框同高，开合仍绕 Z 轴。
- `BeginPlay` 会自动执行对齐，因此**已经放在世界里的门在读档重新生成时也会自动修正**（几何不再靠 pivot 假设）。
- 新增一次性自检日志：`ColdSteelDoor <名> 门框z=[..] 门板z=[..] 门框y=[..] 门板y=[..] 对齐=OK/CHECK`，
  直接给出两件几何体的世界包围盒，便于一眼确认贴地与对齐。

构建：`FPSGAME Win64 Development` → Succeeded（`Saved/BuildEditor/door-fix-game.log`）；
`Tools/Build/Build-Editor.ps1` → Succeeded（`build-20260917-111111.log`）。

边界：门板按 92° 开合，摆动半径 ≈90 cm，会扫到占格之外；若门框紧贴已建墙体，开门时门板可能穿墙。
需要的话下一步给门加"开门方向被挡则只开一半／拒绝开门"的检测。

## 6.1 实测步骤与已知边界（交给用户测试）

## 6.8 预览与落地口径、开关门静音、面板分类（2026-09-17 第八轮）

用户反馈三点，全部已改（编辑器模块 `UnrealEditor-FPSGAME.dll` 14:50:10，调色板 14:50:59）：

**① 门落地位置与预览有出入（体素开发时遇到过同类问题）**

根因是**预览与生成用了两套摆放口径**：

- 预览 `UpdatePrefabPreview()` 一律用 `AVoxelBuildPrefabActor::ComputeTransform()`——把网格**包围盒居中**于占格体积；
- `AVoxelBuildWorld::SpawnPrefab()` 对逻辑构件（门）却是“锚点在占格底面中心、构件自己往上搭”，
  而它判定分支看的是 `Mesh` 是否为空，门的 `Mesh`（缩略图用）非空 → 走了居中口径。
  门身高 200 cm，于是实际落地比预览高约一个半身高、水平也差半个门宽。

修复：

- `SpawnPrefab()` 改为按 **`ActorClass` 是否为空**分流：逻辑构件的锚点 = 占格底面中心；普通构件仍用 `ComputeTransform()`。
- `UpdatePrefabPreview()` 用同一口径：逻辑构件的 ghost 网格**底面对齐占格底面、X／Y 居中于占格**
  （`Centre − Rotate(Bounds.Origin) + (0,0,BoxExtent.Z) + PivotOffsetCm`）。
- 结果：预览与落地的门板位置重合（ghost 用的是门板网格，比门框矮 12 cm，属正常差异）。

**② 开关门不再有提示栏文案与音效**

提示栏（`UColdSteelProgressNotification`）自带升级音效，所以每次开门都会响。现在控制器 E 分支调用门入口后
**不再 PostNotice**（成功与失败都不占用提示栏），入口名仍写日志便于排查。

**③ 面板分类：材质栏只放对应材质的门，「其他」只放铁门**

- 代码：`RebuildCards()` 的「其他」分类改为只列**未归类**构件（调色板 `Material` 留空）；
  归到某栏材质的构件只在该材质的「其他构造」里出现，同一扇门不会两处重复。空列表文案改为「暂无未归类的其他构造…」。
- 调色板：`door_physics`（铁门）的 `Material` 置空 → 只在「其他」；三扇材质门保持各自归属：
  木材→木门、石头→石门、大理石→大理石门。铁门因此从木材栏移除。
- 同一规则的副作用：`roman_column`（大理石）与 `baluster_small`（石头）也不再出现在「其他」，
  只保留在对应材质栏下——符合「其他 = 未归类」的定义；若希望它们同时出现在「其他」，再加一个“同时列出”开关即可。

测试要点：预览与落地门板重合；按 E 开关门不再有提示栏文字与音效；木材／石头／大理石栏下各只有一扇对应材质的门，
「其他」里只有铁门。

## 6.7 开门方向跟随玩家 + 铰链改到把手对侧（2026-09-17 第七轮）

用户反馈两点：① 默认应该**朝玩家开门的方向**打开，而不是固定方向；② 现在门是从**把手对侧**开始打开，
要改成**从把手这一侧开始开**。

改动（[ColdSteelDoor.cpp](../../Source/FPSGAME/Building/ColdSteelDoor.cpp)）：

1. **默认方向跟随玩家**：`OpenDoor()` 先用 `TryGetPlayerSideSign()` 取本地玩家在门的哪一侧
   （门的本地 X 轴就是门板法线），然后取**玩家的反侧**作为首选开向——等价于“玩家把门推开”。
   只有在拿不到玩家位置（无本地玩家／玩家几乎贴在门平面上）时，才退回 `OpenAngleDegrees` 的符号作兜底。
2. **铰链换到把手对侧**：新增 `UPROPERTY(EditAnywhere) bool bHingeOnPositiveY`（默认 **true**）。
   此前铰链在本地 −Y，自由边在 +Y，而 +Y 正是把手对侧；现在铰链在 +Y，**自由边落在 −Y（把手这一侧）**，
   即“从把手这一侧开始开”。要镜像成另一只手的门，把该属性设为 false 即可（不影响每扇门各自的朝向）。
3. 开合角符号与世界侧的换算统一到 `AngleSignForWorldSide()`：铰链在 +Y 时同号、在 −Y 时反号，
   因此“被挡就反向开”（6.4）和“玩家不参与阻塞判定”（6.5）两条在两种铰链侧下都成立。
4. 日志信息扩充为：`ColdSteelDoor <名> 铰链侧=Y+/- 玩家侧=+X/-X 开门方向=+/-（朝玩家反侧开 ／ 推开侧被挡，已反向开）`，
   一眼能看出铰链侧、玩家所在侧与最终开向。

构建：`FPSGAME Win64 Development` → Succeeded（Game 目标先验证编译）；
编辑器模块需在编辑器关闭后用 `Tools/Build/Build-Editor.ps1` 重建后再进 PIE 验证。

## 6.6 按体素材质整体替换的门（2026-09-17 第六轮）

用户要求：门**整体替换材质**（而不是逐部件改），并给现有几种体素各配一扇门放进建筑面板。

做法与口径：

1. **整体替换**：`AColdSteelDoor::Configure(UMaterialInterface*)` 现在把 **门板与门框的全部材质槽**一起
   换成该材质（原先只换 slot 0，网格自带的小窗槽会残留别的观感）。要保留原网格的玻璃小窗，
   把两处循环改回 `SetMaterial(0, Surface)` 即可（一行改动）。
2. **生成时应用**：`AVoxelBuildWorld::SpawnPrefab` 的逻辑构件分支把调色板条目的 `Surface` 传给门
   （此前门生成后仍用网格自带材质，这是"换了材质没生效"的根因）。
3. **每种体素一扇门**（调色板 `Components`，占格统一 (2,6,11) = 40×120×220 cm）：

| 条目 ID | 显示名 | ActorClass | Surface | 归属材质行 |
| --- | --- | --- | --- | --- |
| `door_wood` | 木门（E 键开关） | `/Script/FPSGAME.ColdSteelDoor` | `Rounded/M_Voxel_Wood` | 木材 |
| `door_stone` | 石门（E 键开关） | `/Script/FPSGAME.ColdSteelDoor` | `Rounded/M_Voxel_Stone` | 石头 |
| `door_marble` | 大理石门（E 键开关） | `/Script/FPSGAME.ColdSteelDoor` | `Props/RomanColumn20260915/M_RomanStone_V2` | 大理石 |
| `door_physics` | 铁门（撞开） | `Blueprints/Doors/BP_PhysicsDoor_C` | 包自带 `M_Door` | 木材 |

   抽屉缩略图用条目的 `Mesh` + `Surface` 渲染，所以三扇门的卡片会各自显示对应材质的外观。
4. 三种门共用同一套门型（包里的 `SM_Door` / `SM_DoorFrame`）与同一套交互（E 键开关、6 秒自动关、
   被挡反向开、玩家不参与阻塞判定、开门过程穿过玩家）。要换成不同门型（例如我们自己的
   `UnrealNormandy/SM_Door_00A` 或 `SD_Art` 工业门），只需改门类里两个默认网格路径。

构建：`Tools/Build/Build-Editor.ps1` → Succeeded（`build-20260917-112556.log` 换材质应用、
`build-20260917-112723.log` 全槽替换），`UnrealEditor-FPSGAME.dll` 11:27:26；
调色板脚本读回确认 4 个门条目 + 2 个罗马构件齐备。

待确认的观感取舍：体素材质是给 20 cm 立方体调过的（贴图密度／UV 面向方块），铺到门网格上可能显得
过大或方向不对；若看起来不对，下一步给每种材质做一版 `MI_Door_<材质>`（只调 UV 缩放／方向与
粗糙度），调色板条目改指这版实例即可，不动代码。

## 6.5 玩家不参与阻塞判定，门板可从玩家身上扫过（2026-09-17 第五轮）

用户要求：**玩家直接判定为不被阻挡**，并且**门打开时可以穿过玩家**——避免门朝玩家这一侧开时，
因为玩家胶囊体的碰撞体积被判定成“门口被挡”。

改动（[ColdSteelDoor.cpp](../../Source/FPSGAME/Building/ColdSteelDoor.cpp)、
[VoxelBuildComponent.cpp](../../Source/FPSGAME/Building/VoxelBuildComponent.cpp)）：

1. `IsSwingBlocked()` 改用**对象类型查询**：只查 `WorldStatic`／`WorldDynamic`／`Destructible`
   （地形、体素、构件、残骸），**Pawn（玩家与怪物）完全不参与判定**——不再有“被玩家挡住所以反向开”的情况。
2. 门板碰撞口径 `UpdateLeafPawnCollision()`：**只有“关着且已经静止”的门板才挡住 Pawn**；
   开门／关门过程中以及开着时，门板对 Pawn 为 `Ignore`，所以门可以从玩家身上扫过去（也顺手避免开着的门板绊住玩家）。
   若关到位时玩家仍站在门板里，则先保持 `Ignore`，等他离开再恢复阻挡，避免把人挤住或卡死。
   门框始终阻挡（走门洞即可），门板的 Visibility 响应不变，所以准星指门按 E 仍然有效。
3. 顺带修正拆卸：准星命中的是**门本身**（逻辑构件挂在占位 Actor 下），原先 `AimedPrefab` 只认
   `AVoxelBuildPrefabActor`，会导致右键拆不掉门。现在沿挂载链向上解析占位记录
   （`VoxelBuildComponent::UpdatePrefabTarget` 与 `VoxelBuildWorld::RemovePrefab` 各一处），右键拆除正常。

构建：`Tools/Build/Build-Editor.ps1` → Succeeded，`build-20260917-112024.log`，三个文件均无警告；
`UnrealEditor-FPSGAME.dll` 11:20:34。

## 6.4 开门方向判定：默认侧被挡就反向开（2026-09-17 第四轮）

用户要求：**开门那一面被挡住时，直接从反方向开**。

实现（[ColdSteelDoor.cpp](../../Source/FPSGAME/Building/ColdSteelDoor.cpp)）：

- `IsSwingBlocked(DirectionSign)`：把门板碰撞盒按 25%／50%／75%／100% 的开合角摆四个采样位，
  用 `OverlapBlockingTestByChannel(..., ECC_Visibility, ...)`（与准星交互同一通道）判断这一侧扫过去是否被实体挡住；
  查询忽略这扇门自身与它的占位父 Actor；检测盒每轴略缩 2–4 cm，避免与地面、门框贴合面产生假阻挡。
- `OpenDoor()`：先按配置方向（`OpenAngleDegrees` 的符号）判断；被挡且**另一侧通畅**时改用反方向
  （`TargetAngle = |OpenAngleDegrees| × 反方向`），并把 `bOpenFlipped` 置位；两侧都被挡时保持默认方向，
  宁可夹着开也不出现“门完全打不开”。
- 每次开门都重新判定（墙拆了就会自动回到默认方向），并在日志打印结果：
  `ColdSteelDoor <名> 开门方向=+/-（默认侧被挡，已反向开 ／ 默认侧通畅）`。

设计口径（可随时改）：

- 玩家自己站在摆动范围里也会被算作阻挡，于是门朝另一边开——符合“被挡住就反向”的字面语义；
  若不希望身体触发反向，把检测参数里的 `ECC_Pawn` 排除即可（一行改动）。
- 两侧都堵住时的行为目前是“按默认侧开（会穿墙）”；也可改为只开一半或拒绝开门并提示。

构建：`ColdSteelDoor.cpp` 编译通过（`build-20260917-111348.log` 的 `[2/6] Compile ColdSteelDoor.cpp`）；
该次编辑器构建随后被并行会话正在编辑的 `FPSGAMECharacter.cpp`（`CameraShake` 未声明）打断，
对方修好后模块在 11:14:37 重新链接，已包含本次改动（对象文件 11:13:52 早于 DLL 时间）。

1. 进游戏（`L_TemperateHills_Initial` 或已放置门的关卡），在空地上按 B 打开建造抽屉 → 「材质 → 木材 → 其他构造」，应能看到两张门卡（`木门（E 键开关）`、`铁门（撞开）`）；选中后在 20 cm 格上放置。构件占格 (2,6,11)，放门的位置不要和已建体素重叠。
2. 放置后：**木门**准星对着按 **E** 开关（提示栏播报 `ColdSteelDoor · ToggleDoor`），打开 `AutoCloseSeconds`（默认 6 秒）后自动关；**铁门**用身体撞（包里的物理门，不需要按键）。
3. 门随建筑一起存档：`Prefabs` 记录的是 `Id／Cell／Yaw／Footprint`，重新进世界时按调色板里的 `ActorClass` 重新生成，旧存档无需迁移。
4. 已知边界：
   - 包里的 `BP_RotatingDoor(s)`／`BP_RotatingPhysicsDoors`／`BP_SlidingDoors` 引用的 `SM_Cube_03` **在包内不存在**（我们工程也没有对应资产），迁移后这几扇门是空网格，因此本轮没有登记进调色板；要用它们需要先给它们指定门板网格。
   - 键门（`BP_KeyDoor`／`BP_KeyDoorAutoClose`）资产已迁移但按用户要求暂不启用，钥匙目录未迁移。
   - 拖门／物理门的 Enhanced Input 资源已一并迁移，但角色侧的拖拽逻辑（D）本轮未接。
   - 门模型目前是包自带的 StarterContent 灰门；替换成 `UnrealNormandy/SM_Door_00A` 等自有网格只需改门蓝图的 `Door`／`DoorFrame` 组件，不影响本轮代码。

## 7. 第一人称「推门」动作（用户问：后续做可行吗）

**可行**，而且不需要现在就把门改成动画驱动。落点与做法：

- 现有第一人称手臂是「武器＋手臂」同一套骨骼网格上的整段动画（`Content/Weapons/<武器>/A_<武器>_*.uasset`：idle／draw／fire／reload／inspect…），角色侧已经用代码动态装载并切换动画序列（`Initialize*GripAnimations`、`PistolSprintAnimation`、`DrumReloadAnimation` 等），另外有左手施法分支（`FPSCastingMeshComponent`／`IsCastingWithLeftHand`）。
- 新增一段 `A_FP_PushDoor`（作者在 Blender／MAT 里按现有手臂骨骼做「左手前推、重心前移」），用同一套装载方式播放；门在**接触帧**由 AnimNotify（或代码定时器）触发开门，动作与门的开合时间用同一个事件对齐——门侧已经暴露交互入口，通知里调用同一条入口即可。
- 三种绑定口径，按当时持枪状态选：① 持枪单手推（步枪在左手，右／左手推门）；② 先播收枪、空手推门（最自然，但要占用 `SuspendWeaponForMenu` 那套状态）；③ 用施法左手的现有手型做"推"的动作（最省美术，风格也最接近现有左手内容）。
- 必须遵守现有占用与互斥：左手施法进行中（`IsCastBlockingLeftHandAction`）、换弹、检视、格挡等状态不能同时推门；推门期间锁移动/瞄准输入（沿用菜单/施法那套 `SetIgnoreMoveInput`／`SetIgnoreLookInput`），结束后恢复；被门挡住（门后有实体）时动作照播但门不转，并把"门被挡住"作为提示播报。
- 代价：1 段手臂动画（作者工作）＋1 个 AnimNotify＋约 30–50 行 C++（播放/占用/触发门）；不需要新建武器或改存档。届时把门的交互入口从 E 键改成"通知调用同一入口"，现有 B 的代码不用推翻。

## 8. 门尺寸统一化的尝试与回退（2026-09-18）

用户口径演变：单扇门"没有符合 20 cm 的倍数，尤其高度部分突出" → 要求"模型不替换、只调整大小，连同门框一起调整；
双开门也调整进深；双开门的门扇用单扇门的模型替换"。

**第一轮我改过头了，用户实测后要求"撤回调整，回到原始版本"，已完整回退（见下）。** 记录在这里，别重复踩：

### 改坏的两处（回退原因）

1. **动了本来不需要动的开门代码**：我顺手把 `AColdSteelDoor` 的铰链贴面（`ApplyHingeDepth`）、
   被挡反向的候选开向检测、开角 92°→85°、名义板厚常数一起重写了；而"缩放网格"这件事**根本不需要改 Actor 代码**——
   原代码一律按**包围盒**摆位（`AlignGeometry`），门框与门扇等比缩放后照常工作。结果开门手感被用户判为"完全错误"。
2. **缩放时把材质槽并没了**：用 `copy_mesh_to_static_mesh` 烘焙缩放版时会只留**一个空槽**，
   包里 `SM_Door` 原本是 `[M_Door, M_Glass]` 两槽（门扇自带小窗＝半透明）→ 缩放版丢了玻璃 ✗。
   正确做法：在 `GeometryScriptCopyMeshToAssetOptions` 里打开与 material 相关的开关（照喷泉 2× 脚本里
   `mat_props = [n for n in dir(to_opts) if "material" in n.lower()]` 的探查方式），或烘焙后把源资产的
   `static_materials` 逐槽拷回，再确认 `slots` 数与源一致（喷泉那次就校验了 `materials_kept == 2`，我这次没做）。

### 已回退到什么状态（2026-09-18 11:56）

| 项 | 状态 |
| --- | --- |
| `Source/FPSGAME/Building/ColdSteelDoor.h/.cpp` | `git checkout HEAD --` 恢复；`git diff HEAD` 为空 = 与门线提交逐字节一致（92°、无贴面口径、无候选开向检测） |
| 单扇门网格 | 回到包里 `SM_Door` / `SM_DoorFrame`（24.8 × 114 × 212，含 `M_Glass` 小窗槽）；本轮烘焙出的两个缩放版资产已删除 |
| 双开门网格 | 门框回到自建盒体 **20 × 200 × 200**（占格 (1,10,10)）、门扇回到自建盒体 10 × 91.5 × 183（含圆形把手） |
| `AColdSteelDoubleDoor.cpp` | `LeafHalfThicknessCm` 回 2.5、去掉左扇 180° 覆盖（回到基类"右扇转 180°"） |
| 调色板 | `door_*` = `SM_Door` + 占格 (2,6,11)、`door_physics` 不变、`double_door_*` = (1,10,10)（读回确认） |
| 构建 | Game／Editor 两个目标均 Succeeded（11:56），`git diff HEAD` 对门的源码为空 |

### 下一步该怎么做（如果还要调尺寸）

**只改网格、别碰代码**：把包里的 `SM_DoorFrame` + `SM_Door` 用**同一组逐轴比例**缩放到目标尺寸
（例如门框 40 × 100 × 200 ＝ 100/114 与 200/212），**保留全部材质槽**，然后：
① 先出离线渲染给你看 → ② 进游戏只验证"能放、能开门"，确认没有回归 → ③ 才考虑是否需要动 Actor 代码。
单扇门的 `AColdSteelDoor` 一行都不用改。

另外：**原版本身也会替换门扇自带的玻璃**——`AColdSteelDoor::Configure()` 按当初"整体替换材质"的要求把
门板与门框的**所有**材质槽都换成调色板材质（代码注释里就写了"要保留网格自带玻璃小窗，把两处循环改回只
SetMaterial(0, Surface)"）。想在游戏里保住那扇小窗的玻璃，把 `Configure()` 改成只换 slot 0 即可（一行）。

### 发布记录（2026-09-18）

- 提交：`502bb27`（`origin/main`），发布目录 `D:/FPS3D/FPSGAME`，普通推送 `HEAD:main`，`git ls-remote` 回读一致。
- 验证：Game／Editor 两目标编译 Succeeded；调色板与网格经**独立进程**读回（`verify_*.py`，日志在对应 `SourceAssets/` 目录）。
- 内容依赖：复用既有体素材质与包内 `SM_Door`/`SM_DoorFrame`（未修改包资产）；预览图与日志按忽略规则只留本地。
- **运行时验收仍由用户执行**（清单见该轮案例文档）。
