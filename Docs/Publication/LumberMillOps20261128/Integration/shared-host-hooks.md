# 共享宿主与并行模块集成说明（`LumberMillOps-R58 ～ R62`）

本机工作区中，以下共享宿主文件同时包含并行会话（`QuarryCamp-R1`、`VillageDoorsR1`、`HillsVillageWarehouse`、`KukriGuard20261127`）尚未合入 `origin/main` 的改动。按 `WORKFLOW.md` §7–§8，公开推送仅直推纯净独立模块、制作工具、沉淀 SKILL 与最小纯净补丁，将共享宿主挂点精确记录于此，避免向 `origin/main` 引入未合入的跨功能依赖：

## 1. 伐木场运营调度与任务子系统（依赖共享宿主接口）
- `Source/FPSGAME/WorldGeneration/LumberMillOperationsSubsystem.{h,cpp}`
- `Source/FPSGAME/WorldGeneration/LumberMillQuestSubsystem.{h,cpp}`
  - 依赖 `ATemperateHillsWorld` 独立存档字段与接口（`LumberMillQuestVersion=2`、`IsLumberMillRepaired()`、`GetLumberMillQuestState()`、`GetLumberMillLastSettledDay()`、`CommitLumberMillLastSettledDay()`）。
  - 依赖 `UHillsNightRaidSubsystem::HasUnresolvedInvasion()` / `GetLivingRaiderCount()` 与 `AVillageDefenseGate` / `AHighVillageGate` 幂等 `SetDoorOpen(bool)` / `IsDoorOpen()`（东门 16 m 提前开启、9.5 m 车尾清离后自动关闭）。
  - 依赖 `AColdSteelDoubleDoor::SetDoorOpenAuto(bool, float, bool)`（来自 `VillageDoorsR1`，驱动运输工进出酒馆正门自动开关且零穿门）及 `AQuarryStoneWagon`（来自 `QuarryCamp-R1`，防止两车共用东门时互相关门）。
  - R62 新增热路径缓存：`CachedEastGate`（`1 s` 冷却）、`CachedTavernDoor`（`1 s` 冷却）、客机端 `ResolveWagonActor()` 缓存（`0.5 s` 冷却）。

## 2. M 键世界地图方案 A 补给路线特效（`SupplyRouteVFX-R60`）
- `Source/FPSGAME/UI/SColdSteelWorldMap.cpp`：
  - 新增 `FRouteSilkCanvas`（`MakeCustomVerts` 7 站对称高斯羽化丝带）与 `SampleUniformRibbon()` 等弧长重采样，绘制方案 A「冷钢鎏金丝流」（压地暖暗底影 + 暖金光晕 + 鎏金丝带 + 2 道液态金扫光 + 4 枚波照实心微箭标 + 5 颗径向柔焦光斑 + 实心暗铜鎏金端点徽章）、17:00 实车进度分段与东门局部红盾封锁告警。
  - 因本机同文件已并入 `QuarrySupplyRoute` 采石场第二路线，暂以集成规范与 [Slate 自定义顶点丝带 SKILL](../../../../skills/ue5-ui-umg-slate/references/slate-custom-verts-supply-route.md) 随批公开，待采石场模块同步合入 `main`。

## 3. 每日 +50 木材联机入仓与顶部通知栏（`R57`）
- `Source/FPSGAME/Multiplayer/ColdSteelPlayerState.h` / `ColdSteelPlayerProfileAdmission.cpp`：`GrantLumberMillWoodDelivery`、`ClientNotifyLumberWoodDelivery`、`ClientNotifyLumberSupplyBlocked`。
- `Source/FPSGAME/UI/ColdSteelStatusModel.h` / `ColdSteelWarehouseModel.cpp` / `ColdSteelAreaPickup.cpp` / `ColdSteelProgressNotification.cpp`：`ReceiveLumberMillWoodDelivery`、`TryFlushPendingLumberWood`、`PostBannerNotice`（FIFO 队列 + `Icons/wood.png` + 四级冷钢语义配色）。

## 4. 玩家装备组件去贴花补丁（`R58`）
- `Source/FPSGAME/Characters/FPSPlayerBodyEquipment.cpp`：在 `ApplyOwnerVisibilityFlags` / 外装部件创建处统一补 `SetReceivesDecals(false)`（其余 3 处无冲突文件 `FPSPlayerFirstPersonBody.cpp`、`FPSPlayerBodyComponent.cpp`、`FPSModularOutfitComponent.cpp` 的 `SetReceivesDecals(false)` 纯净补丁已随本批直接推送至 `origin/main`）。
