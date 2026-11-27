# 持法杖左键统一发射、R 轮盘冲突防线与联机施法闭环（2026-11-27）

**第一条（FPSGAME）　文件落盘与引用路径。** 先查[制作目录与功能索引](../../../Docs/Production/README.md)与[存储规则第 4.1 节](../../../WORKFLOW.md#41-存储分配与文件操作边界)。交互改动涉及输入、状态模型、技能组件与 HUD 时须同步更新消费端，交付时登记源码入口与编译版本。

本页补充[持杖施法与预览／发射一致性](staff-cast-and-aim.md)，沉淀 2026-11-27 法杖施法交互重构与全链路排错规则（`StaffLMBPreparedRelease_20261127`）。

---

## 1. 持法杖左键统一发射合同（快捷键与轮盘互通）

- **武器适用边界**：仅当 **装备法杖（`Staff->IsEquipped()`）** 时生效；持步枪、手枪、刀剑、弓或空手时左键保持原开火/攻击逻辑，避免留存左手火球/冰锥时阻断枪械或近战操作。
- **左键释放优先级**：`AFPSGAMECharacter::FirePressed()` 在持法杖分支先判定 `!Model->PreparedStaffMagicSkill().IsNone() || !Model->SelectedMagicSkill().IsNone()`，随后进入 `UColdSteelStatusModel::PressStaffMagic()`：
  1. 先查 `PreparedStaffMagicSkill()`（覆盖 4 大积蓄待发魔法：`fireball` / `iceSpike` / `iceWall` / `blizzard`，无论起手来自数字快捷键还是 R 轮盘）；
  2. 若存在已积蓄魔法，无论 R 轮盘当前为空还是选中了其他魔法，**左键一律优先走该积蓄魔法的释放规则**（火球/冰锥/暴风雪按住预览→松开发射，凝聚中途点按排队连发；冰墙点按确认竖墙）；释放完成后下一击自动恢复轮盘施法或挥杖近战；
  3. 若无已积蓄魔法，再按 R 轮盘 `SelectedMagicSkill()` 施法，轮盘为空时进入法杖近战挥杖。
- **右键职责纯化**：不将鼠标右键绑定到释放积蓄魔法；持法杖时右键专供副手（副手法典专注切换、副手手枪射击或副手火把攻击），彻底避免积蓄魔法期间抢占法典专注开关。
- **HUD 同步**：`ColdSteelStaffReadout` 读取 `PreparedStaffMagicSkill()` 与轮盘选中法术的实时 `StatusText()`；当已有积蓄魔法时显示「`左键释放：<法术名>`」（若与轮盘选法不同，魔法名下方状态行亮金提示「`已积蓄：<法术名> · 左键释放`」）。

---

## 2. 预览归属隔离与施法卡死防线

- **拒收绝不覆写预览归属**：`ColdSteelQuickBarModel::BeginSpellAimPreviewForSkill()` 仅在目标组件**实际进入**预览或待发态（`IsLeapAimPreviewActive` / `IsMeteorAimPreviewActive` / `IsThunderLancePending` / `IsAimPreviewActive`）后才写入 `AimPreviewIndex` 与 `AimPreviewSkill`，防止被拒收的陨星/雷枪/跃击劫持其他按键的释放权。
- **按源取消预览**：取消统一走 `CancelOwnedAimPreview(InputSource)`，仅清理该输入源持有的预览，不误伤其他正在凝聚的暴风雪或雷云域；`PrepareForPanelInput()`、`SuspendWeaponForMenu()` 与 `ResetActionsForPriority()` 必须同步清理快捷栏预览态，全部用 `RuntimePawn()` 优先解析本地角色。
- **防空轮盘误挥杖**：`UStaffWeaponComponent::BeginPrimaryAttack()` 除检查 `IsSpellGestureBlocking()` 与 `IsCastBlockingLeftHandAction()` 外，必须拦截 `UFPSFireMagicComponent::IsMeteorAimPreviewActive()`，避免 R 轮盘为空时按住快捷键选点陨星期间误点左键触发挥杖。
- **冷资源绝不留脏队列**：`dragonBreath` 等技能在素材未就绪时于 `Trigger()` 立即拒收反馈，**严禁**写入 `QueuedSkill` 等待——否则会永久锁死 `IsSpellGestureBlocking()` 导致长按 R 轮盘与挥杖全部失效。
- **后台预载插队**：`FPlayerSkillPreparation` 启动时按「当前持杖选法 > 轮盘绑定 > 快捷栏绑定 > 未绑定目录」排序，并在选法（`SelectMagic`）和施法（`PressStaffMagic` / `UseQuickSkill` / `BeginSpellAimPreviewForSkill`）调用 `PrioritizeSkillAssets()` 插队，消除后期轮盘魔法数十秒冷等待。

---

## 3. 联机施法与同步核查清单

- **客机积蓄态占位**：`FPSFireballComponent::HasPreparedCast()` 需含 `bNetExpectOrb`、`FPSIceSpikeComponent::IsPrepared()` 需含 `bNetExpect`，防止服务端实体尚在复制途中客机重复起手或左键误落入挥杖；客机认领 `AdoptNetOrb` 时同步预览状态并刷新 `NetSpeed / NetDropDelay` 与 `NetRange`；火球/冰锥松手释放须上报锁定的 `CommittedAimPoint` 而非服务端延后重算相机视线。
- **防心跳风暴与防卡死**：Profile 同步时将所有已归零法术冷却统一归一化清零（避免微小浮点残留引发整包 Profile 频繁同步）；Listen Server 房主观测客机蓄寒（如 `FPSAbsoluteZeroComponent::NetBeginChannel`）不依赖 `OnRep`，直接驱动本地表现；客机 `bNetAwaitingRelease / bNetAwaitingCancel` 设 `3.5 s` 超时自动退蓝解锁；远端环爆设足 `NetCullDistanceSquared`（如 `150 m`），晚入场（`Age > 0.75 s`）静默续演不补播首爆音效震屏。
- **近战回执周期对齐**：修改法杖等近战攻速时同步核对 `ColdSteelGenericMelee.cpp` 服务端回执最短间隔与客户端动画时钟一致，防止连击被服务端误拒。
