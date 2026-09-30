# 改造图标覆盖检查（2026-09-30）

这是弓箭替换完成时的阶段快照；下表中的遗漏随后已按 [补齐记录](remaining-attachment-icons-20260930.md) 处理。原图备份现归档到 `trash/modification-icons-20260930/BowFramedIcons20260930/Original/`，不再是当前运行图标。

本次按用户要求替换弓箭，并检查全部改造目录及运行时图片解析规则。统计单位是 UI 引用（分类、原厂和选项），不是独立 PNG；共享图片会重复计数。未启动游戏或进行运行验收。

## 本次弓箭交付

- 5 栏：弓体、握把、弓弦、箭台、瞄具。
- 21 张内置 imagegen 生成母图，对应 27 个 PNG 引用。
- 来源：既有部件图 + 已认可的 muzzle_brake_framed_v2 金属框母版。
- 图片目录：Content/ColdSteelData/AttachmentIcons20260913/FramedBows。
- M4GunsmithLayout.cpp 已增加弓箭目录分流和完整图片等比显示。
- 原图保留；移除瞄具采用银色减号，正常原厂配件不含禁止标识。

## 覆盖结果

| 类型 | 新版目录引用 | 其他已有图片 | 缺图回退 |
|---|---:|---:|---:|
| firearm | 405 | 8 | 4 |
| bow | 27 | 0 | 0 |
| staff | 0 | 20 | 12 |
| melee | 0 | 96 | 0 |
| tool | 0 | 40 | 0 |

“其他已有图片”不直接等于已升级。法杖现有选项使用其原有金属框风格；近战和工具仍读取原部件图，没有本轮新版框图目录。工具的强化按钮使用 SMeleePartIcon 程序图形，是独立于改造槽的附加项，也未换成生成图片。

结论：弓箭本次覆盖完整；所有武器/工具的改造图标尚未全部升级。

## 枪械遗漏

手枪握把表由 PistolGripSurface::MergeOptions 动态合并，因此不能仅检查 weapons[].options。
- `ue_m1911_reargrip_false`：existing_image
- `ue_m1911_reargrip_pistol_grip_granular`：existing_image
- `ue_m1911_reargrip_pistol_grip_diamond`：existing_image
- `ue_m1911_reargrip_pistol_grip_quickdot`：existing_image
- `ue_g18_reargrip_false`：existing_image
- `ue_g18_reargrip_pistol_grip_granular`：existing_image
- `ue_g18_reargrip_pistol_grip_diamond`：existing_image
- `ue_g18_reargrip_pistol_grip_quickdot`：existing_image
- `ue_m16a2_underbarrel_tactical_vertical_foregrip`：fallback
- `ue_a762_underbarrel_tactical_vertical_foregrip`：fallback
- `ue_pkm_lowpoly_underbarrel_tactical_vertical_foregrip`：fallback
- `ue_lmg201_underbarrel_tactical_vertical_foregrip`：fallback

其中 M16A2、A762、PKM、LMG201 的 tactical_vertical_foregrip 没有专属图，运行时沿用分类图。

## 法杖缺图

这些分类/原厂项缺少对应 PNG，当前走后备图形/分类资产；不能算作完整的精致图片覆盖。
- `ue_apprentice_staff_category_head_crystal`
- `ue_apprentice_staff_head_crystal_false`
- `ue_apprentice_staff_category_crown`
- `ue_apprentice_staff_crown_false`
- `ue_apprentice_staff_category_shaft_rune`
- `ue_apprentice_staff_shaft_rune_false`
- `ue_apprentice_staff_category_grip_lining`
- `ue_apprentice_staff_grip_lining_false`
- `ue_apprentice_staff_category_tail_charm`
- `ue_apprentice_staff_tail_charm_false`
- `ue_apprentice_staff_category_mana_line`
- `ue_apprentice_staff_mana_line_false`

完整逐项列表见 SourceAssets/BowFramedIcons20260930/coverage.json；审计脚本为 Tools/AssetPipeline/audit_attachment_icon_coverage_20260930.py。

## 落盘与构建状态

- FramedBows 的 27 个 Texture2D 已通过后台 commandlet 导入保存。
- 同步替换原有 bow_dark PNG 路径，原图备份在 SourceAssets/BowFramedIcons20260930/Original；现有二进制也可按原路径读取新图。
- 新增目录分流代码已完成单文件编译，但完整 Editor 构建被 HundredEyedSlagMonster.cpp 的 Mesh/Instigator 隐藏成员及 FOverlapResult 未定义错误阻塞，基础 DLL 未更新；未修改该任务外文件。
- 未启动交互编辑器或游戏，未进行运行测试。
- 原路径对应的 27 个 Texture2D 也已通过后台 commandlet 保存；共保存 54 个纹理包（两个路径，每个 27）。
