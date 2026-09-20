# 双持手枪快速近战：当前源与归档

当前候选为 [SpinRecoveryV5](SpinRecoveryV5/README.md)：0.80 秒、0.18 秒单次接触、左右轮换出手。每手按装配选择 compact／fitted／long，均保留整圈转枪。已导入 36 条动画，实机与配件组合观感仍由用户确认。

[VideoRefV3](VideoRefV3/README.md) 的动作函数、手工 motion、源模型与对照动画继续保留；V5 作者脚本仍使用其纯函数。根目录 `import_assets.py` 是 V3 包装器仍会调用的共享导入器，不是废案；当前 V5 使用自己的导入器。

首版 V1、FlowV2 以及取消改造枪转枪的 AttachmentClearanceV4 已归档至 `trash/dual-melee-overhead-retired-20260920/SourceAssets/DualPistolQuickCombat20260920/` 对应路径。旧无引用运行包也已归档。原制作记录在归档内；不要重跑旧入口覆盖当前版本。

DW715 枪身／弹巢形变仍未定位，见 [定向诊断](SpinRecoveryV5/RigidFix/README.md)。`RigidFix` 目录名不代表修复已完成。

作者依赖、许可、运行路径、源恢复顺序与归档清单见 [发布说明](../../Docs/Weapons/dual-melee-overhead-publication-20260920.md)。本次整理未启动游戏测试或验收渲染。
