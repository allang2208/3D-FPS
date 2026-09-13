# 当前采集木材制作入口

当前运行资源为 `SM_PoplarLog_Solid_A/B/C`（地面原木）、`SM_CutStump_A/B/C/D`（固定树桩）和 `SK_CutUpper_A/B/C/D`（含原树 Nanite 树冠的截断上半段）。本目录脚本仍按这些杨树变体配置，尚非通用新树种导入工具。

## 原木

保留 `raw_00001_.glb`、`textured_master_00001_.glb`、参考图、生成记录和 `HarvestTimber_Editable.blend`。现有母版可直接用于 `repair_solid_logs.py`；只有需要从冻结的纹理母版重建作者源时才运行 `prepare_timber_mother.py`。该准备器只制作母版和断面材质，不再生成初版碎面低模。

`repair_solid_logs.py` 输出 `SolidRepair/SolidTimber_Editable.blend` 以及 `SolidRepair/Delivery` 的闭合原木和 PBR。通过 UE Python 执行 `import_solid_logs.py` 导入，沿用已有 `M_PoplarEnd` 作为不透明年轮材质的制作输入。该脚本还保留 UE 网格导出步骤，供用户明确要求模型检查时使用；导出本身不代表检查通过。

`inspect_log_geometry.py` 仅在明确要求模型检查/渲染时运行。默认对象为当前 UE 导出网格；显式 `before` 模式读取 trash 中的初版 FBX 和旧法线图。已完成的历史对照图与几何记录保留在 `SolidRepair`，此次整理没有重跑这些检查。

## 树桩与上半段

在必要资源缺失时，UE Python 执行 `import_assets.py` 准备共用年轮参考、材质母版和声音；缺少声音源时可先用 `author_audio.py` 生成 `Delivery` 下两段 WAV。基础导入器不再读取旧 `Delivery/authoring.json` 或生成淘汰网格。

当前切割链按顺序为：

1. UE：`export_tree_sections.py`，导出原树主干源几何及材料表。
2. Blender：`cut_tree_sections.py`，生成匹配的上下主干、封面 UV 和可编辑 `FellingCut/MatchedTreeSections.blend`。
3. UE：`import_tree_sections.py`，导入静态切段、材质与切口轮廓，然后调用 `build_falling_assemblies.py`，生成保留原骨架和 Nanite 叶片组合的 `SK_CutUpper_*`。

离线批次需要续作时，`TREE_CUT_AUTHOR_VARIANTS` 可限定 `build_falling_assemblies.py` 的树形；默认 A–D。`FellingCut/assemblies.json` 记录该次生成批次，当前本机记录为 B/C/D，A 的保存记录在 `Saved/Logs/CutTreeAssemblies-Import.log`，不把三项批次记录称作四项检查。

`SM_CutUpper_*`、`M_FallingPoplar`、`MI_FallingPoplar_*` 和 `M_PoplarEnd` 虽未直接作为最终显示入口，仍是当前作者脚本的输入，不能因旧名称直接归档。`Delivery/T_Poplar_BaseColor.png` 与 `T_Poplar_ORM.png` 仍被保留的作者 Blend 使用。

## 废案与许可

本轮 49 个已替代文件移至 `trash/harvest-timber-superseded-20260913`，保持项目相对目录。包括初版原木/自制树桩/圆片、上一版原树树桩、旧 UE 树皮材质及纹理、旧制作脚本和上一份切割 Blend 快照。基础导入器的旧版本也有归档快照。

详见 [整理记录](../../Docs/AssetArchives/harvest-timber-superseded-20260913.md) 与 [逐文件散列](../../Docs/AssetArchives/harvest-timber-superseded-20260913.json)。不从 trash 覆盖当前 Content。原树、组合子资产、材质函数及其衍生二进制依旧保留在合法本机宿主，公开 Git 不是完整素材备份；来源见 [PROVENANCE](PROVENANCE.md)。
