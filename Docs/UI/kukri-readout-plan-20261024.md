# 尼泊尔弯刀右下角武器状态栏 · 2026-10-24

## 范围与布局

`ue_kukri` 沿用 `UColdSteelAmmoReadout` 的主手栏目：武器完整名称、`单手近战 · 左键挥砍`、分隔线、左右两列资源读数。使用冷钢既有 360px 宽、最小 124px 高的玻璃外壳、字体、颜色、右下锚点和快捷栏避让，不新增控件或独立 HUD。短标签横排；副手段整组折叠；背包及抽屉展开期间按现有规则隐藏。

## 数据与状态

- 原显示入口仅接受双手剑与双手钝器；增加现有 `IsOneHandedMelee` 分类，使弯刀进入 `PresentMelee`。
- 左列 `可普通攻击次数`：复用 `MeleeStaminaReadout`，当前体力除以 `ColdSteelMelee::AttackStamina` 后向下取整。弯刀 `BeginAttack` 已使用同一耗体入口。零消耗为 ∞，零次红色、一次黄色。
- 右列 `体力回满时间`：复用剩余恢复延迟与实际恢复率；满体力为 0.0 s，暂停恢复和不恢复沿用既有文字及字体。体力模型已包含弯刀重击蓄力的暂停状态。
- 沿用 HUD 的 `RefreshAmmo` 调度；近战文字只在变化时更新。不新增 Tick、计时器、输入、存档或业务写入。
- 切回枪械、弓或法杖沿用各自显示入口。状态栏仍不获取焦点、不拦截点击，生命周期沿用现有 HUD。

## 修改与交付

代码仅修改 `Source/FPSGAME/UI/ColdSteelAmmoReadout.cpp` 的分类入口与近战说明。共享体力模型和弯刀战斗实现均无需修改。

后台 Game 构建日志：`Saved/BuildEditor/build-game-kukri-readout-20261024.log`。本次 `ColdSteelAmmoReadout.cpp` 已完成编译；完整构建在 `Production/ProductionWarhammerRift.cpp` 失败（`FWhirlwindCast` 不存在 `ReadySeconds`、`SpinSeconds`、`TurnDegrees`，以及 `TObjectPtr` 不能由 `auto*` 推导），最终 `Failed (OtherCompilationError)`，用时 307.22 秒，未生成新的游戏可执行文件。该文件属于其他并行修改，本轮未编辑或回退它。

当前编辑器正在运行，未关闭它；Editor 普通构建待该编译阻塞消除且编辑器退出后执行。本轮交付为源码与文档落盘，不能视为当前编辑器已经应用。未启动游戏、PIE、测试或截图，画面由用户测试。

后续接续：同日用户选择使用本地第三人称动作后，已随该功能完成 Game 和 Editor 两项目标构建，上述阻塞已消除。新的构建回执为 `SourceAssets/KukriThirdPerson20261024/build-receipt.json`；见 [本地第三人称接入](../Weapons/kukri-third-person-local-20261024.md)。未运行游戏测试。
