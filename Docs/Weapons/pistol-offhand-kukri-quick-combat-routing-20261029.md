# 手枪＋副手弯刀：快速近战分派修正（2026-10-29）

本轮按用户要求进行源码排查并修改：只要当前搭配为主手手枪、副手弯刀，快速近战就由副手刀处理。ADS、冲刺、持刀姿态的过渡权重不再决定使用哪件武器；无法施放时直接拒绝，不回退到手枪砸击。

## 原因和修改

`UColdSteelStatusModel::TriggerQuickCombat()` 原先以 `Offhand->CanQuickCombat()` 决定是否进入副手刀分支。该查询要求没有 ADS、没有冲刺、右手姿态权重大于 0.95，而且刀已经占有可见左手。任一条件不成立就继续走主手手枪分支。这同时影响 ADS、冲刺、刚结束检视/换弹/占手动作的窗口。

- 技能入口改为按 `IsEquipped()` 分派；F 和快捷栏共用。
- `AFPSGAMECharacter::TriggerPistolQuickCombat()` 的直接调用也先交给已装备的副手刀。
- 刀的启动查询保留装备、模型就绪和统一动作优先级要求，不再用当前可见姿态筛选。
- 接受输入后，先按原优先级中断可打断动作，再确认左手所有权，使用原副手刀突刺。
- 清理被中断的持刀入场及换弹支撑臂过渡，接管手臂权重；退出冲刺并明确恢复主手 Idle 动画，覆盖 SingleNode 和动画图路径。

## 源码覆盖清单

| 路径/状态 | 检查与处理 |
| --- | --- |
| F 键 | `DefaultInput.ini` → `QuickCombatPressed` → `TriggerQuickCombat`；固定副手刀路由。 |
| 快捷栏、技能调用 | `UseQuickBinding` → `UseQuickSkill(quickCombat)` → 同一技能入口。 |
| 直接手枪近战入口 | `TriggerPistolQuickCombat` 增加副手刀优先分派。 |
| 腰射、ADS、进出 ADS | 删除刀入口的瞄准限制；原优先级中断清除瞄准输入，出刀期间原占手门控阻止重新开镜。 |
| 冲刺、走动、蹲姿、空中 | 不再因冲刺或持刀姿态权重不足变成砸枪；保留原移动与动作优先级合同。 |
| 开火、检视、换弹执行阶段、消耗品、可中断施法 | 先执行 `InterruptActionsForPriority(false)`，再确认刀取得左手；清理旧播放与表现过渡。 |
| 换弹收刀/回手过渡、切枪/拔枪、菜单、推门、死亡、已有快速近战/上挑 | 保留原统一拒绝条件；拒绝时不再落入砸枪。 |
| 刀资源尚未就绪 | 拒绝此次施放，不启动主手砸击，也不提交刀的体力费用。 |
| 两组主副手槽 | 原装备识别按活动主手槽取其配对副手；不依赖固定第一组。 |
| 支持的手枪 | `ColdSteelInventory::IsDualPistol`：M1911、G18、Pit Viper 2011、Dan Wesson 715、RSH-12，共用此次修改。 |
| 第一人称手臂、持刀和枪避让、镜头 | 继续使用 `OffhandKukriAuthoredStrike` 单次突刺和同一动作时钟；未替换动画资产。 |
| 体力、命中与成长 | 原 `CommitQuickCombatCast` 一次提交；`SlashCount=1`，命中对象去重，刀的实例进入伤害快照；正常结束/取消释放占用。 |
| 服务端伤害 | `ColdSteelPlayerState` 从活动主副手槽校验申报实例；`OffhandKukriThrust` 复算刀伤害，攻击形态为 Blade；无 ADS/冲刺砸枪分流。 |
| 网络拒绝、切换、菜单、结束 | 现有取消路径释放刀动作和技能占用，不另启动手枪动作。 |
| 单持枪、双手枪、主手刀及其他武器 | 装备分类维持原分支；此次没有更改其动作或数值。 |

## 边界与交付

检查是源码检查，没有启动编辑器、游戏、PIE、联机测试或截图验收。后台 `FPSGAMEEditor Win64 Development` 和 `FPSGAME Win64 Development` 均构建成功，分别落盘到 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 和 `Binaries/Win64/FPSGAME.exe`；编译不代表实际动作与画面验收。

本轮输入修正时发现第三人称尚未采样副手刀快速近战时钟。用户随后要求补齐第三人称出刀，后续动作、消费者与逐枪贴合调整见 [第三人称出刀记录](pistol-offhand-kukri-third-person-20261029.md)。

本轮修改四个源码文件，修改前的工作区副本保存在 `Saved/OffhandKnifeQuickCombat20261029/Before/`；保留原有未提交和暂存修改，未提交/推送 Git。必要构建日志位于 `Saved/OffhandKnifeQuickCombat20261029/`。
