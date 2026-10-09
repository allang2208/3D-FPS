# Super90：整理发布与本机恢复（2026-10-09）

本次整理本对话的 Super90 源码、目录、制作配方和经验，不继续动画开发。用户已授权推送 `https://github.com/allang2208/3D-FPS.git` 的 main；执行本仓库 `WORKFLOW.md` 第 8 节的发布检查。其他任务的未提交改动保留在工作区，共享文件按 Super90 相关内容拆分提交。

## 当前状态

| 项目 | 当前状态与入口 |
| --- | --- |
| 原生枪体、V7 手臂、硬壳手套与 ST6 衣袖 | 基础导入与派生已落盘；`SourceAssets/BenelliM4Super9020261006/`，来源及最初交付见 [原始记录](super90-20261006.md) |
| 表面 | 当前为 WS1 分区材质＋修正后的 source FBX/PNG 映射；`Super90Mapping20261007`、`Super90WS1Surface20261007`、`Super90SurfaceAlignment20261007`。不能以初版材质或 GLB 的旧 UV 变换覆盖 |
| 普通换弹／音效 | 持续逐发装填、默认提速 30%，保留打断与空仓闭锁；当前声音来自用户 E 盘 gamedev Super90 输入。见 [连续换弹](super90-continuous-reload-20261007.md)、[声音](super90-gamedev-audio-20261007.md) |
| 配件与机械 | 通用瞄具、贴轨安装、前握把及专用 Profile；挂载红色备弹保留，独立装填弹只在使用阶段显示。当前作者分别在 `Super90Optics20261007`、`Super90DirectOptics20261008`、`Super90Foregrips20261007`、`Super90ShellMechanics20261008` |
| 战术冲刺 | 当前 `Super90TacticalSprint20261007/author_sprint.py`；原生跑步与冲刺 entry/loop/return 由所有权仲裁。肩臂修订仍不视为用户认可案例 |
| 独立待机 | `Super90IdleMatchWalk20261008` 从各自 walk 提取完整左链到 idle；一个基础序列和四份 Profile 已保存，待用户体验 |
| 快速近战 | 当前 `Super90QuickMelee20261008/LeftArmR5`。保持双手握点、手指、枪体左甩和右臂，重解七条左臂轨道。五份生产资产和五条可编辑时间线已保存；R4 被否定，R5 尚未获用户认可。详见 [近战记录](super90-quick-melee-20261008.md) |
| 快速装填 | **用户要求暂停，尚不合格**。R9 保存的 21 项资产和后续未导入源码不是同一版本。保留现场与 [待办](super90-speedloader-paused-20261008.md)，本次不重跑作者、导出或导入 |

## 归档与保留依赖

511 份旧稿、历史回滚副本、缓存及 Blender 自动备份移到本机 `trash/super90-retired-20261009/`，合计约 1124.15 MiB；移动后大小和 SHA256 与移动前一致。公开 [逐文件清单](super90-retired-20261009.json) 记录原路径、新路径、大小、哈希、原因和替代入口；trash 内的实际内容不发布。

R1、DirectionR2、LeftSwingR3、LeftArmR4 的完整近战旧稿已归档。R5 需要的 `inputs.json`、`author_space.json` 和 `camera_basis.json` 已独立保存在 R5，不再跨读被归档目录。其 `animation_patch.json`、`installed_source.json`、`v7_skin_basis.json` 和可编辑 Blend 保留本机。

下面的历史源仍被作者脚本读取，保留原位，不按日期判废：

- `Super90ContactR8_20261008/Before/Source/`：失败证据还原读取旧作者源。
- `Super90LoaderFramingR5_20261008/Before/Source/`：构图作者输入。
- `Super90LoaderRebuild20261007/Before/Source/`：抓握源读取。
- `Super90LoaderRepair20261008/Before/Source/`：坐标与接触布局求解。
- `Super90SprintArmRepair20261007/Before/author_sprint.py`：旧肩臂对照。

快速装填其他日期目录仍组成暂停现场的作者／诊断依赖链。归档的 `Before` 资产可从清单定位；不自动恢复或覆盖当前生产资产。原生母版、V7 母版、第三方源和已保存运行资产保留。

## 恢复顺序与发布边界

1. 从许可完整的本机备份恢复 `Content/Weapons/Super90/`、`Content/Characters/ModularOutfit20260924/Super90Source20261006/`、图标、原始来源包、完整 JSON 姿态和可编辑 Blend。
2. 准备 V7 裸手母版、已有通用瞄具／前握把与 WS1 材质依赖。基础原生制作源为 `Super90_Gameplay_Editable.blend`；不要把原始导入器当成当前全量恢复入口。
3. 表面、机械、配件和冲刺按上表采用入口恢复；制作过程中读取的是各自本地元数据。旧 `apply_runtime.py`／早期一次性替换脚本是历史接入配方，当前 C++／目录已直接发布，不再逐个重放字符串替换。
4. 后续若重新要求制作，先恢复独立 idle，再使用当前 R5 近战输入。R5 `save_assets.py` 只写七条左臂轨道及对应 Profile 的近战差量；不覆盖其他动作引用。近战命中枪托点在 `QuickCombatRifleMotion.h`。
5. 快速装填恢复制作需用户重新提出。暂停源不能用于覆盖当前 idle／近战，也不以 R9 的局部相交报告宣称完整动作合格。

公开范围为原创 C++、配置、目录、作者脚本、研究文字、归档元数据和 SKILL 镜像。第三方模型／动画、音频、贴图、参考视频、UE 包、完整采样、下载响应、导入回执和构建产物留在本机；仅克隆 Git 不构成可运行的完整资产安装。

模型／动作来源为 Cransh 的 [FPS Benelli M4 Animations](https://sketchfab.com/3d-models/fps-benelli-m4-animations-225a62190f6043ca975eaa2798ab7e2c)，来源记录为 CC BY 4.0，原发布另署 haoliu95 枪体和 teenjust500 手套。许可证与改动说明保留于 [来源记录](super90-20261006.md)。用户 gamedev 声音、V7 与共享配件按各自来源链恢复，未宣称统一可再分发。AAnim RTM／视频仅作动作研究，不发布原文件或完整变形矩阵，研究结论不等于动作移植完成。

共享文件中其他工作的热成像、自动扳机、双战术挂件、角色呈现及数值调整不在此次发布范围。Super90 的基础配件目录以本对话的瞄具、前握把和暂停装填器为限；本地其他扩展保留。

本次进行了用户要求的归档与 Git 发布检查，未启动 UE、游戏、PIE、渲染、回归或独立构建。历史构建记录只代表当时完整工作区；本次拆分后的公共源码快照未独立编译，不把资产保存成功或源码发布称为动作验收。
