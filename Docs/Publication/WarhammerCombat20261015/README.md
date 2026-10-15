# 双手战锤动作、格挡与联机修复发布

2026-10-15，工程 `D:/FPS3D/FPSGAME`，目标 `allang2208/3D-FPS` 的 `main`。本轮按用户要求归档废案、更新技能并发布已完成工作；后续游戏测试由用户安排，没有重新启动 UE、运行游戏或追加验收。

## 本机已完成内容

战锤类别已接入工具装备体系，包含普通三连击、重击/冲刺砸地、上挑、旋风、锤头前捅快速近战及五段斜横撑挡。普通三连击第三段 1.25 倍、前方群体判定；冲刺使用冲刺技能伤害并复用圆形冲击波；重击针对符合资格的普通/破韧怪物提供基础 2 秒眩晕。改造属性仍由已发布的战锤目录与求值器提供。

本轮格挡包含进入、保持、受击、破防、收回，复用双手剑防御判定、体力和弹反逻辑。网络回查修复了攻击/格挡互斥、旧轮次回执干扰新动作、客机快速近战未取消旧服务器攻击、破防重复播放及迟到受击反馈打断收回。详细覆盖见 [回查记录](../../../SourceAssets/SteelWarhammer20261014/NetworkReviewV1/REVIEW.md)，动作说明见 [格挡 V1](../../../SourceAssets/SteelWarhammer20261014/GuardV1/README.md)。

## 公开源码与共享接入边界

[source-manifest.json](source-manifest.json) 记录本次代码/配方清单、具名基线和散列。可以独立归属的战锤执行器、砸地范围效果、音效路径、姿态/接触参数、格挡控制、快速近战和审计源码发布到原路径。共享工具/角色/联机文件只保存已辨明的本次修改，没有覆盖本机其他任务的工作。

1. [quick-and-tool-git-integration.patch](quick-and-tool-git-integration.patch) 对应记录的 Git 基线。没有并行差分的工具步态和快速近战声明同时发布到原路径；混有新命中预测、资源预备、检视修改的工具接触、快速近战实现与角色动作优先级仅保留本次补丁，不将旧基线重建文件放回源码路径。按 source-manifest 的 `publication` 字段区分，已落到原路径的部分不要重复应用。
2. [guard-network-named-baseline.patch](guard-network-named-baseline.patch) 基于 `GuardV1/Before` 与 `NetworkReviewV1/Before` 的具名本机快照，覆盖共享格挡声明、输入/时钟/视模挂接、第三人称动作、受伤防御入口、轮次回执及快速近战权威互斥。**它不是直接针对公共 HEAD 的补丁**；对应 Before 已按归档清单保存，应用前比较 LF 文本 SHA-256。
3. [build-prerequisites.patch](build-prerequisites.patch) 只记录本次构建所需的最小修正：两处局部 Slot 重名、食物审计 TSharedRef 调用、篝火审计友元及凸包字段/局部变量。没有公开这些并行功能的完整脏文件。
4. `ProductionBluntAuthority.cpp` 已包含其他会话的新普通连击交接，因此只在上述具名基线补丁保存本次网络互斥修复。没有把移除了新连段逻辑的旧候选提交到源码路径；完整本机文件保持原样。

**公开切片不能作为干净检出即可构建/运行的完整 FPSGAME。** 完整工具调度、当前普通连击头文件、角色档案和第三人称框架仍含未在公共主线完整落地的前置，见 [本地接入依赖](integration-dependencies.json)。恢复时必须统一合并工具声明、执行器、时钟、技能输入与共享档案协议，不能只复制新 cpp。此前已经公开的相关材料见 [战锤改造](../WarhammerMods20261015/README.md)、[联机批次](../Multiplayer20261014/README.md)、[技能批次](../SkillMagic20261015/README.md)。`WarhammerNetworkAudit` 的远端控制器 fixture 来自战锤改造批次的 `WarhammerModificationAuditCommandlet`。

另一路的 `ModulesV1`、检视系列和 `NormalComboSwapV5/FlowV6/RhythmV7` 保留原位，未作为本轮修改归档或公开。当前回执确认普通攻击作者版为 **NormalComboRhythmV7**，六条正式动画仍写入 `NormalComboV4` 包目录。整理期间其他会话继续增加普通攻击本机命中预测，本轮将这些混合文件保留为补丁发布。最新作者/导入器、正式包与并行运行源码的只读时间点散列见 [latest-development.json](latest-development.json)，并行任务可继续推进，不以该记录锁住它们。这里的 V4 作者仅是保留依赖，不是当前最新普通攻击资产；没有重新运行旧导入器。

## 制作与资产恢复

| 内容 | 本次保留入口 | 重要前置 |
| --- | --- | --- |
| 初始锤体/握持/材质 | `SteelWarhammer20261014` 根目录、`MaterialRepairV1`、`SprintDragV1` | 用户 Meshy GLB；已许可原生双手工具手模 |
| 普通三连击基线 | `NormalComboV4` | `RhythmClearanceV2`；后续普通攻击任务另行维护 |
| 重击/冲刺砸地 | `HeavySlamV4`、`SprintSlamV1`、`SprintReadinessFixV1` | 原生镐/斧骨链、地面标记、运行时落点与镜头合同 |
| 烟尘/碎石/裂纹 | `SlamFXV2`、`CrackReliefV3` | V2 烟尘/碎石仍使用；V3 替换被否定的放射线裂纹 |
| 上挑 | `UppercutRightAnatomyV7` | `UppercutTiltClearanceV6` 的 Blend/表面数据及更早源链 |
| 旋风 | `WhirlwindInertiaV8` | 双手剑 RecoverV6 供体、NormalComboV4 待机、原生皮肤站位 |
| 快速近战 | `QuickCombatLeftWristV7` | `QuickCombatReachV6`、双手剑突刺供体；当前释放音复用剑的钝击音 |
| 格挡 | `GuardV1` | NormalComboV4 待机、WhirlwindHandoffV5 求解函数 |
| 专用声音 | `GroundImpactAudioV1`、`NormalSwingAudioV1`、`UppercutAudioV1` | 用户提供砸地、钝器挥舞、钝器上挑 mp3 |

表内阶段均在 `SourceAssets/SteelWarhammer20261014/`。`SprintDragV1/author_sprint.py` 的烘焙函数仍被多条当前作者脚本通过 AST 读取，旧文件不能按版本号批量清走。作者配方是历史分阶段工具，不应按目录顺序无差别重跑；旧导入器可能重置已保存的新资产，先确定目标阶段与实际包名。

合法原始源/原生供体 → 依赖阶段作者数据 → 当前作者 Blend/FBX → 对应导入器 → 正式原生构建，是恢复次序。换机器须调整脚本中的本机 Blender/UE/输入路径。模型、音频、贴图、密集骨架采样、Blend/FBX、UE 包和构建产物不随公开 Git 分发；[local-assets.json](local-assets.json) 只记本地散列，不授予第三方再分发许可。Fab 搜索结果不表示本机已领取或安装相应资产。

## 废案归档与技能

322 个文件、471,807,673 字节（约 450 MiB）移入 `trash/warhammer-combat-retired-20261015/`，全部移动后按 SHA-256 读回一致。范围为用户明确否定且已无活动源码引用的三连击 V2/V3 源与 30 个 UE 动画包、已替代 Before 快照、失效构建记录及重复日志。没有永久删除。

[archive-manifest.json](archive-manifest.json) 记录原路径、目标、大小、散列、原因和保留替代物。历史说明中的旧源/Before 路径通过此清单恢复；不要把恢复过时包误当作当前导入步骤。活动源链、最终回执以及并行任务保持原位。归档工具为 [close_warhammer_combat_20261015.py](../../../Tools/Publication/close_warhammer_combat_20261015.py)，已完成的有日期清单不再重新生成。

另有 4 份本轮发布候选草稿（60,586 字节）因改为补丁发布而移入 `trash/warhammer-publication-drafts-20261015/`，散列读回一致；见 [草稿归档清单](publication-drafts-archive.json)。总归档 326 份，当前源码未因归档改变。

个人技能维护源与工程镜像均更新：[战锤战斗合同](../../../skills/ue5-weapon-workflow/references/warhammer-combat-contracts.md)、[原生骨链](../../../skills/ue5-fps-arms-animation/references/warhammer-native-chain.md)、[格挡轮次与权威归属](../../../skills/ue5-save-load-replication/references/melee-guard-intent.md)。相关武器、手臂、存档与联机章节已加入入口。

## 历史证据与剩余项

完整本机 Game 构建于 2026-10-15 22:57:21 完成，Editor 构建于 23:07:44 完成；此前授权的 `WarhammerNetworkAudit` 52 项、`WarhammerModificationAudit` 103 项通过，合计 155 项、0 失败。见 [历史回执](historical-evidence.json)。这些是完整本机当时的构建/隔离权威测试，不能转述为本次公共切片已重新编译，也不证明真实网络传输或第一人称动画通过验收。

仍待完成：普通挥舞、上挑、旋风、快速近战释放、格挡/弹反的旁观者空间音效同步；真实主机/客机、延迟/丢包/重连与最终音画体验。砸地声音随复制冲击波已有路径。本轮仅执行归档散列、公开内容与 Git 推送检查，未重新运行游戏测试。
