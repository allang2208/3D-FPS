# 弓节拍器：下移、透明背景、完美节拍改为下一次拉弓 +25%（2026-10-18）

用户要求三项调整：

1. 攻击拉弓的节拍器进度条整体往下调整一定距离；
2. 背景改为透明；
3. 完美节拍的效果从原来的“本箭伤害 ×1.25”改为“命中节拍后，下一次射击的拉弓速度 +25%”。

## 一、HUD 节拍器

`UI/ColdSteelCrosshair.cpp::PaintBowRhythm`：

| 项目 | 改动 |
| --- | --- |
| 垂直位置 | 准星中心 `+50px` → `+96px`（1080p 基准，约下移 46px）；`Width=208 / Track=192` 不变 |
| 背景 | 无任何底板：不画圆角外框、不画轨道底线、不填底色；原 `GlassTint` 深灰底与 `Content` 实心轨道均已移除 |
| 轨道/进度/亮标 | 无轨道底；金色进度、金色 0.20s 判定窗口、白色亮标 |
| 提示文字 | **已全部删除**（原“拉弓 · 金色区间松手 / 松手 · 下次拉弓 +25% / 节拍已过 · 满拉 / 完美释放 · 下次拉弓 +25%”），只留进度条 |
| 判定脉冲 | 进度落在金色判定区间（`Rhythm.bPerfect`）时，给整条进度条外缘加一圈呼吸式金色描边：外扩 `2 + 2.5×Wave` px、透明度 `0.35 + 0.55×Wave`、`Wave=0.5+0.5·sin(now×2π×2.2)`（约 2.2Hz）；完美释放后的 0.45s 反馈期继续脉冲 |
| 淡入淡出 | 仍由 `Rhythm.Opacity` 统一控制 |

## 二、效果：下一次拉弓速度 +25%

- 新常量 `ColdSteelBow::PerfectNextDrawSpeedBonus = .25f`，替换原 `PerfectReleaseMultiplier`。
- 拉弓耗时：`DrawSeconds = 基础满拉耗时 / (1 + 0.25)`，与装备、附魔、改造、巧手的拉弓速度处于同一乘区；面板与真实时钟仍由同一个 `Evaluate().Draw` 计算。
- 触发：手动满拉（≥100%）且在满拉后 0.20s 窗口内松手并成功放箭 → 置位“下一次拉弓加速”。力竭自动放箭、提前松手、取消收弓不置位。
- 消耗：该标记在**下一次成功放箭**后按本次是否完美重设（完美→继续保留，非完美→清除）。中途收弓/取消不消耗，下一次实际射击仍享受。
- 伤害：完美节拍的 ×1.25 伤害加成已移除；命中节拍不再直接提高本箭伤害。

## 三、联机同步

- `AColdSteelPlayerState::bBowPerfectSpeedBonus`：`UPROPERTY(Replicated)`，`COND_OwnerOnly`；服务器在接受完美节拍射击后置位，非完美射击清除；只读访问器 `BowPerfectSpeedBonusPending()`。
- 客户端 `UBowWeaponComponent::bPerfectSpeedPending`：本机在完美放箭成功时立即置位，保证服务器回执到达前本机下一箭的时钟已经正确。
- `ServerSetBowDraw`：服务器用同一份 `DrawSpeedScale(bBowPerfectSpeedBonus)` 计算 `BowDrawSeconds`，因此客户端与服务端的满拉时长、0.20s 窗口一致；服务端仍以自己时钟核对释放时间。
- 已知边界：完美射击的请求与下一次拉弓开始若在网络上严重乱序，服务器可能仍按基础时长记录这次拉弓；这一箭仍会正常发射，只是不会被判为完美。属于既有 0.15s 容差之外的极端情况。
- 状态清理：卸下弓（`RefreshEquipment` 无弓）清客户端 `bPerfectSpeedPending`；服务器在 `ServerSetBowDraw` 检测到死亡时清 `bBowPerfectSpeedBonus`，避免重生/换弓后白拿一次加速。

## 四、实现落点

- `Weapons/Bow/BowStats.h`：`PerfectNextDrawSpeedBonus`、`DrawSpeedScale()`。
- `Weapons/Bow/BowWeaponComponent.h/.cpp`：`bPerfectSpeedPending`、`SetStage(Drawing)` 重算满拉时长、完美放箭置位、移除本箭伤害倍率。
- `Multiplayer/ColdSteelPlayerState.h/.cpp`：复制字段、`DOREPLIFETIME_CONDITION`、只读访问器。
- `Multiplayer/ColdSteelBowAuthority.cpp`：`ServerSetBowDraw` 应用倍率；`ExecuteBowShot` 移除伤害倍率并维护下一次加速标记。
- `UI/ColdSteelCrosshair.cpp`：下移、无底板、删文字、判定区间金色脉冲描边。
- `UI/ColdSteelItemTooltipData.cpp`：武器详情「完美节拍」说明改为下一次拉弓 +25%。

## 五、边界与未测

- 只改弓；其它武器、技能、修炼、箭伤曲线、50% 最低拉距均不变。
- 构建：Game `FPSGAME.exe` 20:20:00、Editor `UnrealEditor-FPSGAME.dll` 20:19:27；BowWeaponComponent / ColdSteelCrosshair / ColdSteelBowAuthority / ColdSteelPlayerState / ColdSteelItemTooltipData 的 obj 均晚于源文件，`Result: Succeeded`。
- 未运行游戏/PIE/截图/联机测试；实际下移距离、透明观感与联机节拍由用户验收。下移量是 `PaintBowRhythm` 中一个常量（`96.f`），如偏上/偏下可直接调。
