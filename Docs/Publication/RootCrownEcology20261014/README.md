# 根冠、园艺师与医疗／生态区域发布

2026-10-14，用户认可园艺师 V02 外形后，要求归档废案、沉淀技能并推送源码。当前主工程和 Git 根为 `D:/FPS3D/FPSGAME`，发布目标为 `https://github.com/allang2208/3D-FPS.git` 的 `main`。

## 本机实现与公开范围

本机已有根冠 M-01 的冠盘补骨/权重、移动转向、快速冠缘铡击及白弧、上扇叶骨针、触发地雷、5 秒致残、受击/眩晕/击飞/死亡、表面命中及服务器命中复核。园艺师复用研究员骨架与动作，使用用户认可的 V02 实体分层服装。区域规则如下：

| 区域 | 配置与目标 |
| --- | --- |
| 医疗 | 每间 12～15 名基础职员，单波；医生办公区随机两个不同房间各一只螳螂；第二间病房 5 只螳螂；第三间 2 只悬钟和首领缚群，阶梯座位角落有待接战利品机制的宝箱 |
| 生态第一间 | 6～8 名园艺师，单波 |
| 生态第二间 | 6～8 名园艺师和 4 只螺柱，单波 |
| 生态第三间 | 2 只螺柱和根冠 M-01 |
| 两区域通行 | 入场后封锁来路及出口，允许外部队友进入；击杀本区域首领后一起解锁，不要求清空普通怪；每位玩家显示自己所在区域目标 |

分流大厅工作台/其他设备避让楼梯与通道、医疗室内门、医疗宝箱等场景配方已经在先前地牢发布中提交；本轮保留其现行配方，并归档该次修改前的备份。相关入口为 `SourceAssets/TransitEquipmentClearance20261013`、`TransitMaintenancePlacement20261013`、`MedicalEncounter20261013`、`MedicalBoundaryLock20261013`、`MedicalOfficeMantis20261013` 和 `MedicalTheatreChest20261013`。

本次直接发布根冠专属 C++、15 个共享源码/配置文件中的本次修改块、园艺师/根冠作者与导入工具、说明及技能参考。共享文件以 HEAD 为基底选择性暂存，工作区的其他怪物、货运/发电、武器与性能改动保留原样。

[regional-integration.patch](regional-integration.patch) 保存 14 个相互依赖的区域/共享联机接入目标，包括两个生态模块、医疗/生态声明与生成分派、区域目标、门禁、Root Crown 远端命中复核和合同检查。它依赖本机尚未完整公开的共享地牢、命中报告、任务追踪与生成准备框架，**整体不能直接应用到公开 HEAD，也不要对当前已接入的本机工程再次应用**。本轮不把这些其他任务的实现整文件夹带提交。

[integration-manifest.json](integration-manifest.json) 逐文件记录 UTF-8/LF 前置与结果散列。多数前置内容是从本机整合源码中移除本次增量得到的上下文，并非一个独立历史提交；两个 ThemeEncounter 文件以所记 Git 基线为前置，明确排除后来其他区域扩展。恢复时先合并所需共享 API，再核对散列，匹配时才能用 `git apply --unidiff-zero`；不匹配则按函数合并并保留其他区域。完整本机前置/结果快照留在 `Saved/PublicationRootEcology20261014/integration/`。公开源码不代表干净检出即可构建完整游戏。

## 根冠当前恢复链

所有路径以 `SourceAssets/RootCrown20261014` 为根；作者/导入在 `Tools/RootCrown`。先恢复用户原 `Source/RootCrown_UserRig.glb`（原文件 Meshy_AI_Character_output (1).glb）和许可依赖，再执行需要的制作阶段。不要批量运行历史脚本：部分早期脚本含当时明确要求的检查/预览步骤，当前需按用户授权选择。

1. `read_source.py` / `author_rig.py` 保留原身体绑定、补充冠盘，恢复 `Authored/RootCrown_Source.blend`、`RootCrown_CrownRig.blend` 与 `Exports/SK_RootCrown.fbx`；`install.py` 恢复 RigV01 和原蓝图入口。
2. `author_locomotion.py` / `install_locomotion.py` 恢复 MotionV01。`Authored/RootCrown_LocomotionV01.blend` 是后续动作的作者输入。
3. `author_slash.py --double-downstroke` 生成 SlashV02；`apply_slash_v2.py` 接入快速铡击并保留修复后的肉质材质。旧 V01 的 `install_slash.py`、`finish_slash.ps1`、慢速 FBX/接触数据和音频已移入 trash；如需历史恢复按归档清单取回，不能覆盖当前蓝图。接触 JSON 与对应动作版本必须配套。
4. `author_needles.py` 基础阶段生成 NeedlesV01 弹体及声音；追加 `--upper-fan` 生成 NeedlesV02 上扇叶动作/出口。先 `install_needles.py` 恢复弹体/声音，再 `install_upper_fan_arc.py` 切换当前动作、出口与白色攻击弧。基础导入暂时使用旧动作，所以其 V01 导出仍作为重建中间输入保留。
5. `author_roots.py` / `install_roots.py` 恢复 RootsV01 根结网格和种植动作；`author_mine_audio.py` / `install_mines.py` 将第三招接成当前地雷。`install_mines.py` 复用 `install_roots.py` 的材质函数；RootsV01 不能按旧招式名称清理。
6. `author_reactions.py` / `install_reactions.py` 恢复 ReactionsV01。`prepare_soft_death.py` → `author_soft_death.py` → `install_soft_death.py` 恢复 SoftDeathV01，依赖当前工程的 M14 通用软体工具和本机表面/绑定输入。`install_combat.py` 恢复专用命中 PhysicsAsset。

最终组合：RigV01、MotionV01、SlashV02、NeedlesV02 动作 + NeedlesV01 弹体/声音、RootsV01、MinesV01、ReactionsV01、SoftDeathV01、CombatV01。`build.ps1` / `import.ps1` 使用共享批次互斥；遇到已运行编辑器保留现场，不自动关闭或再开一个编辑器。原生动画 NodeData 崩溃修复见 [记录](../../Monsters/RootCrownNativeAnimCrashFix20261014.txt)。

## 园艺师当前恢复链

蓝图 `/Game/Monsters/EcologyGardener/BP_EcologyGardener` 保持稳定，当前网格为 `/Game/Monsters/EcologyGardener/V02/SK_EcologyGardener_V02`。保留研究员 V05 源、161 骨段、231 个 FR 修形和 8 个共享动作，角色显示身份与动画家族标签分别处理。

`Tools/EcologyGardener/author_v02.py` 仍读取 `SourceAssets/EcologyGardener20261014/V01/Authoring/EcologyGardener_V01.blend`；V01 外观被否定，但这个文件仍是重建输入。`author.py` 是生成该输入的旧配方，还依赖本机 `Tools/CargoStationStaff/author_variants.py` 的 material 函数，此其他任务工具尚未纳入本次公开范围。完整恢复须取得该依赖或恢复保留的 V01 作者文件，不能仅下载本次仓库就假定能够重建。

随后 `author_v02.py` 生成连续围裙、肩带、实体口袋、扣件、弧长 UV、权重与 FR 修形；`import_v02.ps1` / `import_v02.py` 实际保存 V02 网格、18 张纹理、6 个材质及原蓝图共 26 个资产。详细参数和历史导入记录见 [服装 V02](../../Monsters/EcologyGardenerClothingV02_20261014.md)。

## 归档与资源边界

[archive-manifest.json](archive-manifest.json) 记录 **393** 份文件的原路径、`trash/root-crown-ecology-retired-20261014/` 目标、字节数、SHA-256、原因和替代物；移动前后逐份核对。包括大厅/医疗修改前源码及地图快照、Blender 自动备份、被 V02 替代的两个根冠动作作者输出、软体导入前的网格备份，以及慢速 SlashV01 的旧导入器/动作/音频。

保留当前源模型、绑定、服装 V01 作者输入、混合版本动作/网格/声音、实际使用的导入脚本和历史证据。没有移动 `Content/` 内可能被编辑器加载或被恢复链引用的资源包；未核实引用的旧包不凭版本号判作废案。原始失败日志也保留用于排错，不当作废案删除。

公开 Git 只包含原创源码、工具、文档及归档元数据；用户提供的模型、Meshy/Epic/Fab/动作依赖、UE 资源包、贴图、音频、密集姿态/蒙皮/软体 JSON 和构建产物不上传。`.gitignore` 为两个制作目录明确限制发布范围。完整工程仍按 [AssetSetup](../../AssetSetup.md) 恢复授权资产。

## 技能与验证边界

个人技能维护源和仓库参考已同步：

- [无面职员服装](../../../skills/ue5-monster-workflow/references/faceless-staff-clothing.md)：连续实体裁片、独立材质、曲面弧长 UV、固定映射继承全部 FR 修形、材质图编译顺序。
- [根冠原生动画](../../../skills/ue5-monster-workflow/references/root-crown-native-animation.md)：NodeData 限制、持久姿势过渡、攻击时间合同、地雷状态施加与混合恢复链。
- [区域首领联机](../../../skills/ue5-save-load-replication/references/regional-boss-objectives.md)：共享 RunId/Revision、区域独立标志、每位玩家视图、只进不出及 soft class cook 依赖。

历史本机记录：园艺师 V01 接入的 Editor/Game 构建成功；V02 于 21:53 后台导入退出 0、26 个资产保存，用户随后认可外形。用户要求的上一轮排查完成 61 项资产/CDO 检查和 30 项 TaskTrackingContract 检查，并补齐园艺师、螺柱、根冠的 cook 目录。详见 [生态接入排查](../../Monsters/EcologyIntegrationAudit20261014.md)。

本次只检查归档、提交内容、补丁恢复、大小、敏感信息与远端发布，不重新运行 UE、游戏或渲染。历史整合工程构建/合同结果不能替代公开切片编译，也不等于双玩家实测、迟到入场、门口挤压、延迟/丢包或完整打包通过。
