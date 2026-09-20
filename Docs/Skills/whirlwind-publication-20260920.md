# 大旋风整理与源码发布（2026-09-20）

范围为本任务的大旋风迁移、V4蓄势、镜头同步、前景表现、ALT修复和最后追加的移动/跳跃限制。遵循根目录 `WORKFLOW.md` 第4、5、8节：保留并行修改，精确暂存，普通推送到 `https://github.com/allang2208/3D-FPS.git` 的 `main`。

## 正式保留

- 普通柄 `/Game/Weapons/AzureRunesword20260913/A_RuneSword_WhirlwindV4`；加长柄 `/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations/A_RuneSword_WhirlwindV4`。
- `SourceAssets/Whirlwind20260920/WindupV4` 的曲线、作者/导入脚本、Blend、两份FBX、加长柄逐帧关键帧、作者参数和保存回执。Manny握持源、ChargedErgoV43母版与共享双臂求解器继续保留；不把共享母版当作本次废案。求解器的其他并行改动不随本次提交，精确恢复优先使用保留的V4成品源。
- `/Game/Skills/Whirlwind20260920/M_WhirlwindFocus` 与 `ForegroundV3`。V2的HLSL/材质制作脚本和V3的前景材质制作脚本仍是有效依赖。
- 原创图标制作脚本 `make_icon.py` 与公共恢复入口；源图和运行PNG保留本机，由脚本重建。

## 归档

98个旧版本/临时文件，共537,571,594字节，移入本机 `trash/whirlwind-retired-20260920`。六份V1–V3动画包归档前通过UE包引用查询确认无引用且无未保存更改；V4运行加载路径保留。旧作者源、旧输出、临时构建/接入回执、schema及诊断输出随原相对路径归档，当前诊断结论README保留。

[逐文件清单](../AssetArchives/whirlwind-retired-20260920.json) 记录原路径、目标、替代物、大小与SHA-256；移动后逐文件读回散列一致。trash不进入公开Git。历史记录中的旧输出或回执原路径可按清单映射到归档位置。

## 公开边界与部分暂存

公开本次原创C++、配置、作者脚本、HLSL、必要参数与文档。Manny/Fab/授权武器资源、Blend/FBX/uasset、密集逐帧关键帧、截图/音频/视频及本机日志不公开，新增限定忽略规则防止逐帧JSON误入提交；只克隆Git不能得到完整可运行素材包。

共享角色、技能、UI与控制器文件按片段暂存。大旋风在发布快照中增加存档迁移版本12；工作区后续技能的版本13、闪电功能、怪物韧性、其他武器/UI/世界修改保持原状，不夹带发布。新大旋风文件中来自并行韧性工作的接口同样仅留在工作区，发布版本沿用已提交的战斗接口。

技能经验分别沉淀到 `ue5-skill-magic-workflow/references/whirlwind-melee.md` 与 `ue5-fps-arms-animation/references/spin-windup-continuity.md`，个人技能目录和工程镜像同步。

## 已有反馈与未完成接入

用户已确认镜头错位修复成功，并在V4蓄势优化后表示整体没问题；V4此前常规Editor构建日志为 `Saved/BuildEditor/build-20260920-183009.log`。

最后的移动/跳跃限制已写入源码，但本任务Live Coding返回 `CompileNotStarted / Live coding canceled`，常规构建退出被未保存的双持M1911快速近战动画阻断。没有丢弃该资产或强制退出编辑器；本次整理发布不宣称这部分已编译或实机生效。此次只执行用户要求的归档、仓库/暂存/许可检查与远端回读，没有运行游戏、回归、预览或截图。
