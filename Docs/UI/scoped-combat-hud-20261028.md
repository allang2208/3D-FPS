# 黑色外围高倍镜：保留战斗 HUD

2026-10-28，按用户最新要求，高倍镜 ADS 保留伤害数字、怪物血量栏、自身状态、快捷键栏及右下武器状态栏。本合同替代旧版开镜隐藏所有游戏面板的行为。

## 实现与覆盖

移除 `AFPSGAMEPlayerController::PlayerTick` 内随 `GetScopePresentationAlpha` 隐藏全部顶层 Widget 的逻辑及可见性快照，不再由瞄准状态接管面板可见性。无需为每款镜复制 HUD 或重建控件。

- 共用枪械入口：LPVO、PSO、手枪镜、M24 原厂镜、KV 与热成像镜均由 `ULPVOScopeWidget` 展示；镜框/黑色外围保持 PlayerScreen Z=10，现有 `ColdSteelHUD` 为 Z=20。
- 观峰弓镜：继续在 HUD 子控件之前绘制其独立圆形遮罩，所有 HUD 子控件及目标反馈位于其上方。
- 伤害数字沿用 `ColdSteelDamageNumbers`；怪物血量与状态沿用当前目标反馈；自身生命/体力等状态、Buff、快捷栏及 `ColdSteelAmmoReadout` 沿用已有数据与布局。
- 目标血量沿用现有目标获取及反馈生命周期，不增加隔墙显示或全体怪物常驻血条。
- 背包、菜单、弹药轮盘、死亡和加载等场景的显示规则仍由原控件控制。开关镜不再恢复旧的可见性快照，因此不会把本应关闭的菜单或面板重新显示出来。

光学倍率、分划、武器视模隐藏、后处理、伤害与联机数据通道均沿用原实现。本次只调整本地玩家 UI 显示策略，覆盖所有消费共用瞄准镜入口的枪械。

## 交付记录

旧源码备份、构建脚本和构建结果在 `SourceAssets/ScopeCombatHUD20261028/`。没有新增或修改内容资产。按用户工作规则只执行必要后台构建，不启动 UE 或游戏，不进行视觉、运行或联机测试。

`FPSGAME Win64 Development` 与 `FPSGAMEEditor Win64 Development` 均已构建成功；游戏可执行文件和基础 Editor DLL 已更新。
