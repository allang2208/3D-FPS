# 巫婆暂停、归档与源码发布

2026-09-21 用户试玩反馈：普通巫婆反复调整仍不满意，人体动作粗模没有问题。按用户要求暂停，登记 `Docs/Backlog.md` W1–W3。优先怀疑原模型腿脚、长袍拓扑与蒙皮适配；未做本轮隔离诊断，不把怀疑写成唯一根因。后续从完整人体/骨架基础适配巫婆外观，不继续在原身体上叠加补丁。

## 保留入口

| 用途 | 入口与保留内容 |
| --- | --- |
| 当前问题对照 | F6 普通“巫婆” (`Witch`)；`/Game/Monsters/WitchMeshy/OriginalRobeV05` 内为 V06 身体和 V05 待机/走/死亡，`SpellSupportV07` 为两段攻击；原生 WitchMonster / WitchSpellAnimInstance / WitchProjectile |
| 后续动作基础 | F6“巫婆·动作基础候选” (`WitchFoundation`)；`/Game/Monsters/WitchFoundation`、`SourceAssets/WitchFoundation20260920`、`Tools/WitchFoundation`；完整 Quinn、待机和慢走保留。尚无候选攻击/受击/死亡与完整巫婆战斗 |
| 原始外观与来源 | `SourceAssets/WitchMeshy20260919/Meshy`、`Reference`；`Authoring/LayeredV04/Preserved` 的未切母版、头发/头、帽、上衣、原裙参考、双手、法杖、毒瓶及 PBR |
| 当前作者源 | `Authoring/CleanRobeV06`、`Authoring/SpellSupportV07` 和对应 Delivery；保留当前组合及独立分件 |
| 必要上游输入 | CloudGripV02 的干净源动作/握型；V01 原始身体及道具母版；V04 的完整身体输入、Preserved、Sources、Textures、RetargetedRaw；V05 的组合源与动作层仍供 `clean_robe_v06.py` 读取，不能整目录判废 |
| 原生重定向依赖 | UE `LayeredV04/Rig`、`LayeredV04/RetargetedRaw` 与 `PreviousCloudGripV02/SK_Witch_Meshy` 继续供 `retarget_layered_v04.py` 使用；这几个历史路径不是运行中的第二套裙子 |

## 废案整理

归档到本机 `trash/witch-retired-20260921/`，逐文件记录原路径、目标、字节、SHA-256、原因和替代物：

- [作者源清单](../AssetArchives/witch-retired-sources-20260921.json)：145 个文件。包含 LocalRetarget V01、RobeGait V03 成品/脚本、V04 被替代动作与拟合分件、错误供体/旧代理分件、冗余 Blend 备份和已完成的一次性诊断/关闭/修复脚本。V05 导入器仍使用的 `repair_v05_cloth_binding.py` 作为必要恢复工具保留。
- [UE 废案清单](../AssetArchives/witch-retired-assets-20260921.json)：40 个旧包。保留当前运行资产、材质/贴图/道具以及上表制作依赖后，按 AssetRegistry 的外部硬/软引用闭包筛选；先备份并校验，再由编辑器统一移出已退役包。

历史文档中的废案路径按这两份清单在 trash 找回；不要把旧导入器重新用于当前角色。源归档脚本 `Tools/Witch/archive_retired_sources.ps1`，UE 归档脚本 `archive_retired_assets.py`；它们记录此次明确范围，不是全工程清理器。

## 恢复与公开边界

优先从合法本机完整备份恢复上述当前 UE 包与作者目录，包括共享 WitchMeshy Materials/Textures/Props、原始骨架/物理依赖、`Monsters/AI`、毒蛆 VenomLiquid 材质和地图 Witch 导航。重新生成需要原 Meshy 输出、Epic 模板 Quinn/动作、已有护士动作及原 PBR；没有这些输入时，Git 中的脚本不构成完整资产交付。

当前原身体重建链为 `layered_v04.py` 的通用函数/保留输入 → `original_robe_v05.py` → `clean_robe_v06.py` → `Tools/Witch/import_clean_robe_v06.py`（统一 FBX 场景单位）→ `author_spell_support_v07.py` / `import_spell_support_v07.py`。只恢复当前结果时直接使用保留的 V06/V07 FBX 和 UE 包。全量重建 V05 中间态的导入器及布料绑定助手要求临时启用本机 `ChaosClothAssetToolset`，不是当前 V06/V07 日常导入的前置操作。候选恢复按 `Tools/WitchFoundation/prepare_template_sources.py`、`export_motion_sources.py`、`read_authoring_inputs.py`、`author_carry.py`、`import_candidate.py`、`finalize_candidate.py` 的实际阶段进行，完整源与曲线采样留在本机。

公开内容限本任务原生代码、精确共享接入改动、作者脚本、低密度配置、状态与归档清单。Epic/第三方模板和动作、Meshy 几何/PBR、GLB/FBX/Blend/uasset、逐帧骨架/表面采样、下载回执与日志、trash 不公开上传。原素材的使用授权不自动覆盖原始文件再分发。生成客户端只从环境读取密钥；密钥不进入仓库。

发布按 `WORKFLOW.md` 第 8 节检查根目录、origin/main、暂存差异、文件大小、敏感信息及许可边界；精确暂存并普通非强推。共享文件中的并行韧性、玩家身体、其他技能与全局工作流修改留在工作区。巫婆构造函数中并行韧性参数也不随本次发布，远端继续使用已有共享战斗接口。

本次只进行用户指定的整理和推送检查，没有重新运行游戏、动作测试或验收渲染。此前必要构建成功不覆盖用户此次不满意反馈。项目及个人 `ue5-monster-workflow` 已同步长袍人体、模型/动作问题区分、单位与归档经验；未认可的 V07 参数不列为成功模板。
