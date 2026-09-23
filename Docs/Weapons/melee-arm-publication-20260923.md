# 近战手臂修复：源码发布与本机恢复

本批范围为肩部避让 V1、突进与相机缓存顺序修正、第三段突刺双肘支持。包含作者脚本、保留的离线诊断方法、对应文档和手臂技能更新。共享源码按代码段暂存，只发布相机顺序修正；其他尚未归入本批的换弹、施法、跳跃和战斗改动继续保留在工作区。

## 当前正式结果

- 标准柄与长柄的 `Overhead`、`SprintOverhead` 保留 `MeleeArmOpening20260923` 的肩部避让。
- 两套 `Thrust` 在该 V1 基础上叠加 `ThrustElbowRepair20260923`，于 2026-09-23 18:34 完成压缩、正式包保存及完整 FBX 导出，保持 1.25 秒时长。
- 剑组件全状态固定 `TG_PostPhysics`，显式依赖角色及移动组件；旋风退出不再恢复旧更新组。该运行修改已于 18:06 完成正式 Editor 构建。
- 只做过用户所要求问题的离线姿态/实际蒙皮对比，未完成本次游戏视觉验收。发布整理没有启动 UE、游戏或新增测试。

## 本机恢复内容

Git 不包含完整动画或授权手模；需要从合法本机备份保留以下内容：

1. 当前 Manny 手臂、骨架、材质与武器依赖：`Content/Weapons/AzureRunesword20260913`、`Content/Weapons/FrostCrystalSword20260915/Modules20260915`、`Grips20260919/LongGripAnimations`，以及高地双手剑自身的模块资产。
2. `SourceAssets/MeleeArmOpening20260923`：两套真实手模 FBX、rest/parents/密集源姿态、geometry、三个 V1 补丁、开口权重输入、完整可编辑 Blend、导出 FBX、`Before/` 与保存回执。该目录仍是有效上游，不能按旧版本删除。
3. `SourceAssets/ThrustElbowRepair20260923`：两套当前 Thrust 补丁、完整可编辑 Blend、FBX、`Before/` 备份、冻结 `diagnosis.json`、实际保存回执和离线评审图；其蒙皮站位输入来自 `RuneSwordPickaxeOverhead20260920/ImpactV2/authoring.json`。
4. `Saved/MeleeArmOpeningReview20260923` 保留实际加载状态、压缩采样、分析、`GeometryCapture` 与 `CameraLagGeometry`。它们是诊断材料，不是运行时资产或游戏验收记录。

重建顺序是先恢复合法输入，再制作/安装肩部 V1，最后制作/安装肘部支持；恢复当前备份时可直接恢复已保存的正式资产。不要在当前肘部修正上重跑旧安装脚本，哈希拒绝意味着源版本不匹配，不应绕过。

## 废案归档

失败或不可靠的 UE 取帧工具、对应图像/日志/中间输出，以及已结束的一次性编辑器控制脚本，移至 `trash/melee-arm-obsolete-20260923/`。精确文件数、原路径、字节数、SHA-256、原因和保留替代物见 [归档清单](melee-arm-archive-20260923.json)。移动前验证路径，移动后逐文件核对散列；不删除资产或清理全仓库。

临时 C++ `RuneSwordArmOpeningCapture.cpp` 与 `RuneSwordAuditCommandlet` 的 `ArmOpeningCapture` 路由一同退役。这只是移除未发布诊断入口，未改正式动作行为；本次未为清理重新构建 DLL。后续常规构建将不再包含该临时入口。

`trash`、Content 二进制、Blend/FBX、密集姿态/几何、截图和日志不公开提交。仅增加相关目录的精确忽略规则，保留其他任务的暂存区与未提交文件。推送只使用普通 `HEAD:main`，目标 `https://github.com/allang2208/3D-FPS.git`，旧 Godot 归档标签保持。
