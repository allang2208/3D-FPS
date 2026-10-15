# 双手锤右下角状态面板

按用户要求复用双手剑的 `ColdSteelAmmoReadout::PresentMelee`：上方为当前武器名、“双手钝器 · 左键挥击”，下方左列“可普通攻击次数”、右列“体力回满时间”。沿用 360px 冷钢外壳、共享字体、单行标签、低次数颜色、右下定位和快捷栏避让。

## 数据与状态

- 双手锤使用工具动作执行器，`ActiveProductionTool()` 返回当前锤实例；面板允许该实例进入近战分支。背包铁铲覆盖主手时继续排除收起的武器，斧／镐不因本次接入变成双手锤。
- 次数由现有 `MeleeStaminaReadout` 读取 `ColdSteelMelee::AttackStamina`，与战锤 `ColdSteelTool::Evaluate`、单人及服务端攻击扣体力共用实际消耗，包含改造、临时效果和装备消耗倍率。按当前体力向下取整，零消耗为 ∞，零次红色、一次黄色。
- 体力回满时间继续包含剩余恢复延迟和当前恢复倍率；满体力为 0.0s，停止恢复显示“暂停恢复”，零恢复率显示“不恢复”。不另建计时器或计算公式。
- 法杖第二行、书本说明和副手整组在切到双手锤时折叠；切回枪械沿用原标签、字体与弹药刷新。面板只读、无输入或存档变更，跟随现有 HUD 刷新并在菜单打开时让位。

修改范围为 `Source/FPSGAME/UI/ColdSteelAmmoReadout.cpp` 及 UI 规则／SKILL 参考。无新增资产，进行必要后台构建；未要求游戏、UI、联机测试，由用户测试。

## 本轮构建结果

已有的 Game Development 构建纳入本次修改，第 3/41 个动作编译 `ColdSteelAmmoReadout.cpp`，第 40/41 个动作链接 `Binaries/Win64/FPSGAME.exe`，最终 `Result: Succeeded`。完整回执保留于 `Saved/BuildEditor/hammer-readout-shared-game-20261014.log`；本任务未重复启动构建。

项目仍有后台 `UnrealEditor-Cmd` 进程占用 Editor DLL，保留其现场，Editor 目标尚未更新。未进行游戏或界面测试。
