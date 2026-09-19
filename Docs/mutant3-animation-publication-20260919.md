# 突变体-3 动作归档与发布（2026-09-19）

本次只整理突变体-3 动作制作、恢复说明和相关技能。当前运行类、战斗逻辑与正式 `Content/Monsters/Mutant3Meshy` 未改；游戏效果仍由用户测试。仓库按 `WORKFLOW.md` 第 4、5、6、7、8 节执行归档和精确发布，不纳入并行武器、建筑、四足等修改。

## 当前保留

- 完整源：`SourceAssets/Mutant3Meshy20260915/godot_runner/Mutant3_Meshy_GodotRunner.blend`。
- 固定输入：同目录 `Mutant3_Meshy_CombatBase.blend`，从当前完整源按字节复制，同目录保留相对材质路径；`author_runs.py` 改为读取它，不再依赖已归档 revision2。
- 两条当前跑步：Denys Almaral `running_58f`，原 Godot 运行别名 `Walk`；Running 1.875 s / 240 cm/s、RunFast 1.25 s / 360 cm/s，FBX 在 `godot_runner/final/`。
- 站立受击：`godot_runner/combat_base/` 保留 Hit_Chest 源、重定向及最终 FBX，Stagger 0.9 s。当前完整 Blend 保留所有非跑步动作。
- 模型、PBR、原始授权来源、其他现役动作、物理输入与制作工程保留；旧原始源动作中的跑步/受击是来源档案，不等于当前已采用成品。

## 归档

共 **114 个文件，393,506,881 字节（约 375.28 MiB）**，移入 `trash/mutant3-animation-retired-20260919/`：

- 被否定的 revision2 Jog 跑步制作包。混合包中的有效 Hit_Chest 已先保留。
- 旧原版完整 Blend、原跑步及倒地受击最终 FBX、被替换的包备份和已替代 Blender 自动备份。
- 制作工程内旧跑步动画与 Jog/ZombiePosture 专用源/重定向包。
- 未采用的 Hyper Chase 样包调查和 Quaternius 免费候选；只是未采用，不宣称这些动作本身不合格。

[归档清单](AssetArchives/mutant3-animation-20260919.json) 逐文件记录原路径、归档位置、大小、SHA-256、原因、替代入口，并记录 4 个有效输入的保留副本。移动前限制路径到本任务目录，移动后已读回比对大小与散列。此记录不代表游戏或动作验收。

## 恢复与发布边界

当前制作/导入入口为 [Godot runner README](../SourceAssets/Mutant3Meshy20260915/godot_runner/README.md)。旧初版和 revision2 安装流程会带回被替代动作，不能当作当前恢复入口。旧文件中的路径和时间保留其历史含义；按归档清单选择性恢复，不整包覆盖当前正式 Content。

Git 提供脚本、合同、许可说明和恢复映射，不提供本机 Blend、FBX、GLB、ZIP、UAsset 或 trash。克隆仓库后仍须从有授权的本机资产备份恢复当前完整源、固定输入及正式 Content。被移除的旧文本还可从提交 `4c3ca2a583bd911230dd6180166f1817983c69f6` 取回。

当前跑步署名与 CC BY 4.0 修改说明保留在 Godot runner README 和 `sources/LICENSE.md`；模型 Meshy 授权与 Mesh2Motion CC0 分别记录，不将整包统一称 CC0。未发布候选二进制或下载凭据。

## 技能沉淀

[怪物动作迁移与归档](../skills/ue5-monster-workflow/references/monster-motion-migration.md) 新增实际场景引用追踪、源动作意图、样包和许可边界、速度/腿长换算、站立受击选源，以及有效/废弃混合包的归档方法。项目技能与个人技能对应部分同步；失败跑姿不列为已认可模板。

只进行用户本次要求的仓库整理与推送检查；未启动编辑器、游戏、渲染或玩法测试。
