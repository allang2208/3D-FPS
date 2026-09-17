# 左手占用提示与双持施法拒绝（2026-09-16）

用户确认火球在双持状态下无法释放是正确的，但不应停在「等待左手」：双持时左手被副手手枪占着，等待本身不会让手空出来，所以请求必须直接拒绝。提示改为「左手占用」，跳动 3 秒后消失，逻辑上不再等左手空闲后补发火球。

## 规则

- `AFPSGAMECharacter::IsLeftHandHeldForCast()` 表示左手被装备长期占用。当前只覆盖双持手枪的副手（`IsDualWieldingPistols()`），只有换装备／退出双持才会释放。
- `UFPSFireballComponent::Trigger()` 在该状态下直接拒绝凝聚与发射请求，不设置 `bQueuedCast`／`bQueuedLaunch`。已经排队、途中才切换成双持的请求同样丢弃，不会在左手空出来后补发。
- 反馈优先级：左手占用提示 > 冷却／缺蓝等 1.5 秒提示。原来的「等待左手」只保留给会自行结束的冲突（换弹、近战、采集、检视、ADS、穿行），行为不变。
- 冰锥共用同一条左手仲裁与手势，镜像同样的双持拒绝和提示。

## 提示表现

- `FFPSLeftHandNotice`（`Source/FPSGAME/Skills/FPSLeftHandNotice.h`）按世界秒计时：3 秒窗口，0.4 秒一次闪烁＋上跳（峰值 5 px），最后 0.35 秒淡出，随后回到正常状态文字。
- `ColdSteelQuickSlot` 在绑定槽上给自己的状态文字做透明度与上跳位移，不新建控件、不改冷却遮罩、不写业务状态。
- 提示期间该槽的数字冷却读秒让位给「左手占用」，因为这是对玩家按键的直接回应。

## 实现入口

- `Source/FPSGAME/Skills/FPSLeftHandNotice.h`（新增）：提示窗口与闪烁／跳动曲线。
- `Source/FPSGAME/Skills/FPSFireballComponent.h/.cpp`：`RejectHeldLeftHand()`、`StatusText()` 优先返回「左手占用」、`IsHandOccupiedNotice()`／`HandNoticeAlpha()`／`HandNoticeRise()`，并在 `TryBeginQueuedCast()`／`TryBeginQueuedLaunch()` 丢弃失效排队。
- `Source/FPSGAME/Skills/FPSIceSpikeComponent.h/.cpp`：同样的拒绝入口与提示；`ServiceQueue()` 在已排队时检测到双持就丢弃。
- `Source/FPSGAME/FPSGAMECharacter.h/.cpp`：新增 `IsLeftHandHeldForCast()`。
- `Source/FPSGAME/UI/ColdSteelQuickSlot.cpp`：状态文字的跳动提示与冷却读秒优先级。

## 验收边界

源码接入已完成；改动包含带 UHT 的头文件（两个技能组件新增成员），必须关闭编辑器做全量编译，不能热补丁。本轮未编译、未进 PIE，按用户规则由用户测试：双持时按火球／冰锥提示跳动 3 秒后消失且不补发；退出双持后重新按键可正常施法；普通换弹／近战等待仍然生效。
