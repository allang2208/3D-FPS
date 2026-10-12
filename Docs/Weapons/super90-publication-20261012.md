# Super90：源码发布与废案整理（2026-10-12）

本次按用户要求整理本对话的 Super90 开发线、沉淀 SKILL 并发布至 `https://github.com/allang2208/3D-FPS.git`。执行 `WORKFLOW.md` 的归档与发布规则；共享文件只提交本线内容，其他任务的工作区改动保留。

## 当前恢复入口

| 部分 | 最新入口与边界 |
| --- | --- |
| 快速装填姿态 | R24 机械后止补丁，保留 R23 腕臂／表面、R21 枪手响应与抓握、R20 臂根，以及 R14–R17 完整推进链；[R24 记录](super90-speedloader-r24-bolt-rear-stop-20261010.md) |
| 推进播放节奏 | [R25](super90-speedloader-r25-align-drive-20261012.md)：前 30% 行程慢速对准、后 70% 加速，枪手、装填器、相机、音效与一次补满共用源时钟；新节奏待用户体验 |
| 镜头与原声 | R22 参考背景＋ASH-12／PKM 接触强度；R15/R16 七段快速装填原声，普通声音独立；源音视频不发布 |
| 普通空仓 | 后续按用户指定改为 [Cransh 原生释放段](super90-cransh-release-20261012.md)：保留当前逐发装填及握把，恢复 424 帧源动作，尾段短促释放枪机；此更新晚于本页原发布，构建状态见新记录 |
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

## 2026-10-13 后续收尾发布

本次发布包含此前未提交的 SUPER90 局部表面、前握把与通用后握把接入、按压释放、臂根修正、三种弹药及其模型配方、轮盘图标修复、四段圆环和六项网络收尾。共享文件按差异拆分，未带入并行开发中的其他武器双战术挂件、热成像、扳机、移动、营火、UI 资源条或技能变更；本机这些改动保留。

| 当前部分 | 恢复入口 |
| --- | --- |
| 手臂表面 | `Super90JointSurface20261012`；依赖 `Super90SkinClean20261011` shader；保留原生绑定和权重。两次已否定的整臂／权重方案不可重装 |
| 普通空仓 | `Super90CranshRelease20261012`，前 360 帧逐发装填，闭栓事件在源帧 374；替代 NativeEmptyBolt/PacingR2 尾段 |
| 快速装填收尾 | `Super90LoaderRelease20261012` 的按压释放，`Super90LoaderArmRoot20261012` 修正推进至回握；保留 R25 推进时钟及 R14–R24 有效前段依赖 |
| 前握把／挂载弹 | `Super90GripRepair20261012`、`Super90MountedShellColor20261012`；材质按导入槽身份匹配，避免错用旧显示名 |
| 后握把／下挂件 | `Super90RearGrips20261012`、`Super90TacticalBottom20261012`；本枪一个下挂槽，既有副槽存档迁入主槽；安装失败恢复原厂后握把 |
| 弹药／图标 | `Ammo12Gauge20261012`；鹿弹 8 颗，箭型 8 颗且额外穿一目标，独头 1 颗／整发伤害 75%／双倍射程／10% 物理护甲穿透。模型、PNG 与 UE 包本机保留 |
| 网络和散布 | [六项收尾](super90-network-closeout-20261013.json)；服务端枪弹／装填与弹药回执，远端道具／枪口／声音／灯光，圆环含腰射偏移与弹丸锥角 |

新增归档 **339 份、1,032,929,126 字节（约 985.08 MiB）**，位于 `trash/super90-retired-20261013/`，见 [逐文件恢复清单](super90-retired-20261013.json)。包含已否定的 MPFB 几何产物、相关退役工具及完整 `Super90BareRefine20261010` 目录。全部移动前后大小和 SHA256 一致。当前表面配方仍读取 MPFB 目录的 `inputs.json` 与 `materials_saved.json`；这些文件、原始 Before/Snapshots/Rollback、许可参考 External 和来源回执保留原位。没有删除或移动当前正式 Content 包。

早前完整本机工作区 `FPSGAMEEditor Win64 Development` 构建成功，日志为 `Saved/Super90Closeout20261013/Editor.stdout.log` 和 `Editor.final.stdout.log`。此次只执行用户要求的归档与发布检查，不重新构建或运行 UE；拆分后的公开源码未单独编译，双端联机、延迟/丢包及最新视觉体验仍待用户。历史表面和轮盘专项检查只代表各自当时的结果。

公开新增内容为原创 C++、四份数据目录增量、必要 cook/模块依赖、作者脚本、说明、归档元数据及技能。原始模型许可与署名沿用 [来源记录](super90-20261006.md)，模型／动画／纹理／声音／视频、完整骨骼与网格采样、编辑器回执、构建结果及归档实体不公开；仅克隆仓库不能恢复完整游戏资产。先恢复许可允许的本机 Content 和输入，再按上表合并当前补丁，不串行重跑全部历史导入器。

可复用经验同步到枪械技能的 [霰弹枪权威与表现](../../skills/ue5-weapon-workflow/references/shotgun-authority-and-presentation.md)和手臂技能 [局部修订](../../skills/ue5-fps-arms-animation/references/super90-shared-clock.md)。本机 SKILL 入口的其他迁移不随本次发布。
