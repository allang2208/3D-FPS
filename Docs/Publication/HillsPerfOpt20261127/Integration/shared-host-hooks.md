# 共享宿主与未合并模块集成说明（`HillsPerfOpt-R50 ～ R57`）

以下模块在本机工作区中与并行功能/重构交织，或尚未向公开 `origin/main` 合入基础类。为避免把其他功能的未验收拆分或头文件带入 `main`，本次公开提交在 `origin/main` 基础上完整推入了独立模块、工具、文档与纯净补丁，并将共享宿主上的挂点精确记录于此，供后续合入对应并行模块时复用或核对：

## 1. HUD `UInvalidationBox` 主框与叶子绘制分层（未含未合入拆分的文件）
由于 `ColdSteelHUDWidget.h/.cpp`、`ColdSteelHUDConstruction.cpp`、`ColdSteelCrosshair.cpp`、`ColdSteelFireballHUD.cpp` 与 `ColdSteelTopVitals.cpp` 在本机工作区已包含大量 UI 拆分与骑乘/法书并行改动，本次仅直推了可无冲突合入的 R56/R57 UI 守卫文件，主框架与叶子隔离挂点如下：
- **三层根结构（`ColdSteelHUDWidget.h` / `ColdSteelHUDConstruction.cpp` / `ColdSteelCrosshair.cpp` / `ColdSteelHUDWidget.cpp`）**：
  - `UColdSteelHUDPaintLayer`：独立 `UUserWidget` 子类，覆写 `NativePaint`，分挂 `BackPaintOverlay`（`Z=-100`，弓镜光学遮罩）与 `FrontPaintOverlay`（`Z=200`，准星/罗盘/标记/目标框）。
  - `HUDInvalidationBox`（`UInvalidationBox`，开关 CVar `fps.HUD.InvalidationCache=1`）包裹主 `ColdSteelRoot`（`Z=0`）。
  - `NativeTick` 仅对 `FrontPaintOverlay` 与按需状态改变的 `BackPaintOverlay` 调用 `CachedWidget->Invalidate(EInvalidateWidgetReason::Paint)`，不再整树每帧重刷。
  - `UpdateInteractHint()`（`ColdSteelHUDConstruction.cpp` L263–L272）对 `InteractHintBlur` 与 `InteractHintTitle` 的 `SetVisibility()` 增加差异判断。
- **20 Hz 生命周期组件指针缓存（`ColdSteelTopVitals.cpp` L196–L219、`ColdSteelFireballHUD.cpp` L30–L40）**：
  - 按 `TWeakObjectPtr<const APawn> + CompCount` 缓存 `UFPSCombatHealthComponent`、`UFPSIceArmorComponent`、`UFPSSurvivalComponent`、`URuneOrbBladesComponent`、`UStaffWeaponComponent` 与 `UStarMarrowComponent`，避免 `RefreshTopVitals` 与 `RefreshQuickBar` 每次重复扫描组件数组。
- **天气时间轴折叠态呼吸脉冲缓存字段（`ColdSteelHUDWidget.h` L813–L814）**：
  - 在 `UColdSteelHUDWidget` 私有区添加 `float LastTimelineLineOpacity = -1.f;` 与 `float LastTimelineMarkerOpacity = -1.f;`，配合 `NativeTick` 仅在活跃降雨或展开时以 `0.15 s` / `>= 0.03` 脉冲写入透明度，折叠待机态恒定 `0.88 / 0.94`。

## 2. 角色 `Tick` 分段剖析与相机组件指针复用
- `Source/FPSGAME/FPSGAMECharacter.cpp` / `FPSGAMECharacterCamera.cpp` 在本机工作区已完成大拆分重构（相比 `origin/main` 拆出多个子文件）；本批 R57 对应改动：
  - 在 `AFPSGAMECharacter::Tick` 植入 `FPSChar_Traversal`、`FPSChar_ProfileTick`、`FPSChar_MovementRefresh`、`FPSChar_WeaponState`、`FPSChar_CameraViewmodel`、`FPSChar_ActionPose` 6 个 `TRACE_CPUPROFILER_EVENT_SCOPE` 观察点。
  - 在 `AFPSGAMECharacter::UpdateCamera` 内复用 `auto* Body = FindComponentByClass<UFPSPlayerBodyComponent>();` 局部指针（消除同帧 `RestoreCloseCameraClearance`、`ApplyOwnerCameraOffset`、`UpdateCloseCameraClearance` 三处重复查找）。

## 3. 尚未发布至 `origin/main` 的独立 Actor 优化挂点
- **伐木场工人与运木马车（`LumberMillWorkerActor.h/.cpp`、`LumberMillTimberWagon.h/.cpp`）**：在所属网格设 `EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered` 与 `bEnableUpdateRateOptimizations = true`，并分别复用 `fps.Hills.ResidentRayTracingDistCm` 与 `fps.Hills.HorseRayTracingDistCm` 控制 3P 光追代理开关。
- **村庄守备特斯拉闪电塔（`VillageLightningSpire.cpp`）**：`OnRep_Setup` 创建 `CrownLight`（`SpireCrownGlow`）时设置 `SetCastVolumetricShadow(false)` 与 `SetVolumetricScatteringIntensity(0.08f)`。
- **远景暖窗采集对村庄仓库的弱耦合兼容（`VillageDistantGlow.cpp`）**：公开提交版本通过按类短名 `FName(TEXT("VillageWarehouseActor"))` 识别流送仓库（`CollectMountWindows`）以避免未发布头文件依赖；本地全量版保留强类型 `#include "VillageWarehouseActor.h"`。
