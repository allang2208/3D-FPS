# Super90：源码发布与废案整理（2026-10-12）

本次按用户要求整理本对话的 Super90 开发线、沉淀 SKILL 并发布至 `https://github.com/allang2208/3D-FPS.git`。执行 `WORKFLOW.md` 的归档与发布规则；共享文件只提交本线内容，其他任务的工作区改动保留。

## 当前恢复入口

| 部分 | 最新入口与边界 |
| --- | --- |
| 快速装填姿态 | R24 机械后止补丁，保留 R23 腕臂／表面、R21 枪手响应与抓握、R20 臂根，以及 R14–R17 完整推进链；[R24 记录](super90-speedloader-r24-bolt-rear-stop-20261010.md) |
| 推进播放节奏 | [R25](super90-speedloader-r25-align-drive-20261012.md)：前 30% 行程慢速对准、后 70% 加速，枪手、装填器、相机、音效与一次补满共用源时钟；新节奏待用户体验 |
| 镜头与原声 | R22 参考背景＋ASH-12／PKM 接触强度；R15/R16 七段快速装填原声，普通声音独立；源音视频不发布 |
| 普通空仓 | [NativeEmptyBolt](super90-native-empty-grasped-bolt-20261010.md) 的 7.4 秒源姿态＋[PacingR2](super90-native-empty-pacing-r2-20261010.md) 分段时钟，保留逐发装填，尾段抓握拉柄 |
| 快速近战 | [RightArmR9](super90-quick-melee-right-arm-r9-20261010.md)，保留 R7 身体侧竖直收臂与枪托前送，辅助骨按站位分配旋前；R23 左肘／R9 右肘表面补丁均保留 |
| 普通移动 | [LocomotionIdleGrip](super90-locomotion-idle-right-grip-20261010.md)，右链按各握把认可的 idle 统一，保留枪身起伏 |
| 射击／弹药 | Super90 基础及最低射击间隔均为 60 ms；快速装填压实后一次补齐可装弹药，普通装填仍逐发结算 |
| 整枪装备栏图 | [InventoryIcon](super90-inventory-icon-20261009.md)；原图标制作入口转用现有 UE 目录图管线。装填器配件图标仍是独立待办 |

本机动画、四份握把配置、可编辑 Blend 及声音已按各版本记录保存。R25 Editor／Game 常规构建完成，已包含普通空仓 R2；历史 Live Coding 限制不代表最新基础 DLL 状态。本次仅做归档与发布检查，没有重跑制作、导入、构建、游戏、渲染或验收；拆分后的公开源码快照没有另行独立编译。

保存配方依赖 `WeaponAnimationAuthoring::FinalizeAuthoredAnimation` 的帧率同步与压缩完成处理，此公共方法随本线一起提交；未夹带其他动画制作功能。

## 本次归档

598 份文件，963,323,661 字节（约 918.70 MiB），已移至本机 `trash/super90-retired-20261012/`。逐文件移动前后大小和 SHA256 一致，清单见 [归档元数据](super90-retired-20261012.json)。原文件可按清单恢复，无删除或覆盖当前资产。

- 被否定／撤回的 R10、R11、R13、R18 完整过程目录。
- RightArmR8 的 Iteration1–5，R23 的首版修复和已替代试验姿态。
- 本轮作者链的旧 Before 回滚副本、R21 错误导入路径备份，以及缓存／自动备份。

有效历史输入保留原位：R12、R14–R17、R19–R25 作者链；R21 `source_poses.json` 与 R16 `audio_provenance.json`；R5 校准、R8 `animation_patch.json` 与 `BeforeSupportRefinement`；R23 接触拟合／几何／表面和 R24 输入。更早的五处 Before 作者输入依赖继续按 [10 月 9 日整理记录](super90-publication-20261009.md) 保留。旧日期不能作为废案依据。

## 恢复与发布边界

先恢复具备许可的本机原生母版、V7 手臂、配件、材质、参考输入和当前 Content 包，再使用当前作者输入。不要重新执行历史全量导入器或字符串替换脚本覆盖最新配置。Profile 只合并目标条目；装填、普通空仓、近战和移动的最新补丁需要共同保留。R25 不重写姿态资产，恢复其运行时映射与生成头文件即可。

公开内容为本线 C++、必要配置变更、原创制作／导入脚本、文档、少量运行相机与时钟参数、归档元数据和 SKILL。完整骨骼姿态、模型／动画、Blend、UE 包、贴图、音频、参考视频、下载响应、构建产物、日志／回执与 trash 实体均留本机。仅克隆 Git 不能构成完整可运行资产安装。原始模型署名与许可沿用 [来源记录](super90-20261006.md)；用户视频和录音没有在本次获得公开再分发许可，因此不上传媒体。

经验汇入手臂动画 SKILL 的 [Super90 分段时钟与腕臂修订](../../skills/ue5-fps-arms-animation/references/super90-shared-clock.md)以及既有近战／枪械集成参考。个人维护源与工程参考内容同步，其他任务正在整理的 SKILL 入口迁移不混入本次提交。
