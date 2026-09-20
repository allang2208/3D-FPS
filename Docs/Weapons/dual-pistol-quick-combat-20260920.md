# 双持手枪快速进战

## 当前候选：改造后保留转枪与 recover 腕臂 V5

用户要求即使枪械改造也保留转枪恢复，并优化 recover 手腕形变。已制作 [SpinRecoveryV5](../../SourceAssets/DualPistolQuickCombat20260920/SpinRecoveryV5/README.md)：compact、wide、long 三套完整转枪轨迹，按每只手的配件分别选择；长消音器分支优先，包含同时安装瞄具/战术配件的情况。主手恢复时前送外展，转轴向前臂方向倾斜，让枪口在外侧完成一整圈；副手稍晚归位。

recover 现在让肩、肘、腕共同支撑握姿，并把轴向扭转逐段分配到上臂和前臂辅助骨，拇指与其余手指错开接柄。0.80 秒动作、0.18 秒单次接触、轮换出手及原 F 触发修复保持。新目录含 36 条 120 Hz 动画，四份完整 Blend 与 FBX 留在作者目录；V3 对照资产保留；V4 已在本轮整理中归档。

36 条动画已通过当前编辑器保存到 `/Game/Weapons/DualPistolQuickCombat20260920/SpinRecoveryV5`。运行加载与分档在 `PistolDualWieldComponent.cpp`，必要编译记录见作者目录 `compile-result.txt` 与 `integration-status.json`。本轮不启动 PIE、运行测试或绘制验收图，作为候选交由用户试玩；不宣称所有装配组合已无穿模。

## 归档与待定位事项

当前源依赖和归档清单见 [发布说明](dual-melee-overhead-publication-20260920.md)。DW715 枪身／弹巢形变尚未解决，`SpinRecoveryV5/RigidFix` 仅为诊断。以下为各阶段历史记录；已退役 V1／FlowV2／V4 的原路径统一在本机 `trash/dual-melee-overhead-retired-20260920/` 下按相对路径保存，历史“保留”不表示它们仍为运行默认。

## 历史 V4：F 触发与改造件避让

用户要求排查双持偶发 F 无反应及改造件穿模。已修正双持检视写入并遗留单持忙碌状态，以及射击/掏枪表现尾段不能让位给近战的问题；真实换弹和公共动作占用仍阻止近战，新增具体拒绝原因日志。旧失败日志只有“武器动作未结束”，无法唯一还原刚才那次占用状态。

当时裸枪使用已认可的 VideoRefV3，装有外扩瞄具、灯/激光或枪口件的每只手改用保持握持回收的 AttachmentClearanceV4，避免翻枪时配件穿过手掌和前臂。十二条动画导入保存，19:47:32 Live Coding 成功；时长、左右轮换及单次接触合同不变。该“改造后取消翻枪”的动作分支已被上面的 V5 候选替代，F 触发修复继续保留。详见 [历史制作与排查记录](../../trash/dual-melee-overhead-retired-20260920/SourceAssets/DualPistolQuickCombat20260920/AttachmentClearanceV4/README.md)。

本次按用户要求执行了源动画配件几何排查：两款枪左右手各采样 68 个时刻，所检查配件与持枪侧手臂在 V4 中无表面相交。该结果限定于记录中的源装配样本，未进行完整 UE 实机手感验收。

隔离状态回归 `FPSGAME.Weapons.DualPistol.QuickCombatState` 已排队，覆盖旧检视状态、两手射击/掏枪尾段、换弹、菜单、滑铲及单持边界。当前先受编辑器后台帧率等待影响，随后编辑器处理另一批编译，尚无执行完成结果；不将“已排队”计为通过。结果收集脚本为 `AttachmentClearanceV4/collect_diagnostics.py`，阶段记录位于 `Saved/DualPistolQuickCombat20260920/diagnosis-summary.json`。

## 视频参考 V3（保留作者源与旧资产）

依据用户提供的 [Bilibili 视频](https://www.bilibili.com/video/BV19hUoBMEdX/) 制作左右手轮换横击与翻枪回握，详见 [V3 作者说明](../../SourceAssets/DualPistolQuickCombat20260920/VideoRefV3/README.md)。本版采用 0.80 秒动作、0.18 秒单次接触，主手横击后翻枪回握，副手压低避让并先恢复持枪。镜头改为轻微横向随动，命中探针采样本次实际出手侧的指根位置。

四份可编辑 Blend 与十二条 FBX 位于 `SourceAssets/DualPistolQuickCombat20260920/VideoRefV3`，运行资源位于独立的 `/Game/Weapons/DualPistolQuickCombat20260920/VideoRefV3`。旧 V1／V2 作者源与 V2 运行资源保留。本版为基于画面观察的三维适配，未提取或导入原视频游戏资产。未测试，由用户试用。

十二条动画已导入保存，回执为 `VideoRefV3/import.json`。2026-09-20 19:21:25，Live Coding 完成 `FPSQuickCombatComponent.cpp` 与 `PistolDualWieldComponent.cpp` 的必要编译，构建输出 `Result: Succeeded`，编辑器输出 `Live coding succeeded`。当前编辑器已应用函数补丁；未执行基础 Editor DLL 的常规构建，下一次常规构建需包含这些源码。导入与编译输出位于 `Saved/DualPistolQuickCombat20260920/import-video-v3.txt` 和 `compile-video-v3.txt`。未启动 PIE 或进行动作效果验收。

## 上版调整：FlowV2

用户反馈首版僵硬后，已制作并重导入 [FlowV2](../../trash/dual-melee-overhead-retired-20260920/SourceAssets/DualPistolQuickCombat20260920/FlowV2/README.md) 的六条动画，保留原有运行路径与 0.55 秒／0.26 秒业务时序。

- 右肘先带起，枪沿连续弧线前下砸；取消顶点的整组停顿，接触后持续带出并提前收回。
- 左枪稍晚收回，接触后有小幅反摆，整段持续随动。
- 两手作者源错开归位：右手约 0.485 秒，左手 0.55 秒，再沿用现有 idle 交接。
- 改用关键帧之间速度连续、限制过冲的三次 Hermite 插值，保留各手固定握点与机械状态。

四份可编辑 Blend、六条 FBX 与本版参数位于 `SourceAssets/DualPistolQuickCombat20260920/FlowV2`；首版作者源保留。此次只修改动作源及导入脚本，没有改动 C++，无需重新编译。

首次保存被正在运行的游戏阻塞；随后从第一条已导入动画的保存步骤继续，其余五条完成导入保存。回执为 `FlowV2/import.json`，桥输出为 `Saved/DualPistolQuickCombat20260920/import-flow-v2-resume.txt`。未启动游戏测试、截图、渲染或验收，手感由用户试用。

## 首版接入记录

双持装备时按 F／快速栏的快速进战，现在进入右手握把砸击与左手持枪避让分支。支持双 M1911、双 DW715，以及两种左右混搭；M1911 每手按弹药状态选择正常／空仓动作。

动作总长 0.55 秒，0.26 秒进行一次右手命中结算，继续使用现有快速进战的伤害、范围、击退、眩晕、冷却和修炼。两只手共用时钟，左手不额外造成伤害。没有更改技能数值、存档字段或弹药结算。

作者管线：[动作源与制作说明](../../SourceAssets/DualPistolQuickCombat20260920/README.md)。本机包含四份可编辑 Blend 与六条 FBX，六条动画已通过打开的 UE 编辑器导入保存到 `/Game/Weapons/DualPistolQuickCombat20260920`。

运行接线涉及：

- `FPSGAMECharacter.cpp`：双持入口分流；单持与步枪原分支保留。
- `Weapons/PistolDualWieldComponent.*`：加载每手动作、同步播放与归位、两手输入占用、左枪保持可见、按右手实际视模取接触探针。
- `Skills/FPSQuickCombatComponent.*`：DualPistol 风格和共用技能时钟，保留一击一结算、冷却与修炼语义。

本轮默认不测试：没有启动 PIE、运行自测／回归、截图或验收渲染。资产保存与必要编译不代表动作观感已获认可，实机效果由用户试用。

## 编译与生效范围

2026-09-20 14:52:44，现有编辑器中的 `LiveCoding.CompileSync` 返回成功，编辑器日志记录 `Live coding succeeded`，UBT 记录 `Result: Succeeded`。代码补丁已应用到当前编辑器。本轮没有关闭编辑器执行常规基础 DLL 构建，后续常规构建仍需包含这些源码。

首次构建被 `UI/M4GunsmithLayout.cpp` 的六处未限定 `Text` 阻塞：`GunsmithUI::Text` 颜色与 `ColdSteelInventory::Text` 函数发生名称冲突。该文件修改前无未提交变更；仅将这六处颜色名称限定为 `GunsmithUI::Text` 后重新编译成功，界面布局与行为未改动。

构建记录：`Saved/DualPistolQuickCombat20260920/compile-bridge-2.txt`、`livecoding-build-success-20260920.log`；首次失败留档为 `livecoding-build-20260920.log`。资产导入回执：`SourceAssets/DualPistolQuickCombat20260920/import.json`。

当前编辑器中重新进入游戏可创建带新动作资源的双持实例；本任务未操作或测试游戏实例。
