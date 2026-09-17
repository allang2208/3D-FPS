# 地形改造接入：体素沙盒 + 丘陵弹坑（2026-09-16）

> **2026-09-16 已退役（体素部分）**：经性能评估，项目决定**不引入体素地形**，地貌破坏只保留高度场方案，现行标准见 [地貌破坏：高度场方案](../WorldGeneration/terrain-destruction-20260916.md)。本文保留为历史记录：体素插件、局部洞穴测试台的接入过程与性能排查都在这里；相关代码与测试地图已归档到 `trash/voxel-terrain-retired-20260916/`（含 SHA-256 清单），VoxelFree 与 VoxelPluginInstaller 在 `.uproject` 中已置为 `Enabled: false`。

把免费的 **Voxel Plugin Free Legacy** 接进 `D:/FPS3D/FPSGAME`：装上插件、编进 Editor 目标、加一层自己的运行期入口，并建一张可以立即挖／炸的沙盒地图。本文记录实际接入内容、证据边界和尚未做的事。来源、许可与收费情况见 [Voxel Plugin 安装器登记](VoxelPlugin-installer-20260916.md)。

本次边界：没有跑 PIE、没有实机点技能、没有做存读回归、没有截图或帧率测试——按用户规则由用户自行测试。下面所有"已生成／已编译"都有日志或文件时间戳支撑，但都不等于玩法与画面验收。

## 1. 用的是哪一份插件

| 项 | 内容 |
| --- | --- |
| 名称 | Voxel Plugin Free Legacy（免费版；Fab 上的 `Voxel Plugin Installer` **不能**安装它） |
| 来源 | GitHub `https://github.com/VoxelPlugin/VoxelPluginFreeLegacy`，`master` @ `7e64a89ce827b44a75c83a939e2c2e2e42bee61d`（2026-06-24） |
| README 口径 | "This code should compile on 5.6, 5.7 and 5.8" |
| 本地位置 | `D:\FPS3D\FPSGAME\Plugins\VoxelFree`（工程 `Plugins/` 已在 `.gitignore` 内，不进公开仓库） |
| 取材方式 | `git clone --depth 1 --filter=blob:none --sparse`，sparse 只取 `Source / Config / Shaders / Resources`，另外单独下载 `Content/Editor/**`（37 个编辑器图标，约 0.22 MB）。示例内容 `Content/Examples`（约 195 MB）没有取，所以没有示例地图。 |
| 体积 | 源码约 4.5 MB；编译产物 `Binaries` 约 626 MB、`Intermediate` 约 379 MB（本地缓存，不进仓库） |
| 许可待确认 | 该仓库没有 LICENSE／EULA 文件。正式对外发行前必须按其官网条款确认；本机保持"只在本工程内使用、不公开分发"。 |

## 2. 启用与编译

- `FPSGAME.uproject`：加入 `{"Name": "VoxelFree", "Enabled": true, "MarketplaceURL": "com.epicgames.launcher://ue/marketplace/content/b08e5581837e4bbca486b61cdf2751bb"}`（MarketplaceURL 来自插件描述符；缺它编辑器每次启动会提示 "Project FPSGAME requires update"）。
- `Source/FPSGAME/FPSGAME.Build.cs`：`PublicDependencyModuleNames` 增加 `"Voxel"`。
- 编译：`Tools/Build/Build-Editor.ps1`（FPSGAMEEditor Win64 Development）。插件模块 `Voxel / VoxelHelpers / VoxelGraph / VoxelEditor / VoxelEditorDefault / VoxelExamples / VoxelGraphEditor` 与 `FPSGAME` 一起编译链接成功；本模块只剩插件自带的 `double→float` 警告。
- 编辑器启动日志证据：`LogPluginManager: Mounting Project plugin VoxelFree`，随后加载上述 7 个模块 DLL。
- 已知无害警告：插件同时带 `Config/BaseVoxelFree.ini` 与 `DefaultVoxelFree.ini`（内容相同），引擎提示前者为弃用名。属第三方包内容，本次未改动。

## 3. 我们自己的代码入口

新增 `Source/FPSGAME/WorldGeneration/VoxelTerrainRuntime.{h,cpp}`：一个 `UWorldSubsystem`，是地形体素的唯一入口（20 cm 建造体素仍归 `UVoxelBuildWorld`，两套语义不混用）。关卡里没有 `AVoxelWorld` 时全部空转，不影响现有地图。

| 接口 | 作用 |
| --- | --- |
| `Get(WorldContext)` | 取子系统；`nullptr` 表示这个关卡没有体素地形 |
| `GetVoxelWorld()` | 关卡里的 `AVoxelWorld`（缓存） |
| `CarveSphere(Center, RadiusCm)` / `FillSphere(...)` | 挖／填一个球，返回 `FVoxelTerrainEditResult{Modified, Removed, MinCell, MaxCell, bValid}` |
| `CarveCrater(Contact, Normal, EffectRadiusCm)` | 爆炸弹坑：球心沿命中法线压入地表 |
| `CarveAtAim(Radius, Range, Out)` | 从玩家相机打射线，在命中点编辑 |
| `SaveTerrain` / `LoadTerrain` | 存读 `Saved/VoxelTerrain/<地图>.voxsave`（独立于 ColdSteel 角色档案） |

控制台命令（游戏内可用）：

| 命令 | 说明 |
| --- | --- |
| `fps.VoxelTerrain.Info` | 打印体素世界名、是否已创建、体素尺寸、深度与包围盒 |
| `fps.VoxelTerrain.Dig [半径cm]` | 准星命中点挖球 |
| `fps.VoxelTerrain.Fill [半径cm]` | 准星命中点填球 |
| `fps.VoxelTerrain.Save` / `fps.VoxelTerrain.Load [文件]` | 地形编辑存档的存／读 |

CVar：`fps.VoxelTerrain.CraterRadiusScale`（默认 1.2，体素弹坑半径＝效果半径×该值）、`fps.VoxelTerrain.CraterDepthScale`（默认 0.6）、`fps.VoxelTerrain.DigRadius`（默认 60）、`fps.VoxelTerrain.DigRange`（默认 2000）、`fps.VoxelTerrain.DebugLog`（默认 0）；丘陵高度场地形另有 `fps.Hills.CraterRadiusScale`（默认 1.5）、`fps.Hills.CraterDepthScale`（默认 0.4）、`fps.Hills.CraterRimScale`（默认 0.12）。

玩法挂钩（本次只接了火球一处）：

- `AFPSFireballProjectile::Explode` 调用 `UVoxelTerrainRuntime::CarveTerrainCrater(this, Contact, Normal, Cast.Radius)`，这是"这次爆炸改变地面"的统一入口：**关卡里有 `AVoxelWorld` 就挖体素球**，**有 `ATemperateHillsWorld` 就往高度场里打一个碗形弹坑**，两者都没有（出生地主城）返回 false、原行为不变。
- 其它爆炸源（手雷、炸药桶）和镐／铲类工具都可以走同一个入口／`CarveSphere`，尚未接线。

## 3.1 丘陵高度场弹坑（2026-09-16 追加）

温带丘陵不是体素地形，它是 `ATemperateHillsWorld` 的运行时高度场 + 64 m 分块动态网格。所以弹坑按"**高度场印章**"实现，而不是往体素世界里挖：

| 环节 | 实现 |
| --- | --- |
| 形状 | `TemperateHillsSurface::FCrater{X,Y,Radius,Depth,Rim}`：半径内是碗（`-Depth·(1-t²)²`），半径外一圈抬起的唇（`+Rim·(1-u)²`）。两条曲线都在边界处零斜率，所以弹坑外面地形法线不变 |
| 高度 | `ATemperateHillsWorld::Height()` = `BaseHeight()`（河流／噪声）＋ 弹坑偏移。偏移在碗内为**负**（下陷）、在唇上为**正**（微抬）；`SurfaceNormal()` 只在弹坑影响范围内改成数值法线，其余仍用原生成法线（便宜） |
| 重建 | 只把弹坑覆盖到的分块标脏（`InvalidateTerrainCells`），旧网格继续留在场上，新网格异步生成并烹饪好碰撞后才替换——不会因为炸坑让玩家瞬间掉进地里，也不会触发整片世界重新流送 |
| 存档 | `UTemperateHillsSave` 升到 Version 2，带 `TArray<FHillsCraterRecord>`；旧 V1 存档仍可加载（只是没有弹坑）。每打一个弹坑立即写一次槽 |
| 上限 | 每个世界最多 256 个弹坑，超出后淘汰最旧的并把它覆盖到的分块重建回生成高度 |
| 日志 | 打中时 `HILLS_CRATER x= y= radius= depth= rim= count=`；分块失效 `HILLS_CRATER invalidate_cells=…`；恢复存档 `HILLS_CRATER restored=…` |

已知限制：已经被打坏的格子不会让树木／岩石重新落地（PCG 实例不随弹坑重算，只有新生成的点会用新高度）；河道水面网格不随弹坑重建；远景 backdrop 用的是另一套简化高度，不参与弹坑。

## 3.2 地貌编辑的自然度（2026-09-16 第二次）

用户反馈"连续炸出弹坑后棱角明显"。原因与处理：

| 棱角来源 | 处理 |
| --- | --- |
| 相邻弹坑用加法叠加，交界处出现尖脊／双深 | 弹坑之间改用**平滑最小值**合并（`SmoothMin`，k=60 cm），重叠的两个坑融成一个碗 |
| 弹坑是标准正圆、深度一致，重复炸很"机械" | 每个弹坑按位置取种子，轮廓与深度各叠加两个低频谐波（半径 ±11%、深度 ±10%），同一处永远同一形状 |
| 编辑分块沿用 100 cm 顶点间距，3 m 碗只有 3 个顶点 | 被编辑过的分块网格分辨率**翻倍**（详细格 64→128 格 = 50 cm，粗格 32→64），棱角显著减少；只有被编辑的少数分块付这个代价 |
| 法线在坑内仍是生成法线 | 弹坑影响范围内改用数值法线（±100 cm 步长），过渡处零斜率 |
| 铲子方块步进是刀切边 | 方块边缘加 50 cm smoothstep 过渡带（中间仍是平的 20 cm 层） |

## 3.3 火球清草与铲子挖掘／回填（20 cm 规则）

| 项 | 行为与数值 |
| --- | --- |
| 火球清草 | 弹坑半径 × 1.15 内的**草类**实例被移除：`Grass / GrassAccents / RiverGroundCover / RiverReeds / RiverBankGrasses`；**不动树（骨骼实例）、岩石、灌木、鹅卵石**。PCG 分块流送回来后，每秒对玩家 80 m 内的编辑重新清一次，避免草"长回来" |
| 铲子挖掘 | 铁铲（8）左键。3 次命中为**一层**：在 **240 × 240 cm（12 × 12 个 20 cm 格）** 的足迹上下降 **20 cm**，中心对齐 20 cm 世界网格。同一格可反复挖、越挖越深；下限 = 生成地面 −400 cm（4 m）。每次完成产出 2 个「泥土」（沿用原表土奖励） |
| 右键回填 | 铁铲（8）**右键**（工具在手时右键不再是 ADS）：在同样足迹上抬高 20 cm，消耗 **2 个「泥土」**，上限 = 生成地面 +100 cm（5 层）。海拔超限或泥土不足会在提示栏播报原因 |
| 斜率／河床 | 沿用表土采集门槛：坡面法线 Z < 0.65 或河床湿区拒绝（"陡坡或河床不可铲取表土"） |
| 物品 | **没有"泥土体素块"物品**。现有材料 `soil`（泥土，material 类）即挖掘产出／回填消耗的介质。要做成可放置的「泥土体素块」需要新增调色板材质 + 图标 + 承重数值（改承重必须跑 `Tools/Building/run_voxel_stress_probe.ps1`），本次未做 |
| 存档 | 这些编辑与弹坑同源存在世界槽里（Version 3：`Edits` 数组，V2 的圆形弹坑在读取时自动迁移） |
| 日志 | `HILLS_STEP`（每层挖／填）、`HILLS_REFILL`（回填）、`HILLS_GROUND_COVER`（清草数量）、`HILLS_CRATER`（火球坑） |

铲子的物品说明（`Content/ColdSteelData/production_tools.json`）已同步更新，不再写"当前不挖空地形"。

## 3.4 局部体素洞穴测试台与"一击一层"（2026-09-16 第三次）

高度场做不出竖井／洞穴／悬垂，所以按"不动现有地形、只加一块本地体素区"的思路做测试台：

| 项 | 内容 |
| --- | --- |
| 新增 Actor | `AFPSVoxelCavePad`（`Source/FPSGAME/WorldGeneration/FPSVoxelCavePad.*`） |
| 怎么出现 | 由丘陵世界在 `BeginPlay` **自动生成**（CVar `fps.Hills.VoxelPad`，默认 1 = 开；设 0 关闭），因此不需要改地图资产；也保留手动摆放脚本用于把测试台固定在某个地图里 |
| 位置 | 运行时按**种子**定位：丘陵出生点 + `StartOffset`（默认 +30 m），Z = 该点局部地表 +20 cm。换种子/换世界都不用改地图 |
| 体素参数 | 体素 50 cm；自定义边界 ±64 体素＝**64 m 见方**（不用自定义边界时平地生成器会铺到几公里，穿透周围高度场）；生成器 `VoxelFlatGenerator`（平板以下全实体）；材质 `M_TemperateGround` |
| 能做什么 | 往下挖竖井、横向挖洞穴、掏悬垂；平板抬高 20 cm 贴在局部地表之上，玩家站在体素板上，铲子射线打到的是体素而不是高度场 |
| 不能做什么 | 走出版边界就回到高度场地形；洞里没有天光；体素编辑**目前不写进丘陵世界存档**（只在会话内，`fps.VoxelTerrain.Save/Load` 可手动存读），导航也没有专门的体素 invoker |
| 手动摆放（可选） | `Tools/SceneTests/Add-VoxelCavePad.ps1`（启动编辑器→放置/更新 Actor→保存地图→退出，不跑游戏）；报告写在 `Saved/SceneTests/voxel-cave-pad.json`；运行时日志统一是 `VOXEL_PAD placed x= y= z= voxel= half_voxels=` |

同时把铲子改成**一击一层**（原来 3 次命中才算一层）：

| 项 | 规则 |
| --- | --- |
| 丘陵高度场 | `FProductionResource::HitsRequired=1`（只对 Layer 2 表土；树和岩石仍然是 3 次）。左键一下 = 240×240 cm 足迹整体下降 20 cm、产出 2 个泥土；同一格可继续往下挖（下限 −400 cm），右键回填 +20 cm（上限 +100 cm，消耗 2 泥土） |
| 体素地形 | 铲子左键**一次**挖掉半径 90 cm 的球（`fps.Tool.ShovelVoxelRadius` 可调），产出 2 个泥土；右键回填一个球并消耗 2 个泥土。提示栏会报"挖走 N 个体素格／回填 N 个体素格" |

**瞄准距离（2026-09-16 第四次）**：铲子原来沿用 3.2 m 的工具触及距离，眼高 1.7 m 时只有俯角很大才能命中地面，实际表现成"只能挖脚底下"。铲子现在用独立的瞄准距离 `fps.Tool.DigReach`（默认 **1000 cm**）：左键挖掘、右键回填都走"屏幕中心射线"，站着眼平视前方 10 m 内的地面也能挖；斧头/矿镐仍旧是 3.2 m 触及。

## 3.5 体素台加进来以后丘陵变卡的排查（2026-09-16 第四次）

先说结论：**最大头是体素世界的"可见分块碰撞"**，不是内存泄漏。Voxel Plugin 默认 `bComputeVisibleChunksCollisions=true`（`VisibleChunksCollisionsMaxLOD=5`），意思是**每一个可见分块都要烹饪碰撞**；我们的测试盒有自定义边界，盒子侧壁（32 m 高、64 m 长）也会被当成"可见分块"一起烹饪，于是整个丘陵都跟着掉帧。已改的默认值（`AFPSVoxelCavePad`）：

| 项 | 原值 | 现值 | 作用 |
| --- | --- | --- | --- |
| `bComputeVisibleChunksCollisions` | true | **false** | 碰撞只按 invoker（相机兜底，半径 10 m）生成，不再为每个可见分块烹饪碰撞——这是本轮最大的性能改动 |
| `MaxLOD` | `ClampMesherDepth(32)`（几乎不限） | **4** | 远处分块用粗 LOD，不再全分辨率网格 |
| 体素盒半边长 `HalfVoxels` | 64（64 m 见方、侧壁 32 m） | **40（40 m 见方、侧壁 20 m）** | 体积与侧壁面积大幅下降 |
| `bGenerateDistanceFields` / `bEnableNavmesh` / `bDebugManager` | 关/关/开 | 关/关/关 | 去掉距离场、导航网格与调试管理器开销 |

如果还想再省：`fps.Hills.EditMeshBoost 1`（编辑过的分块不再翻倍细分，代价是坑更方）、`fps.Hills.VoxelPad 0`（整块体素台不生成，回到原来的高度场性能）。

**可见分块碰撞到底开不开（2026-09-16 第五次）**：插件头文件对这项的注释就是 `If false, use only invokers collisions settings`，所以它不是必须项，而是两种模式之一：

| 模式 | 代价 | 后果 |
| --- | --- | --- |
| 可见分块碰撞 = 开（插件默认，`VisibleChunksCollisionsMaxLOD=5`） | 每个可见分块都要烹饪碰撞网格；分块越多越卡，内存也随分块增长 | 玩家看得见的地面基本都有碰撞；但远处是粗 LOD 碰撞 |
| 可见分块碰撞 = 关（**当前默认**） | 只有 invoker 半径内烹饪碰撞（相机兜底 invoker，半径 1000 cm = 10 m，LOD 0 高精度） | 玩家附近碰撞**更准更便宜**；**10 m 外的体素地形完全没有碰撞**：子弹/投掷物/掉落物/布娃娃在远处会穿过地面，快速冲刺或长距离下落有可能跑在碰撞生成前面而短暂穿地；怪物需要自己挂 voxel invoker（且体素 navmesh 未开） |

因此：当前 40 m 单人测试台用"关"最划算；如果以后体素地形铺满全图，推荐中间档——`fps.Hills.VoxelPad.VisibleCollisions 1` 配 `fps.Hills.VoxelPad.VisibleCollisionsMaxLOD 2~3`（远处给粗碰撞兜底），再给玩家与怪物各挂一个 voxel invoker（碰撞半径 15–20 m）。这三个开关都是 CVar，但**在测试台创建世界时读取**，改完要重进地图才会生效；插件自带 `voxel.LogCollisionCookingTimes 1` 可以直接量化碰撞烹饪耗时。

排查用的读数（游戏内控制台）：

| 命令 | 看什么 |
| --- | --- |
| `stat voxel` | 体素线程池的分块生成/网格/碰撞任务耗时（CPU 侧是不是它） |
| `stat voxelmemory` | 体素数据与分块的内存占用（判断内存是不是它） |
| `stat unit` | 帧时间拆分：Game / Draw / GPU，先判断卡在 CPU 还是 GPU |
| `stat game` | 游戏线程各系统耗时（体素、PCG、地形流送、碰撞） |
| `memreport -full` | 按类列出内存占用（配合 `-LogMemory` 写进日志） |
| `fps.Hills.VoxelPad 0` | A/B：关掉体素台，若完全不卡了就是它 |
| `fps.Hills.EditMeshBoost 1` | A/B：如果只在挖了很多坑之后才卡，是编辑分块细分/重建的代价 |

> 体素台在会话内编辑不存档，但**每次挖洞都会重建受影响分块的网格与碰撞**；短时间连续炸/挖几十次会看到连续的重建波，这是编辑系统的固有代价，不是内存泄漏。

## 4. 沙盒地图

`/Game/GameMaps/L_VoxelTerrain_Test` 由 `Tools/SceneTests/create_voxel_terrain_test.py` 生成，可重复执行；重跑只更新同名 Actor，不重复生成。

| Actor | 说明 |
| --- | --- |
| `VoxelTest_World`（`AVoxelWorld`） | 位于原点；`create_world_automatically`、`use_camera_if_no_invokers_found` 打开；体素 1 m、`RenderOctreeDepth=10`（世界边长约 1024 m）、`MaxLOD=6`；生成器 `VoxelFlatGenerator`（地面正好在 Z=0）；`VoxelMaterial = /Game/WorldGeneration/TemperateHills/M_TemperateGround` |
| `VoxelTest_PlayerStart` | (0, 0, 200)，落在地面正上方 |
| `VoxelTest_Sun` / `_SkyLight` / `_SkyAtmosphere` / `_Fog` | movable 光照，不依赖主地图的灯光管理器 |

地图使用工程默认 `FPSGAMEGameMode`，所以角色、枪械、火球、HUD 都是现有真系统。生成报告写在 `Saved/SceneTests/voxel-terrain-test.json`。

一键重建（会启动编辑器、跑脚本、再退出编辑器；不跑游戏）：

```powershell
& 'D:\FPS3D\FPSGAME\Tools\SceneTests\Create-VoxelTerrainTest.ps1'
```

## 5. 手工验证清单（由用户执行）

1. 打开 `L_VoxelTerrain_Test` 并 Play：地面应在出生点下方、可站立行走、材质正常（不是灰色默认材质）。
2. 火球打地面：应出现弹坑；`fps.VoxelTerrain.DebugLog 1` 可看编辑日志。
3. `fps.VoxelTerrain.Dig 200` / `fps.VoxelTerrain.Fill 200`：准星指向地面时挖／填一个 2 m 球。
4. `fps.VoxelTerrain.Save` → 退出 → 重进 → `fps.VoxelTerrain.Load`：弹坑应恢复（这条没有测过）。
5. 温带丘陵样地：站在坡地上用火球打地面 → 应立刻出现碗形坑（一两帧内先看到旧地面、随后换成新网格），能走进坑里；日志有 `HILLS_CRATER x=… radius=… count=…` 与 `invalidate_cells=…`。
6. 丘陵弹坑持久化：从丘陵走门回主城再进丘陵（或退出重进）→ 之前打的坑仍在，日志 `HILLS_CRATER restored=…`。
7. 确认 `DayNight_Lighting`（主城）行为不变：那里地面是静态地板，火球只留特效，这是当前设计。

## 6. 未完成 / 已知限制

- 未运行任何测试：以上都是接入与编译证据；PIE、弹坑表现、存档往返、帧率、光照／Nanite 质量全部待用户判定。
- 地形编辑还没有接进 ColdSteel 存档：现在只有独立 `.voxsave`，没有 `WorldId`／`Generation` 语义，也没有自动存读时机。
- 玩家身上没有挂体素 invoker 组件（沙盒用相机兜底）。真实地貌世界应给角色加 `UVoxelSimpleInvokerComponent`（半径略大于原生导航 invoker），否则远处 LOD／碰撞／导航覆盖不足。没做的原因：`FPSGAMECharacter.cpp` 当前有并行会话改动，避免冲突。
- 没接 PCG／植被／天气／导航：地形可挖之后，树木岩石悬空规则、`NavigationSystem` 动态重烘焙、地表湿度参数都还没重新对齐。
- 没有替换温带丘陵后端：`TemperateHillsWorld` 的运行时高度场分块网格仍是丘陵样地的实现，弹坑是叠在它上面的高度场印章（见 3.1）。
- **出生地主城仍然不参与地貌改变**：`DayNight_Lighting` 的地面是一块 40 cm 厚的静态实体地板（`Floor`），既不是高度场也不是体素地形，所以火球在那里只留下特效。要让它也能被打坏，需要把地板换成可变形网格（动态网格地板）或者放一块体素地面，两者都改变主城外观／碰撞，未做。
- 沙盒地图只有一块平面平地（`VoxelFlatGenerator`）。要丘陵地貌需要另做体素图（Voxel Graph）或高度图来源；插件示例内容没有取。
- 插件的 `create_world` 没有暴露给 Python，脚本只能设置 Actor 属性；地形实际生成发生在关卡加载时（本次日志：`VoxelWorld_0 took 0.875s to generate`）。
- 把整张开放世界换成体素地形是一次后端替换（流送、LOD、碰撞烹饪、存档、植被、导航全部要重做），不是本次范围。
