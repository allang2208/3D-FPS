# 枪械快速近战：收尾、归档与公开恢复边界

日期：2026-09-19。用户在 recover 修正后确认“成功结束”，授权归档废案、更新 SKILL 并推送 GitHub。

## 当前版本

| 范围 | 当前作者源 | 运行资产 |
| --- | --- | --- |
| M4 六套 | `SourceAssets/M4QuickMeleeRefine20260919N` | `/Game/Weapons/M4QuickMeleeReplica20260919/<Profile>/A_M4_QuickCombat_<Profile>` |
| AKM 五套、ASH-12 Base | `SourceAssets/RifleQuickMelee20260919` | `/Game/Weapons/RifleQuickMelee20260919/<Weapon>/<Profile>/A_<Weapon>_QuickCombat_<Profile>` |
| QBZ191 五套 | `SourceAssets/QBZ191QuickMeleeGrip20260919O` | `/Game/Weapons/RifleQuickMelee20260919/QBZ191/<Profile>/A_QBZ191_QuickCombat_<Profile>` |

步枪共 17 条动画（QBZ191 O 覆盖其中五条），均为 0.9 s，接触 1/6 s。AKM／QBZ191 弹鼓沿用 Base。共享角色文件中的其它枪械扩展属于并行工作，不随此次发布。

最后的 [recover 修改](quick-combat-recovery-20260919.md) 同时归位动作权重和视模组件锚点，统一计时，在结束前交给当前枪型／配件的待机姿态；保留击打、抓握及业务时序。

## 归档

本机 `trash/quick-melee-retired-20260919/` 收入 13 个明确路径，共 117 个文件、2,193,927,234 字节。包括 J／L／M 作者废案、对应阶段文档、被替代的 UE／C++ 备份及 QBZ191 探索性求解器。逐文件原路径、目标、大小、SHA-256、原因与保留替代物见 [清单](quick-melee-archive-20260919.json)。移动前核对范围，移动后散列一致，未删除文件。

仍保留 I 的参考帧／输入读取与制作记录、K 的可编辑源／支撑求解器、N 的腕臂求解器、Rifle 目录中的旧 QBZ191 Blend。它们是当前作者依赖或参考依据；不是待清理废案。历史对比脚本已改读归档 M，不能用旧导入脚本覆盖当前版本。

## 公开内容及重建

公开 C++、作者／导入／诊断脚本、手工参考参数、版本说明和归档散列；原始视频、第三方模型／贴图、Blend／FBX／uasset、密集骨骼数据、预览媒体与执行日志均留本机。沿用 [资源恢复规则](../AssetSetup.md)，商用使用许可不等于源文件再分发许可。公开仓库本身不含可直接运行的完整资源包。

在有已许可本机内容的环境中，按 I 输入读取／K 参考拟合与作者源 → M4 N → Rifle 跨枪适配 → QBZ191 O 的顺序恢复；各目录 README 说明所需 `authoring.json`、源 Blend 及运行路径。先恢复本地输入，再执行作者与导入入口。导入会覆盖同名运行资产，最终 QBZ191 必须用 O，M4 必须用 N。源宿主固定为 `D:/FPS3D/FPSGAME`，换机需修改各脚本目的地。

对应经验已同步到个人和工程镜像的 [快速近战接触与收势 SKILL](../../skills/ue5-fps-arms-animation/references/quick-melee-contact-recovery.md)，武器技能增加分流入口。

## 检查边界

此前 N 与 O 的检查是当时用户明确要求的排查；数值保留在各版本记录。recover 已完成必要 Editor 构建，日志 `Saved/BuildEditor/quick-combat-recovery-20260919.log`。此次仅执行用户要求的仓库整理／发布检查：归档散列、精确暂存、差异、文本语法、链接、许可／敏感内容边界及远端回读。未重新运行游戏、测试、截图或渲染，游戏效果由用户测试。
