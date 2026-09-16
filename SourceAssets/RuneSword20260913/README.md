# 双手符文剑 · 当前作者入口

宿主及 Git 根为 `D:/FPS3D/FPSGAME`，物品 `ue_rune_sword`，游戏资源目录 `/Game/Weapons/AzureRunesword20260913`。

**2026-09-16：当前接入 [InspectGripArcV46](InspectGripArcV46/README.md) 的 V47。两件事：(1) 前臂扭转分布——把两臂压在肘关节骨上的旋前（右 177.4°、左 99.3°）按实测蒙皮位置分散到 `lowerarm_twist_01/02_*`，工作区间肘扭转降到 0.0°；(2) 转刀重建——按参考视频逐帧量出的柄尾画面角做时钟，接触点固定在实测手/剑接触顶点（漂移 0.000000 m），剑柄画面角与参考最大偏差 0.01°，剑尖最近进深 +0.114 m 不再穿相机，窗口之外与上一版逐位相同。此版未测试，由用户测试。**

**2026-09-16：新增冲刺举顶竖劈 `A_RuneSword_Overhead`（[V49](InspectGripArcV46/README.md)）：按住 Shift 奔跑中攻击即触发**，1.30 s，由已接受的重击抬举与下劈**重新计时**而成（没有重解任何姿势），命中窗 0.44–0.54 s 对齐剑身真正在相机前方的劈砍段。原普通攻击与蓄力流程不变。此版未测试，由用户测试。

**2026-09-16（已停做）：原创转剑 `A_RuneSword_Twirl` 与 L 键按要求删除**，整套作者文件归档在 `trash/sword-twirl-v48-retired-20260916/`（清单见 `Docs/AssetArchives/sword-twirl-v48-retired-20260916.json`）。

**2026-09-15（历史）：接入 [OffscreenLeftInspectV42](OffscreenLeftInspectV42/README.md)。移除检视中途左手再次入镜的动作，保持左臂画外，结束时接回原双手待机。右手、剑和 V41 肩臂修正沿用，完整动作仍为 2.90 秒。V36 原文件和恢复入口保留。**

## 保留的动作与作者源

| 用途 | 当前入口 |
| --- | --- |
| 普通左右斩、重击、突刺和跨步 | V8/V12/V16/V17 与其保留依赖，见 [参数和状态](../../Docs/Weapons/runesword-baseline-20260914.md) |
| 左拳抵剑格挡 | [FistBraceGuardV21](FistBraceGuardV21/README.md)，用户反馈“成功”；V20 是必要姿态输入 |
| 蓄力左臂及释放/未蓄满衔接 | [ChargedArmV22](ChargedArmV22/README.md)，用户反馈“OK了” |
| 切剑装备 | [BackDrawEquipV23](BackDrawEquipV23/README.md)，用户明确保留的 1.20 秒背后拔剑 |
| 当前 F 键检视 | [InspectGripArcV46](InspectGripArcV46/README.md) 的 V47：前臂旋前分散 + 转刀按参考相位重建；2.90 秒；未测试 |
| 冲刺举顶竖劈 | [InspectGripArcV46](InspectGripArcV46/README.md) 的 V49：重定时已接受重击得到的举顶下劈，Shift 奔跑中攻击触发；1.30 秒；未测试 |
| 上一版 F 键检视 | [OffscreenLeftInspectV42](OffscreenLeftInspectV42/README.md)，移除中途左手入镜，保留右手转剑和末尾回握 |
| 用户认可的检视母版 | [ReferenceReplicaV36](ReferenceReplicaV36/README.md)，指定视频 76–78 秒逐帧重建，2.90 秒；保留原姿态、原文件与恢复入口 |
| 默认待机位置历史版 | [DefaultIdleInspectV38](DefaultIdleInspectV38/README.md)，用户反馈更僵硬，已停用 |
| 肩侧过渡历史版 | [ShoulderOutsideInspectV37](ShoulderOutsideInspectV37/README.md)，用户反馈腕臂仍扭曲，已停用 |
| 霜晶剑正在引用的完整母版 | [WristOutsideInspectV34](WristOutsideInspectV34/README.md)，只保留 Blend；其中 Inspect 未接受 |
| CSGO 源动画读取与配合研究 | [GitHubMotionStudy20260915](GitHubMotionStudy20260915/README.md)，原始资源留本机，公开原创研究工具与文字 |
| 两个指定视频的连续帧 | [VideoReferenceStudy20260915](VideoReferenceStudy20260915/README.md) 与 [PivotStudy20260915](PivotStudy20260915/README.md) |

已用源依赖为 `WeightLeftV5 → DiagonalHeavyV6 → CompactRecoveryV8 → ChargedHeavyV12 → StrideThrustV16 → GuardParryV18 → GuardPoseV19 → FistBraceGuardV20 → FistBraceGuardV21 → ChargedArmV22 → BackDrawEquipV23`，V3/V4 等保留材质、抓握与历史读取依赖。版本旧或含未接受姿态，不自动等于整个目录可退役。

V24–V33、V35 检视目录及 V34 非共享内容归档至 `trash/sword-inspect-paused-20260915/SourceAssets/RuneSword20260913/`。完整原始位置、散列与保留原因见 [归档清单](../../Docs/AssetArchives/sword-inspect-paused-20260915.json)。旧脚本可能覆盖同名 UE 动画，未经用户恢复制作的指示不要运行。

## 公开与恢复边界

本轮只发布选定作者代码、研究脚本、文档和 Skill。模型、Manny 手臂、图像/视频、声音、Blend/FBX/uasset、反编译模型及密集源骨骼数据留本机；原始素材各自遵守来源许可。只克隆 Git 不能恢复完整可运行画面。

V5 的 ImportHost 仍是本机导入依赖，不递归移动其 Content 联接。根目录 `build_sword.py` / `import_sword.py` 只是初始制作入口，不生成当前全部版本。本次未改原生代码或运行游戏测试。

- [近战武器标准](../../MELEE-WEAPON-WORKFLOW.md)
- [上一轮归档与发布边界](../../Docs/Weapons/melee-publication-20260914.md)
- [Source/CSGO 手部 Skill](../../skills/ue5-fps-arms-animation/references/source-hand-animation-study.md)
