# 共享宿主最小化合入与本地拆分分支对照（`SkillMagicCloseout-20261127`）

为严格遵守 `WORKFLOW.md` 第 7 / 8 节（不夹带未收口并行会话的代码与未合入的大文件拆分重构），本次在 `origin/main` 独立隔离 worktree 上采用 **纯净文件直推 + 共享宿主最小化手术补丁** 的策略，以下记录所有与本机全量工作区存在结构差异的共享宿主文件，供后续合入并行重构时核对：

## 1. 角色宿主：`FPSGAMECharacter.h/.cpp` 与 `FPSGAMECharacterActionPriority.cpp`
本机工作区已由并行会话将 `FPSGAMECharacter.cpp` 拆分为 `FPSGAMECharacterInput.cpp`、`FPSGAMECharacterActionAvailability.cpp`、`FPSGAMECharacterCamera.cpp` 等多个子文件，且包含手持木火把/骑乘等尚未公开合入的改动。本次公开提交直接将本批必需挂点最小化合入 `origin/main` 的单文件 `FPSGAMECharacter.cpp` 与 `FPSGAMECharacterActionPriority.cpp`：
- **组件创建与声明**：`FPSGAMECharacter.h` 新增 `friend class UFPSAbsoluteZeroComponent;`；`FPSGAMECharacter.cpp` 引入 `#include "Skills/FPSAbsoluteZeroComponent.h"` 并在构造函数创建 `CreateDefaultSubobject<UFPSAbsoluteZeroComponent>(TEXT("AbsoluteZeroSkill"))`。
- **移动锁定与菜单/施法阻塞**：
  - `IsMeleeSkillMovementLocked()` 新增 `(AbsoluteZero && AbsoluteZero->IsChanneling())`。
  - 菜单打断清理新增 `if(auto* AbsoluteZero=FindComponentByClass<UFPSAbsoluteZeroComponent>())AbsoluteZero->CancelPending();` 与 `if(IsLocallyControlled())if(auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Model->CancelSpellAimPreview();`。
  - `IsSpellGestureBlocking()` 新增 `if(const auto* AbsoluteZero=FindComponentByClass<UFPSAbsoluteZeroComponent>();AbsoluteZero&&AbsoluteZero->HasQueuedAction())return true;`。
  - `FPSGAMECharacterActionPriority.cpp` 的 `InterruptActionsForPriority()` 新增 `if(IsLocallyControlled()&&Profile)Profile->CancelSpellAimPreview();`。
- **法杖左键统一释放（`FirePressed` / `FireInputReleased` / `FireReleased`）**：
  - `FirePressed()` 在 `Staff && Staff->IsEquipped()` 分支优先判断 `!Model->PreparedStaffMagicSkill().IsNone() || !Model->SelectedMagicSkill().IsNone()` 并调用 `Model->PressStaffMagic()`，否则执行 `Staff->BeginPrimaryAttack()`。
  - `FireInputReleased()` 在 `Staff && Staff->IsEquipped()` 分支调用 `Model->ReleaseStaffMagic()`。
  - `FireReleased()` 顶部在 `IsLocallyControlled()` 下调用 `Model->CancelStaffMagic()`。
  - `AimPressed()` / `AimReleased()` 保持原状（右键仅负责副手法典专注 / 副手武器，不参与施法释放）。

## 2. 法杖组件与三视角动作：`StaffWeaponComponent.cpp` 与 `FPSPlayerBodyActions.cpp`
本机工作区的 `StaffWeaponComponent.h/.cpp` 包含并行会话的手持木火把共用挥击改造（`TorchHand` / `PairedTorchMesh` / `OutFov`），`FPSPlayerBodyActions.cpp` 包含骑乘与火把姿态改动。本次公开提交仅将以下 4 处本批挂点合入 `origin/main` 基线，不引入任何火把/骑乘依赖：
- `StaffWeaponComponent.cpp`：
  1. 新增 `#include "../../Skills/FPSFireMagicComponent.h"` 与 `#include "../../Skills/FPSAbsoluteZeroComponent.h"`。
  2. `CastingPoseInCamera()` 优先返回 `AbsoluteZero->SampleStaffSlamPose(Carry)`（当 `IsEquipped() && AbsoluteZero->IsPresentingStaffSlam()`）。
  3. `GetCameraMotion(FVector& Location, FRotator& Rotation)` 叠加 `AbsoluteZero->GetCameraMotion(AzLoc, AzRot, nullptr)`（保持 `origin/main` 原两参签名；本地三参 `OutFov` 版本在合入火把分支时透传 `OutFov`）。
  4. `BeginPrimaryAttack()` 新增 `if(const auto* FireMagic=Pawn->FindComponentByClass<UFPSFireMagicComponent>();FireMagic&&FireMagic->IsMeteorAimPreviewActive())return;`，防止空轮盘陨星选点期间点左键误触挥杖。
- `FPSPlayerBodyActions.cpp`：新增 `#include "../Skills/FPSAbsoluteZeroComponent.h"` 并在 `FireballMagic` 施法分支后补齐 16 行绝对零度第三人称/多人观察者举杖顿地姿态同步。

## 3. 状态公式、快捷槽与联机存档同步的定向剥离
以下共享文件在本机工作区混有并行会话（热油叠层、伐木场运木、仓库扩容、HillsPerfOpt HUD 缓存）的未公开挂点；本次公开提交仅保留本批功能补丁：
- `CombatStatusFormula.h/.cpp`：仅合入 `ConsumeFrostForShatter()` 与 `AddStun()` 中绝对零度蓄寒轻僵直抗性（`<= 0.35 s`）；剥离并行 `AddOilBurn` 叠层改签。
- `ColdSteelStatusModel.h`：仅合入 `AbsoluteZero*` 技能声明、`PreparedStaffMagicSkill()`、`CancelOwnedAimPreview()`、`PrioritizeSkillAssets()` 与 `AbsoluteZeroSkill` 成员；剥离并行仓库升级/伐木场运木与横幅通知声明。
- `ColdSteelInventoryTypes.h`：仅合入 `AbsoluteZeroCooldown / Duration / bAbsoluteZeroReserved / ReservedMana` 4 个存档字段；剥离并行 `PendingLumberWood` 与 `WarehouseUpgradeRanks`。
- `ColdSteelPlayerState.h`：仅合入 `#include "../Skills/AbsoluteZeroTypes.h"` 与 `PendingAbsoluteZeroStats`；剥离并行伐木场/仓库 RPC。
- `ColdSteelPlayerProfileSync.cpp`：仅合入全法术冷却与预留蓝量归一化清理（防 84 KB 心跳风暴）；剥离并行 `PendingLumberWood` 合并行。
- `ColdSteelQuickSlot.cpp`：仅合入 `absoluteZero` 图标冷却、手部占用提示与蓄寒金边（`NativeTick` + `Refresh`）；剥离未在 `origin/main` 合入的 `FindCachedSlotComponent` HUD 缓存改动。
- `ColdSteelGenericMelee.cpp`：本地对齐法杖普攻 `0.84 s / 0.58 s` 周期的改动依赖未发布的 `IsWoodenTorch` 与 `StaffPrimaryAttackMotion::StrikeStart/StrikeEnd` 新常量，留待与法杖/火把近战重构分支一并合入。
