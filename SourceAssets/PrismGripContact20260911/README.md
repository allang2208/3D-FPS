# M4 棱镜阻手器：水平包握

当前可编辑源：`prism/M4_Prism_Family_Editable.blend`。九组对应 FBX 位于同目录。游戏预览：`prism/M4_Prism_Horizontal_Gameplay.mp4`，由实际独立游戏进程截图序列生成，无声。

正式接触配置为 `prism/fit_final.json`、`contact_overrides.json`、`profile.json`、`release_profile.json`。`prism/build_animation.py` 调用 `SourceAssets/VerticalGripClass20260911/build_family.py`，继续复用垂直握把类生成器。废弃拟合脚本、旧报告和自动备份已移到 `trash/prism-horizontal-cleanup-20260911/`。归档清单位于 `Docs/Weapons/prism-horizontal-archive-20260911.json`。不要从废案覆盖最终配置。

运行目录 `/Game/Weapons/M4PrismHorizontalGrip`，由 `Source/FPSGAME/Weapons/VerticalGripAnimationFamily.h` 的 Prism 分支选择；Vertical 分支保持 Raised/Vertical。原生构建后缀 2026095561，实际游戏运行 prism-horizontal-v1。

本次校正整掌与四指屈伸平面，按安装座截面校准握点，收拢下方指列并消除指间挤压。腕部轴线弯折保持 21.31 度，骨长、rest、scale、手指局部平移与原换弹接触时序均按源约束验证。

验收：302 项游戏检查、九动画导入读回通过；446 个手指/配件采样无交叉；闭合十组指对和普通换弹松手/回握的 82 个采样无指间交叉。完整数据见 `acceptance.json`、`pose_metrics.json`、`self_contact.json`、`self_transitions.json`、`prism/source_validation.json`、`prism/import_report.json`。实际检查掌侧、手背、正面、腕臂及回握画面。

导入 commandlet 仍报告工程已有的 GameFeatureData 配置与 HTTP 端口占用错误；九项导入与读回断言通过，独立游戏进程验收通过。未验证打包构建。

## Git 发布与本机恢复

本次公开作者/验证脚本、接触配置说明、汇总验收与技能，不公开完整姿态矩阵、逐采样松手数据或模型/动画二进制。恢复清单见 `Docs/Weapons/prism-horizontal-local-assets-20260911.json`。完整本机最终配置继续保留原位置。

`build_animation.py` 依赖公开的 `SourceAssets/VerticalGripClass20260911/build_family.py` 及本机完整源。恢复所需九动作母版为 M4ContactImpact20260910、M4WrapGrip20260910、M4TacticalToss20260910、M4SlapImpact20260910、M4DrumContact20260910；对照检查和松手重建还需要 VerticalGripRaised20260911/prism 的已许可 Blend、fit_final.json 与 release_profile.json。这些输入是活跃依赖，不是废案。

当前完整宿主的角色/枪械模块混有 AKM 等并行实现，本次不将其整包发布。Git 中的作者工作流与本机已接入运行版本应区分：单独克隆本次提交不足以恢复完整枪匠配件系统。运行接入点为 M4HandstopVisual.cpp / M4VerticalForegrip.cpp 中的 VerticalGripAnimationFamily::M4ClipPath，以及 FPSGAMECharacter 与 ForegripAudit；本机验收对应前述完整宿主。
