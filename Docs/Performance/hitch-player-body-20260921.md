# 卡顿排查：玩家建模之后的常驻开销（2026-09-21）

本文记录 2026-09-21 `DayNight_Lighting` 卡顿排查的实测结论与已落地的修改。
所有数字来自 CSV 采集与本次新增的诊断探针，非推测；未测项在文末单列。

## 1. 复现与采集

| 采集 | Profile | 地图 | 帧数 | 结论 |
| --- | --- | --- | --- | --- |
| A（用户现场） | `DayNightPerformance20260921` | DayNight_Lighting | 1200 | 与 B/C/D 同一签名 |
| B | `DayNightPerfB20260921` | DayNight_Lighting | 1200 | 复现，44 帧 > 25 ms |
| C | `DungeonProbe20260921` | L_Dungeon_Prototype | 900 | **换地图同样复现**，63 帧 > 25 ms |
| D | `DiagHitch20260921D` | DayNight_Lighting | 900 | 打开同步加载探针的定位采集 |

采集方式：`Tools/Performance/run_daynight_capture.ps1`，
`-game -RenderOffscreen -ResX=1280 -ResY=720 -csvCaptureFrames -csvGpuStats`。

关键事实：**换地图照样卡**，所以与 DayNight 的天气贴图、体积云、天空系统无关。
背包里「不要先降天气贴图」的限制因此成立——天气不是原因。

## 2. 稳态卡顿的真实形态（采集 D，gate 60 帧之后）

```
steady frames : 840
steady median : 12.453 ms
stalls        : 24 帧 > 20 ms
stall frames  : [96,97,98,99][149,150][199][227,228][281,282][335,336][389,390]
                [479,480,481][561,562][617,618][676][899]
```

- **约每 50 帧（≈0.57 s）出现一次 45~55 ms 的顿挫**，随后跟一个 170~670 ms 的大停顿。
- 大停顿帧上的 `Exclusive/GameThread/FlushAsyncLoading` 和
  `FileIO/GameThread/AsyncLoadingTime` 从稳态的 **0.000 / 0.0004 ms**
  跳到 **407 / 231 ms**（最大 515 / 340 ms）。
  也就是说：**稳态本来完全不加载，顿挫帧却在做同步加载**。
- 顿挫帧 `SceneCulling/NumDynamicInstances` 513→1029、
  `NumStaticInstances` 153→306，正好翻倍；`Ticks/Total` 96→99。
- 渲染线程是受害者不是元凶：`Exclusive/RenderThread/EventWait` 跟着 GT 一起涨到 661 ms，
  自身工作量稳定在 24~27 ms；GPU 稳定 9~11 ms。
- `TextureStreaming/StreamingPool` 只在 272~1095 MB 之间自动变动，
  `NonStreamingMips` 恒定 5300 MB，显存余量约 2.2 GB。
  **没有证据支持动贴图或预算**。

## 3. 定位手段：同步加载探针

`Source/FPSGAME/Diagnostics/FPSLoadHitchProbe.*`（新文件，默认关闭）

- 挂 `FCoreDelegates::OnSyncLoadPackage`，记录游戏线程同步加载的包名、
  间隔时长，并在加载入口抓调用栈（按模块基址换算成偏移，可离线对 PDB）。
- 运行期开关：`fpssyncload <thresholdMs> [everyEntry]`，
  证据写到 `Saved/Profiling/LoadHitch/<profile>.log`。
- 采集 D 实测：整段 900 帧只发生 **676 次同步加载，且全部落在游戏开始运行的
  头 ~10.5 秒之内**（相对时长精确可测）；之后直到采集结束，再没有任何一次
  >25 ms 的同步加载。稳态帧的同步加载次数是 0——与上面 CSV 的判断一致。
  （探针的绝对时间戳是机器开机秒数，所以这里只取相对间隔，不做跨时钟对齐。）

探针抓到的慢加载（耗时降序，这是「更新后变卡」的直接证据）：

| 耗时 | 包 |
| --- | --- |
| 305 ms | `/Game/Weapons/PKM/SightGrip20260921/SK_PKM_Manny` |
| 264 ms | `/Game/Building/Voxels/Rounded/M_VoxelAimEdge` |
| 172 ms | `/Game/Weapons/PKM/SightGrip20260921/Animations/A_PKM_idle` |
| 170 ms | `/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny` |
| 156 ms | `/Game/Weapons/A762/Integrated20260920/SK_A762_Manny` |
| 119 ms | `/Game/Weapons/AKM/VideoAudio20260921/S_AKM_ChargeRelease` |
| 118 ms | `/Game/Weapons/A762/Accessories05/Animations/prism/A_A762_prism_sprint_exit` |
| 95 ms | `/Game/Weapons/FreeFirearmAudio20260913/S_QBZ191_Suppressed_04` |
| 87 ms | `/Game/Weapons/DanWesson715/Chrome20260914/SK_DW715_Manny` |
| … | 另有 M1911、ASH12、AKM 等共 20 条 |

模式很清楚：**每个武器家族一套世界身体网格 + 持枪动画 + 配件 + 音频，
全部同步加载**。这正是玩家建模接入后新增的加载面。

## 4. 根因

### 4.1 玩家世界身体与装备全部同步加载

- `FPSPlayerBodyComponent::InitializeBody()`
  （`Source/FPSGAME/Characters/FPSPlayerBodyComponent.cpp:53`）
  同步 `LoadObject<USkeletalMesh>` 身体网格，然后循环
  `Content/ColdSteelData/player_body.json` 的 **60 条 `clips`** 逐条同步
  `LoadObject<UAnimSequence>`。这些都在 `BeginPlay` 里。
- `FPSPlayerBodyEquipment.cpp` 的 `RebuildWeapons()`（`:120` 起）
  对每个武器槽同步加载 `Mesh`、`HoldClip`、`Materials`、`Parts[].Mesh`、
  `Parts[].Materials`；`ApplyOutfit()`（`:191` 起）同步加载 outift 网格与材质。
- `FPSPlayerBodyComponent` 每 **0.2 s** 跑一次 `CaptureEquipment()`（5 Hz），
  变化时整批重建。装备/外观切换、状态模型 `OnChanged` 都会触发。

### 4.2 每帧重设可见性，持续弄脏渲染状态

这是常驻开销，也是本次最直接的修复点：

- `AActor::CalcCamera` → `UFPSPlayerBodyComponent::ApplyCameraView()`
  → `UpdateWorldOwnerVisibility()`，
  **每次相机更新都对身体、世界武器、配件、外观逐个 `SetOwnerNoSee()`**。
- `TickComponent` 每 0.2 s → `UpdateOwnerVisibility()`，
  对第一人称相机的**每一个子图元**逐个
  `SetOnlyOwnerSee` + `SetOwnerNoSee` + `SetCastShadow`。
- 这三个 setter 都会把图元渲染状态标脏（重建渲染状态、重新注册阴影场景、
  重算可见性），而且**无论值是否变化都会执行**。
  8 帧一组的瞬顿、顿挫帧实例数翻倍，与该行为吻合。

### 4.3 身体网格被强制每帧刷骨骼

`InitializeBody()` 把身体网格设成
`EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones`。
第一人称下身体是 `SetOwnerNoSee(true)`，但依然每帧刷骨骼变换。

### 4.4 缺失图标反复重试

采集 D 日志里 **123 条** `LogImageUtils: Warning: Error creating texture … could not be found`，
固定三个文件反复出现，每个 41 次：

```
Content/ColdSteelData/Icons/ue_pkm.png
Content/ColdSteelData/Icons/ue_dan_wesson715.png
Content/ColdSteelData/Icons/ue_frost_crystal_sword.png
```

三个文件在磁盘上确实不存在。`UColdSteelInventoryWidget::LoadIcons()`
在 `ImportFileAsTexture2D` 失败时直接 `continue`，**不记失败**，
于是每次 `OnChanged`（5 Hz 级）都重新读盘、重新报 warning、
再造一个马上被丢弃的 `UTexture2D`。

## 5. 已落地的修改

| 文件 | 修改 |
| --- | --- |
| `Characters/FPSPlayerBodyTypes.h` | 新增 `FPSBodyEquipment::ApplyOwnerVisibilityFlags` 声明 |
| `Characters/FPSPlayerBodyEquipment.cpp` | 实现该 helper：三个标志**只在值变化时**才 set；`WorldVisibility()` 改用 helper |
| `Characters/FPSPlayerBodyComponent.cpp` | `UpdateOwnerVisibility()` 改用 helper；按是否第三人称在 `AlwaysTickPoseAndRefreshBones` / `AlwaysTickPose` 之间切换身体网格 |
| `Characters/FPSPlayerBodyCamera.cpp` | `UpdateWorldOwnerVisibility()` 改用 helper，不再每帧无条件 set |
| `UI/ColdSteelInventoryWidget.h/.cpp` | 新增 `FailedIcons`，导入失败的图标只记一次，不再每次刷新重试 |

行为契约未变：可见性结果与原来完全一致，只是不再重复下发；
第三人称切回来时骨骼刷新立刻恢复。

## 6. 修复后的测量（2026-09-21 23:14，采集 E）

修好并链接后按**完全相同参数**重跑（`DayNight_Lighting`、1280×720、900 帧、
`-ExecCmds=fpssyncload 25`）。

### 6.1 确实生效的

| 项 | 修改前 (D) | 修改后 (E) |
| --- | --- | --- |
| 缺图标 warning 条数 | **123** | **6** |
| 首帧前的同步加载条目 | 676 | 676 |

图标重试的浪费已经消除（`FailedIcons` 生效，实测 123 → 6）。

### 6.2 没有测出改善的（如实记录）

| 指标 | D（前） | E（后） |
| --- | --- | --- |
| 稳态中位帧时间 | 12.45 ms | 12.60 ms |
| 稳态 >20 ms 帧数 | 24 | 25 |
| 最大帧时间 | 667 ms | 710 ms |
| 启动前 11 帧总耗时 | 18.96 s | 35.54 s |

启动耗时在不同采集之间本来就在 19~35 s 间大幅波动（采集 A 25.66 s、B 30.71 s、
D 18.96 s、E 35.54 s），**所以 E 的启动变慢不能归因于这次修改，也不能说已改善**。

### 6.3 但这轮测量给出两个更硬的结论

**结论一：顿挫是确定性的，不是随机噪声。** D 和 E 的顿挫时刻几乎逐点对齐：

```
D: 0.50s 49ms | 1.17s 667ms | 2.00s 49ms | 2.61s 615ms | 3.66s 49ms | 4.03s 370ms | 5.29s 558ms ...
E: 0.56s 51ms | 1.27s 710ms | 1.96s 51ms | 2.70s 666ms | 3.85s 435ms | 4.86s 48ms | 5.55s 689ms ...
```

两次独立运行复现同一串节点，说明背后是**代码行为**，不是磁盘冷缓存或后台干扰。
另外：**最后约 3 秒完全没有顿挫**，1200 帧的采集 B 也是帧 600 之后基本干净——
顿挫集中在进入游戏后的头 ~11 秒，随后消失。

**结论二：剩下的顿挫不是游戏线程 CPU 工作量造成的。**
对 45~50 ms 的规则顿挫逐列展开（`dump_hitch_frames.py --gate 60 --threshold 40 --below 60`）：

```
FrameTime=50.81  GameThreadTime=12.54  RenderThreadTime=14.52  GPUTime=13.10
  GameThreadTime_CriticalPath                     47.56
  Exclusive/GameThread/EventWait/WorldTickMisc    35.04   <- 游戏线程在 UWorld::Tick 里等待
  Exclusive/GameThread/FlushAsyncLoading           0.00   <- 不再有同步加载
  Exclusive/GameThread/Tickables                   0.00
  SceneCulling/NumDynamicInstances            1029  (常态 514，仍翻倍)
```

游戏线程自己的活只有 12.5 ms，渲染线程 14.5 ms，GPU 13.1 ms，
但 `GameThreadTime_CriticalPath` 是 47.6 ms——**多出来的 35 ms 是
`WorldTickMisc` 等待**（`LevelTick.cpp:1506`，即 `UWorld::Tick` 自身的等待段）。

`SceneCulling/NumDynamicInstances` 在顿挫帧恰好翻倍（514→1029），
说明渲染侧确实在那一帧处理了两倍的可见性实例，与“游戏线程等渲染同步点”一致。
**这是渲染同步等待，不是本轮的可见性重复下发造成的**，所以修改前后数字不变。

## 7. 隔离实验：把玩家建模整个关掉（决定性）

前几轮的 A/B 都不干净（`-ExecCmds` 在第 1 帧才生效，而 `InitializeBody()` 在世界初始化
阶段就跑完了，所以 `fps.body.WorldBody=0` 实际没拦到任何东西——两次采集的同步加载数
都是 677，`world body suppressed` 一行都没打）。

改成**临时挪走 `Content/ColdSteelData/player_body.json`**，这样 `BeginPlay()` 里
`Configuration` 无效，整个世界身体功能彻底不建立（日志确认打了
`PlayerBody: missing Content/ColdSteelData/player_body.json`）。采集后已还原配置文件。

| 采集 | 稳态中位 | >20 ms 帧 | 最大帧 |
| --- | --- | --- | --- |
| 世界身体开启 | 12.807 ms | 24 | 705.6 ms |
| `fps.body.WorldBody=0`（未真正生效） | 12.662 ms | 26 | 575.9 ms |
| **player_body.json 挪走（真正关闭）** | **11.407 ms** | **24** | **678.2 ms** |

### 结论（修正上一轮的判断）

1. **顿挫在玩家建模完全关闭时照样存在**：24 帧 >20 ms、最大 678 ms、
   间隔中位数仍是 ~55 帧。所以**这串顿挫不是玩家建模造成的**，我上一轮
   「建模导致顿挫」的归因过宽，这里更正。
2. **但玩家建模确实有 ~1.0~1.4 ms/帧 的常驻开销**：
   稳态中位 11.407 ms（关）→ 12.662~12.807 ms（开），约 **+11%** 帧时间。
   这是额外的世界身体网格 + 阴影投射 + 骨骼动画的固定成本，在 60 FPS 预算里
   是 8~11%；场景更重时占比会更明显。用户感觉「加了建模以后变卡」有这个成分。
3. 顿挫仍然集中在**进游戏后的头 ~11 秒**，之后自行消失。
   所有采集（A/B/D/E/On/Off/NoBody）都是这个形状。

## 8. 结论与下一步

1. **玩家建模的账**：固定的 ~1.0~1.4 ms/帧世界身体成本（已量化，未优化）。
   可见性去抖改动是对的但测不出差异；身体资产同步加载确实存在（`InitializeBody()`
   在 `BeginPlay` 里同步读网格 + `player_body.json` 的 60 条 clips），
   但探针在慢加载清单里**从未出现过 `SKM_Manny_PlayerSkin` 或任何
   `Mannequins/Anims` 包**——41 条慢加载全是武器家族的资产。
   也就是说：**身体资产的加载不是那批慢加载的主角，武器世界副本才是**
   （`SK_PKM_Manny` 467 ms 等，来自 `CaptureEquipment`/`RebuildWeapons`）。
2. **尚未解释的主线顿挫**（24~26 帧 >20 ms，最大 575~710 ms，
   约每 55 帧一次，头 11 秒后消失）：
   - 是**游戏线程的等待**，不是游戏线程的工作量：顿挫帧
     `GameThreadTime` 仅 12.5 ms、`RenderThreadTime` 14.5 ms、`GPUTime` 13.1 ms，
     而 `GameThreadTime_CriticalPath` 47.6 ms，其中
     `EventWait/WorldTickMisc`（`UWorld::Tick` 自身等待段）35 ms，
     同时 `Exclusive/RenderThread/EventWait` 涨到 670~700 ms。
   - **不是玩家建模**（本轮已用隔离实验排除）。
   - **不是同步加载**（探针在稳态帧记录不到任何 >25 ms 的包加载）。
   - 下一步需要 Rendering/RHI 侧的等待点细分：`-trace=gpu`、
     或现场 `stat unit` / `stat gpu` / `stat levels`，本轮未做。
3. **武器世界副本的同步加载**仍然值得改成异步：41 条慢加载、
   单条最长 467 ms，是明确的启动期浪费，但**不是**主线顿挫。
4. **仍未验证**：所有数据都来自 `-game -RenderOffscreen` 独立运行，
   不是用户的交互 PIE 现场；用户现场的帧时间、视角、角色数量都还没采到。

## 10. 异步预加载（已实现并实测，结论：对这批慢加载无效）

用户的诉求：把身体/装备资产改成 `RequestAsyncLoad` 异步预加载。

### 10.1 为什么用预加载而不是改造每个加载点

真正的调用点需要**同步**拿到资产（`InitializeBody()` 建身体、`RebuildWeapons()` 建
世界武器组件、`FPSGAMECharacter.cpp:337-420` 换视模），把它们整体改成纯异步会改动核心
装配时序，风险远大于收益。改成**先把同一批资产异步请求进内存**，后面那些
`LoadObject`/`LoadSynchronous` 就变成缓存命中。

### 10.2 新增 `UFPSBodyAssetPreloader`（GameInstanceSubsystem）

`Source/FPSGAME/Characters/FPSBodyAssetPreloader.h/.cpp`

在第一个游戏世界出现时（早于角色 `BeginPlay`）收集路径并一次性
`UAssetManager::GetStreamableManager().RequestAsyncLoad(...)`。
路径来源：`player_body.json`（身体网格 + 60 clips + outfit）、
`AFPSGAMECharacter` CDO 的类默认值与全部组件、存档内每件物品的 `Data`。

### 10.3 实测：只有 69 条，慢加载一条都没覆盖

第一次实测（`PreloadOn20260921`，采集参数与 E 完全一致）：

```
BodyAssetPreloader: requested 69 assets asynchronously (0 resident already)
BodyAssetPreloader: 69 assets resident
LoadHitchProbe summary: 678 sync-load entries seen, 42 recorded
```

**慢加载清单与打开预加载之前逐条相同、耗时也相同**：
`SK_PKM_Manny` 425 ms（前 467 ms）、`SK_QBZ191_Manny` 236 ms（前 203 ms）、
`SK_A762_Manny` 148 ms（前 148 ms）……

原因是**这 69 条路径根本没覆盖真正慢的资产**。慢加载清单全部落在
`/Game/Weapons/<家族>/` 下，而这些路径是**编译期常量**：

- `FPSGAMECharacter.cpp:382` → `PKMWeaponAssets::MeshPath`
  = `TEXT("/Game/Weapons/PKM/SightGrip20260921/SK_PKM_Manny.SK_PKM_Manny")`
- `:346` `ASH12WeaponAssets::MeshPath`、`:373` `DanWesson715WeaponAssets::MeshPath`、
  `:337` QBZ191 字面量路径……
- 以及 `M4TacticalSprintComponent.cpp:34`、`GunsmithSystem.cpp:64`、
  `PistolDualWieldComponent.cpp:126` 等处的动画/音效路径

这些常量**不在任何资产里**，CDO 上也取不到（CDO 的视模是默认 AKM），
所以走资产引用是找不到的。`ApplyInventoryWeapon()` 是按
`ActiveInventoryWeaponDefinition` **逐个家族懒加载**的。

### 10.4 修正：从常量生成注册表

`Tools/Performance/generate_preload_registry.py` 扫描游戏模块头文件里所有
`TEXT("/Game/...")` 字面量，生成 `Source/FPSGAME/Characters/FPSPreloadAssetRegistry.gen.h`
（**62 条包路径**）。这是设备代码真正读取的常量集合，属于可再生成的真相来源。
脚本同时列出 **61 条 `Printf` 动态模板**（`A_PKM_%s`、`S_%s_` …），
这些**无法静态枚举**。

### 10.5 文件夹展开：试过，明确是有害的

为了覆盖 61 条动态路径，加了 `fps.body.AsyncPreloadExpandFolders`，用资产注册表
按内容文件夹递归收集。实测（`PreloadExpanded20260921`）：

```
BodyAssetPreloader: 62 folders expanded via the asset registry
BodyAssetPreloader: asset cap 1200 reached, 856 paths skipped
BodyAssetPreloader: requested 1200 assets asynchronously (131 named, 1069 by expansion)
LoadHitchProbe summary: 687 sync-load entries seen, 60 recorded   <- 变差了（42 -> 60）
BodyAssetPreloader: 1200 assets resident        <- 花了 19 秒
```

三个问题：
1. **范围失控**：`Content/Weapons` 下有 **3383 个包**，而实际被引用的只有约 131 条。
   武器目录保留了每一代设计稿（`SightGrip`09/10、`Recovery07`、`GripFinish08` …），
   只有最新一版进运行时。展开把它们全拖了进来。
2. **反而更慢**：慢加载 42 → 60。预加载用了 `AsyncLoadHighPriority`(=100)，
   与游戏自身的流送抢带宽，把游戏线程饿住了。
3. 19 秒才全部 resident，与 `AsyncLoading2` 的 `Multithreaded: false` 一致。

**因此**：`fps.body.AsyncPreloadExpandFolders` 默认改为 **0**，
优先级改为 `DefaultAsyncLoadPriority`(=0)，上限收到 400。
这条经验值得记住：**不要用资产注册表按目录盲扫武器目录**。

### 10.6 当前状态与判断

- 命名路径预加载（131 条）保留并默认开启：它覆盖身体、装备定义与 62 条家族常量，
  成本低、语义明确。
- **必须诚实说明：它没有消除那批慢加载。** 因为 131 条命名路径里仍缺少
  61 条 `Printf` 动态路径（各家族的动画与音效），而实测最慢的几条正是它们
  （`S_AKM_ChargeRelease` 143 ms 属 AKM 家族动态路径）。
- 要把这批也消掉，正确做法不是继续扩大预加载，而是**按家族提供一份权威清单**：
  为每个家族加一个返回该家族全部运行时路径的函数（网格 + 全部 clip + 全部音效），
  在 `ApplyInventoryWeapon()` 切到该家族**之前**异步请求。这需要按家族逐个补齐
  清单，属于后续独立工作。

### 10.6 实测：命名路径预加载确实削减了武器家族的慢加载

生成器最初有个**真 bug**：字面量正则会匹配到 `Printf(TEXT("..."))` 里面的字符串，
于是把 `TEXT("/Game/Weapons/QBZ191/%s/Animations/%s/A_QBZ191_%s_%s")`
这类**模板当成了可加载路径写进注册表**。这解释了为什么 `SK_QBZ191_Manny`
修好别的之后仍然 186 ms 加载——注册表里有 QBZ191 的**模板**，没有真实路径。
已修正：含 `%` 的字符串归入动态模板，另外过滤掉字符串拼接产生的残片
（以 `/` 或 `_` 结尾，如 `SM_QBZ191_`）。

修正后（`PreloadNamed20260921`，采集参数与 E 完全一致，且是**同一代码状态的背靠背对照**）：

| 指标 | 打开预加载之前（E） | 命名路径预加载 |
| --- | --- | --- |
| 请求资产数 | — | 128 |
| 慢加载条数 | 42 | **24** |
| 慢加载总耗时 | 2451 ms | **1065 ms** |
| `SK_PKM_Manny` | 467 ms | **已消失** |
| `SK_A762_Manny` | 148 ms | **已消失** |
| `SK_QBZ191_Manny` | 203 ms | 186 ms（当时仍是模板 bug） |
| `SK_DW715_Manny` | 88 ms | **已消失** |
| `warehouse_chest_rigid` | 70 ms | 81 ms |
| `A_A762_prism_sprint_exit` | 108 ms | **已消失** |
| `S_AKM_Suppressed` | 45 ms | **已消失** |

所以这套机制**对它能枚举到的资产是有效的**，武器家族网格与配件动画基本都变成了缓存命中。

### 10.7 环境警告：后续测量已不可比

修正注册表后重测（`PreloadFinal20260921`）时，**源码树被并行的另一条工作流改动了**
（期间 `Source/` 下数十个文件被批量改写，新增
`Docs/Weapons/pkm-retirement-20260922.md`，PKM 武器家族整体退役、
`PKMWeaponAssets.h` 被删除）。这次采集出现：

- `LoadHitchProbe summary: 845 sync-load entries seen, 94 recorded`
- 47 条慢加载 / 3461 ms，其中 **25 条来自
  `/Game/__ExternalActors__/GameMaps/`（1811 ms）**——World Partition 的外部 Actor 包，
  与装备预加载无关
- 出现 3281 ms 的极端帧，>`20 ms` 帧 66 个

**这些数字不能用于评价本次改动**：关卡内容本身变了，而且
`FPSGAMECharacter.cpp` 等文件在同一次采集前后被改写。
10.6 的表格是唯一一段代码状态一致的对照，结论以它为准。

## 11. 顺带修复的编译错误（与本次改动无关，但阻塞了链接）

编辑器目标有 3 处**必然编译失败**的问题，独立目标此前没暴露出来：

1. `Monsters/WitchRebuiltMonster.h:21` — `static bool BuildDrape(USkeletalMesh* Mesh)`：
   参数名 `Mesh` 遮蔽 `ACharacter::Mesh`，**UHT 直接拒绝**（`shadowing is not allowed`）。
   已改名 `SourceMesh`。
2. `Monsters/WitchRebuiltMonster.cpp:29` — lambda 参数 `Role` 遮蔽 `AActor::Role`（C4458 视为错误）。
   已改名 `ClipRole`。
3. `Monsters/WitchRebuiltMonster.cpp:118` — 局部 `Controller` 遮蔽 `AActor` 成员，
   且 `const auto*` 无法从 `TObjectPtr<APawn>` 推导。已改为显式
   `const APlayerController*` / `const APawn*`。
4. `Monsters/WitchRebuiltAuthoring.cpp` — `BuildDrape` 函数体内所有 `Mesh`
   都解析到了继承的非静态成员（静态函数里非法引用），
   `for (auto* Body : ...SkeletalBodySetups)` 无法从 `TObjectPtr` 推导，
   lambda `Section` 的 `return INDEX_NONE` 与 `return I` 推导冲突。已全部修正。

这些是**既有问题**，不是本次改动引入的；修好之后编辑器目标才第一次链接成功。

## 13. 采集机器的真实硬件（2026-09-22 核实）

此前所有采集日志都写 `gpu="NVIDIA GeForce GTX 750 Ti"`，一度被当作真实硬件。
**这是显示名被改写，不是真卡。** 三条独立证据：

| 来源 | 值 | 说明 |
| --- | --- | --- |
| `LogD3D12RHI` | `DeviceId: 2208` | `0x2208` = GA102 = **RTX 3080 系列**，与 750 Ti（`0x1380`）不符 |
| `LogD3D12RHI` | 专用显存 **12084 MB** | 750 Ti 只有 2 GB |
| `nvidia-smi` | **RTX 3080 Ti**，12288 MiB，驱动 596.21 | 直接来自驱动 |

其余健康指标（`nvidia-smi`，桌面空闲态）：

```
temperature 50 C | fan 37% | power 76.5W / 350W cap
throttle reasons 0x0000000000000001 (GPU Idle)   <- 不是温度/功耗降频
SM clock 210 MHz (idle) / max 2100 MHz
```

主机：ASUS，i7-13700K（16 核），31.7 GB RAM。

**结论：没有硬件故障，显存也够。** 依据：
1. 显存 12288 MB，采集里 `LocalBudgetMB` ≈10.7 GB、`LocalUsedMB` ≈8.5 GB，余量 ~2.2 GB。
2. 顿挫帧 **GPU 时间只有 13.1 ms**，而 `GameThreadTime_CriticalPath` 47.6 ms——
   瓶颈在游戏线程的等待，不在 GPU。（此前误读 `LocalBudgetMB` 得出的
   「建立在 4 GB 卡上、预算 10.7 GB 自相矛盾」这一推论**作废**：卡是 12 GB，预算合理。）
3. 顿挫**周期性且确定性强**（约每 50~55 帧一次，两次独立采集逐点对齐），
   且**进游戏约 11 秒后自行消失**。硬件降级/故障的表现是随机的、与负载无关、
   且不会自己恢复。这条形状本身就指向软件与启动期数据，不是硬件。

### 13.1 顺带发现：这台机器上有虚拟显示适配器，GPU 名被改

- `Win32_VideoController` 里有 **MuMu Virtual Display Adapter**、
  **GameViewer Virtual Display Adapter**（1920×1080）两个虚拟显示适配器。
- GPU 名字被改成 "GTX 750 Ti"，但项目配置里**没有** `sg.OverrideGPUBrand`
  （已确认），所以是驱动/注册表层面的改名，来自某个串流或模拟器工具。

两点影响：
1. **可能影响项目按 GPU 名分支的设置**，也会干扰以后的诊断与驱动更新检查。
2. 如果用户是通过**串流/虚拟显示层**实际游玩，那一层自带帧率与输入延迟，
   可能产生与本次采集**不同**的顿挫。这是我一直在提「需要现场 `stat unit`」
   的另一个原因——如果顿挫在本地直接玩时消失、只在串流时出现，那就属于另一个问题。

## 14. 「帧数降低」（持续降帧）——与本文主线顿挫是两件事

用户 2026-09-22 澄清症状是**帧数降低**，不是周期性顿挫。此前所有采集都在
**1280×720**，而用户实际桌面是 **2560×1440**，GPU 压力差一个量级，
所以「降帧」在既有数据里根本显不出来。据此按原生分辨率重测。

### 14.1 帧预算分解（`Tools/Performance/frame_budget.py`，窗口取帧 420~900）

| 采集 | 分辨率 | 中位帧 | game | render | **gpu** | p90 帧 | >16.7 ms | >33.3 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E（预加载前，720p） | 1280×720 | 12.46 | 3.61 | 12.48 | **10.90** | 13.90 | 2.1% | 1.5% |
| 命名预加载（720p） | 1280×720 | 12.55 | — | — | — | — | — | — |
| **720p 当前构建 · 运行 1** | 1280×720 | **35.56** | 5.07 | 35.84 | **34.45** | 92.40 | 96.2% | 63.8% |
| **720p 当前构建 · 运行 2（立即重跑）** | 1280×720 | **12.41** | 3.56 | 12.41 | **10.80** | 14.57 | 2.5% | 0.8% |
| 1440p 身体开 | 2560×1440 | 11.56 | 10.09 | 9.64 | **9.88** | 24.64 | 15.2% | 6.9% |
| 1440p 身体关 | 2560×1440 | 12.25 | 11.97 | 5.14 | **9.20** | 36.39 | 18.8% | 10.4% |

### 14.2 两条可用结论

1. **GPU 不是瓶颈，降画质大概率没用。** 三次干净采集里 720p 与 1440p 的
   GPU 时间几乎相同（10.90 / 10.80 / 9.88 ms）——**分辨率翻两番，GPU 时间没变**，
   说明有别的环节在限制帧率。1440p 下 GPU 只用 9.88 ms，离 16.7 ms 预算还很远。
2. **玩家建模的降帧成本很小，不足以解释「帧数降低」。** 我先前的 720p 对照是
   12.807（开）→ 11.407（关），约 1 ms；本轮 1440p 对照是
   11.56（开）→ 12.25（关），方向相反。两组都说明差异在测量噪声量级。

### 14.3 警告：本机采集无法复现用户的降帧

- **720p 当前构建连续两次运行：35.56 ms（28 FPS）与 12.41 ms（80.6 FPS），
  相隔仅 2 分钟、同一构建、同样的参数。** 第一次是离群值，立即重跑即正常。
  也就是说这套 `-game -RenderOffscreen` 采集本身有 **±3 倍**的不可复现波动。
- 两次 1440p 采集都有 **2800~2960 ms 的极端帧**，与「树在这一时段被并行工作流
  改动（PKM 退役等）」重叠，不能当作稳态数据。
- **因此：我不能用这套数据复现或解释用户遇到的降帧。** 上面 14.2 的两条结论
  只在「三次干净采集」范围内成立。

### 14.4 下一步需要用户现场数据

必须区分两件事，而现有数据无法区分：
1. **持续降帧**（用户报告的症状）：需要用户 PIE/独立运行现场按 `stat unit`，
   记录 **Game / Draw / GPU** 三个数。若 Game 高 → 游戏线程（CPU/蓝图/动画）；
   若 Draw 高 → 渲染线程；若 GPU 高 → 才是画质与分辨率。
2. **周期性顿挫**（本文 1~13 节追的那条）：头 11 秒、每 ~55 帧一次、自行消失。

### 14.5 重要更正：本套采集的分辨率改不动，14 节前半的 1440p 数据无效

为验证「1440p 下 GPU 是否成为瓶颈」，用 `-ResX 2560 -ResY 1440` 采集了两次。
**但这两次实际都跑在 1280×720。**

证据链：
1. 两次采集日志的元数据都是 `systemresolution.resx="1280" / resy="720"`。
2. 分辨率相关的工作量指标**没有变大**：`RenderTargetPool/PeakUsedMB`
   = **2041 MB**（"1440p"）对 **2365 MB**（720p）——真按 1440p 渲染这个数会显著更大。
   同理 `RenderTargetPoolUsed` 2041 对 2365、`RenderTargetPoolCount` 100 对 109。
3. 引擎命令行**确实**收到了 `-ResX=2560 -ResY=1440`（日志 `LogInit: Command Line` 有），
   但被覆盖。

试过三种强制手段，**全部失败**：

| 手段 | 结果 |
| --- | --- |
| `-ResX/-ResY`（配合 `-RenderOffscreen`） | `systemresolution.resx="1280"` |
| `-windowed -ResX/-ResY` | `systemresolution.resx="1280"` |
| `-ExecCmds=r.SetRes 1600x900w` | `systemresolution.resx="1280"` |
| 改写 `Saved/Config/WindowsEditor/GameUserSettings.ini` 的 `ResolutionSizeX/Y`（已备份还原） | `systemresolution.resx="1280"` |

**这把 `GameUserSettings.ini` 里写死的 `ResolutionSizeX=1280 / ResolutionSizeY=720`
以及引擎在此无头配置下的窗口大小策略钉死在 720p。**

### 14.6 因此作废与仍然成立的结论

**作废**：
- 「GPU 不是瓶颈，降画质大概率无效」。它建立在「720p/1440p 的 GPU 时间几乎相同」
  之上，而那个相同是因为**根本没换分辨率**。**1440p 下 GPU 是否是瓶颈：未测量。**
- 14.1 表中标注 2560×1440 的两行，实际是 1280×720。
- 720p 与 1440p 的行为差异（render 12.41 → 9.64、game 3.56 → 10.09）是
  **运行间噪声**，不是分辨率效应。

**仍然成立**：
- 硬件无故障：RTX 3080 Ti、12288 MB、驱动 596.21、50 °C、
  `throttle reasons = GPU Idle`（第 13 节）。
- **720p 稳态**：中位帧 **12.41 ms**、GPU **10.80 ms**、p90 14.57 ms、>33.3 ms 仅 0.8%。
- **本套采集有 ±3 倍不可复现波动**：同构建同参数相隔 2 分钟得到
  35.56 ms（28 FPS）与 12.41 ms（80.6 FPS）。这一条不受分辨率问题影响。
- 玩家建模的降帧成本在噪声量级（约 1 ms @720p），不足以解释整体降帧。

### 14.7 定位回归的正确路径（需用户配合）

用户明确说「**原来 100+，近期更新才降**」，这是**回归**，可用二分定位。
但需要先划定边界：

1. **需要用户提供**：上次确认 100+ FPS 是哪一天/哪个提交前后、在哪张地图、
   什么分辨率与画质、PIE 还是独立运行。没有这个边界，二分区间无法确定。
2. 候选提交（`git log`，2026-09-21）：`d96558e`(20:46) 之前用户自己已把
   「DayNight 回归」记入待办，说明症状**早于**当晚 22:07 之后的弹道/体素改动。
   但 `Source/FPSGAME/Characters/`（玩家身体）在 git 里**未跟踪**，不在这条历史里，
   其引入时间无法从提交记录判断。
3. 弹道/曳光弹改动**已被排除为整场景降帧原因**：三个曳光弹材质
   （`M_BallisticTracerSoftV2` / `VisibleV12` / `VisibleV13`）
   **都是 `BLEND_Additive` + `MSM_Unlit`，混合模式未变**，
   且只在开火时才有实例，不影响空载帧率。
4. `d96558e` 对 `Config/DefaultGame.ini` 的改动只有
   `DirectoriesToAlwaysCook`（打包用），**不影响运行时**。
5. 定位手段：对候选提交做 `git worktree` + 独立构建 + 同参数采集对照。
   注意本套采集的分辨率限制在 720p、且有 ±3 倍波动，**每个候选点至少需要
   2~3 次采集取中位**，否则会把噪声当成回归。

## 15. 未完成 / 未验证

- **未测量**：按家族补齐 61 条动态路径之后的效果。
- **环境不可比**：10.7 记录的那次采集因并行工作流改动源码树而失效；
  任何后续对照都必须确认 `Source/` 在采集期间未被改写。
- **未定位**：主线顿挫的 `WorldTickMisc` 等待具体挂在哪个同步点。
- **未验证**：`AlwaysTickPose` 档位切换是否影响第三人称切换瞬间的姿态首帧表现。
- **未覆盖**：61 条 `Printf` 动态路径（各家族动画与音效），其中包含实测最慢的
  `S_AKM_ChargeRelease`（104 ms）。要覆盖需按家族补权威清单，见 10.6。
- ~~`fps.body.WorldBody` 这个诊断开关**当前实际不生效**（读值时机早于 `-ExecCmds`）~~
  **已于 2026-09-22 修复**：改成在 `InitializeBody`／`UpdateOwnerVisibility`／
  `UpdateWorldOwnerVisibility` 三处各自读值，并加了 cvar 回调立即生效。
  见第 16 节。当时那一轮只能用挪走 json 的方式完成隔离。
- 三个缺失的图标文件是内容缺口（`ue_pkm.png`、`ue_dan_wesson715.png`、
  `ue_frost_crystal_sword.png`），本次只消除了重试开销，没有补图。

## 10. 复现命令

```powershell
# 常规采集
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Performance/run_daynight_capture.ps1 `
  -Profile DayNightPerfC20260921 -Map DayNight_Lighting -Frames 900

# 带同步加载探针
powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Performance/run_daynight_capture.ps1 `
  -Profile DiagHitch20260921E -Map DayNight_Lighting -Frames 900 `
  -ExtraArgs '-ExecCmds=fpssyncload 25'

# 分析
python Tools/Performance/steady_state_attribution.py Saved/<profile>/baseline.csv --gate 60 --threshold 20 --period
python Tools/Performance/analyze_daynight_csv.py Saved/<profile>/baseline.csv --skip 10
```

注意：UE 把 CSV 写到引擎级目录
`%LOCALAPPDATA%\UnrealEngine\5.8\Saved\Profiling\CSV\`，
`run_daynight_capture.ps1` 会两个目录都找并复制到 `Saved/<profile>/baseline.csv`。
`-ExecCmds` 用逗号分隔且会 trim，取值命令必须写成 `name=value`（不能写 `name value`）。

## 16. 运行时开关：`fps.body.WorldBody`（2026-09-22，供用户现场测试）

用户要求现场可开关第三人称模型以便自行对比帧数。**两个开关，语义不同**：

| 控制台变量 | 默认 | 作用 | 生效时机 |
| --- | --- | --- | --- |
| `fps.body.WorldBody` | 1 | **运行时开关**。0 = 隐藏第三人称身体网格 + 世界武器副本 + 配件副本 + outfit 网格 | 立即（有 cvar 回调，不等 0.2 s 刷新） |
| `fps.body.WorldBodySuppress` | 0 | 采集隔离用。1 = 整个会话根本不建立世界身体 | 只在初始化时读一次，必须命令行设置 |

### 16.1 只隐藏身体网格是不够的

世界武器、配件、outfit 副本是**各自独立的组件，各自投射阴影**。只关身体网格，
成本会原样转移到这些副本上。所以 `UFPSPlayerBodyComponent::ApplyWorldBodyVisibility()`
统一处理全部四类组件（身体 / `WorldWeapons` / `WorldParts` / `OutfitMeshes`）。

### 16.2 会覆盖开关的三条路径，都已处理

这是实现里最容易出错的地方——身体可见性会被三处反复重设，任何一处漏掉，
开关就会被「弹回去」：

1. `InitializeBody()`（初始化最后）
2. `UpdateOwnerVisibility()`（每 0.2 s 的可见性刷新）
3. `UpdateWorldOwnerVisibility()`（**`CalcCamera` 每次相机更新都会调用**）

三处最终都汇到 `ApplyWorldBodyVisibility()`。
第 3 处尤其关键：相机路径在第三人称下会把身体设回可见，
所以那里加了 `FPSPlayerBodyWorldBodyHidden()` 早退。

### 16.3 修正了一个我自己引入的回退

`ApplyWorldBodyVisibility()` 一开始无条件把 `VisibilityBasedAnimTickOption`
设为 `AlwaysTickPoseAndRefreshBones`，这会**在第一人称下撤销**之前那项
tick-option 优化（第一人称时身体是 owner-no-see，刷新骨骼是纯浪费）。
现已按「开关开 **且** 处于第三人称」才刷新骨骼。

### 16.4 使用方式

PIE 或独立运行中按 `~` 打开控制台：

```
fps.body.WorldBody 0     // 隐藏第三人称模型，观察帧数
fps.body.WorldBody 1     // 恢复
```

身体网格**保留常驻内存**，所以来回切换是瞬时的，不需要重新加载。
配合 `stat unit` 看 Game / Draw / GPU 三个数的变化最直观。

### 16.5 未验证

按用户全局规则，**本项未做主动测试**：只确认编译通过（`FPSGAME Win64 Development`
→ `Result: Succeeded`）。开关的实际视觉效果与帧数影响由用户现场判断。
编辑器版链接需要用户关闭编辑器（DLL 被占用），已在后台等待任务中排队。