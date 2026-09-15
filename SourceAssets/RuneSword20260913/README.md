# 双手符文剑 · 当前作者入口

宿主及 Git 根为 `D:/FPS3D/FPSGAME`，物品 `ue_rune_sword`，游戏资源目录 `/Game/Weapons/AzureRunesword20260913`。

**2026-09-15：用户否定转剑检视 V35，要求暂停。检视没有最终获接受的版本；当前游戏文件冻结为 V35，不继续导入或替换。废案已移入 trash，后续状态以 [暂停与归档说明](../../Docs/Weapons/sword-inspect-paused-20260915.md) 为准。**

## 保留的动作与作者源

| 用途 | 当前入口 |
| --- | --- |
| 普通左右斩、重击、突刺和跨步 | V8/V12/V16/V17 与其保留依赖，见 [参数和状态](../../Docs/Weapons/runesword-baseline-20260914.md) |
| 左拳抵剑格挡 | [FistBraceGuardV21](FistBraceGuardV21/README.md)，用户反馈“成功”；V20 是必要姿态输入 |
| 蓄力左臂及释放/未蓄满衔接 | [ChargedArmV22](ChargedArmV22/README.md)，用户反馈“OK了” |
| 切剑装备 | [BackDrawEquipV23](BackDrawEquipV23/README.md)，用户明确保留的 1.20 秒背后拔剑 |
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
