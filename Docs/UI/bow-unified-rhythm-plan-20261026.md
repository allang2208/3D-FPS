# 弓节拍与穿心箭统一进度条

> 后续用户调整见 [红色脉冲与持续耗体](bow-piercing-red-stamina-plan-20261026.md)：穿心就绪改为红色脉冲，取消自动射箭，按重击规则持续耗体。下文保留本轮连续进度条的布局与初版接入记录。

## 授权与范围

用户认可“一条连续进度条、两个释放节点”的方案并要求继续接入。本次修改准星下方现有圆弧与短条、成功释放反馈及联机拒绝时的预测反馈清理；技能倍率、穿透、箭速、3 秒门槛、完美窗口和持弓时限沿用现有玩法。

本方案替代 heart-piercing-arrow-plan-20261026.md 中先显示完美节拍、再将短条清空显示穿心蓄力的初版表现。B 提示保持移除。

## 结构与视觉

- HUD 的现有只读 Slate 绘制入口 → 满拉圆弧 + 单条连续进度条；不新增控件、焦点、输入事件、文字、技能图标或外围圆环。
- 圆弧沿用 44px 半径、90° 下弧；显示拉弓完成度，满拉后保持形状。完美时金色提亮，穿心就绪时银白提亮；继续蓄力不重新展开。
- 短条沿用 120×4px，中心位于准星下方 64px。普通时序为拉弦 54px、完美窗口 18px、穿心蓄力 48px。
- 全部低亮度轨道、金色完美窗口和空心穿心菱形从实际开始拉弦时显示。指针从左向右连续推进；经过完美窗口后保留已填充部分，继续填充后段。
- 穿心就绪使用技能真实布尔状态：空心菱形变实心、已填区域与圆弧转银白，保持至松弦或自动放箭。
- 完美区采用两条短刻线，穿心采用约 7px 菱形；位置、形状和颜色共同表达释放时机。
- 使用 ColdSteelUIStyle 的 HUDGold、HUDGoldLight、HUDGoldDim、TextPrimary、TextSecondary。沿用深色细描边和 HUD PixelScale，微小视口沿用原限位缩放。

## 时间映射与重叠

数据来自本次拉弓的 FullDrawSeconds、Elapsed、PiercingSeconds、bPerfect 和 bPiercingReady。实际时间不因显示宽度改变。

普通时序：

1. `0 → FullDrawSeconds` 映射 `0 → 54px`。
2. `FullDrawSeconds → FullDrawSeconds + PerfectReleaseWindow` 映射 `54 → 72px`；真实完美窗口仍为 0.20 秒。
3. `完美窗口结束 → max(FullDrawSeconds, PiercingSeconds)` 映射 `72 → 120px`。

若慢弓使穿心门槛落在完美窗口内，取消额外等待段，拉弦段使用 102px、完美区保留 18px；穿心菱形放在该窗口内对应的真实门槛位置。两状态同时满足时，银白填充配金色窗口边线／菱形轮廓。指针仍单调向右，释放时保留对应位置。

未学会穿心箭时只显示拉弦与完美窗口，不显示穿心标记。严格超过 3 秒的判定继续由玩法提供，时间到达标记位置本身不会点亮就绪状态。

## 反馈、取消与生命周期

- 完美箭和穿心箭成功进入放弦后，分别保留金色／银白反馈 0.15 秒并淡出；重叠时保留银白与金边。沿用实际释放时的快照，不重算装备或技能等级。
- 早松普通箭不播放技能成功提示。搭箭、DrawEntry 举弓准备、缓收弓、待机不显示进度；只在实际 Drawing／Holding 和有效释放反馈期间绘制。
- 新一轮拉弓、取消、死亡与换装通过现有动作生命周期清除上次成功标志。反馈不会更改弓弦机械回弹使用的 ReleaseFeedbackAge 时钟。
- 客户端沿用现有即时预测；服务器拒绝弓射击时同时撤回预测的完美加速与两种成功反馈。不新增 RPC 或伤害字段。

## 数据与性能

UBowWeaponComponent 在 GetDrawRhythm 提供只读快照；绘制阶段只做分段映射、颜色与固定数量线段，不读取 JSON、不加载纹理、不重建 HUD。圆弧采样沿用静态缓存，菱形复用已有点缓冲。

文件范围：

- Source/FPSGAME/UI/ColdSteelBowRhythm.cpp
- Source/FPSGAME/Weapons/Bow/BowWeaponComponent.h/.cpp
- Source/FPSGAME/Multiplayer/ColdSteelBowAuthority.cpp

没有存档、图标、伤害或装备数据变更。无新增监听或资源，生命周期继续由现有 HUD 和弓组件管理。

## 交付阶段

源码已接入；必要后台构建记录写入 Saved/BowUnifiedRhythm20261026。未主动运行测试、游戏、截图或视觉验收，实际观感由用户测试。

- FPSGAME / Win64 / Development：Succeeded，251.78 秒，Binaries/Win64/FPSGAME.exe 已更新。
- FPSGAMEEditor：暂缓。构建入口和游戏目标完成后，现有 UnrealEditor.exe 均仍占用工程；保留运行中的编辑器，没有关闭、重启或覆盖已加载模块。当前编辑器会话尚不包含本轮改动，关闭后可执行 Saved/BowUnifiedRhythm20261026/build.ps1 完成编辑器构建。
- 未运行测试或进行视觉验收。
