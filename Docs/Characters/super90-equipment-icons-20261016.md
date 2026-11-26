# Super90 源装备图标与目录接入收尾 — 2026-10-16

随 Benelli M4 模型包载入的硬壳手套 `ue_hardknuckle_gloves` 与 ST6 衣袖 `ue_st6_sleeves`（2026-10-06 交付，见 [Super90 交付记录](../Weapons/super90-20261006.md)），本轮按衣物标准工作流完成剩余开发：装备图标合同与运行时图标路径。装备网格、材质、覆盖与存档接入此前已落盘，本轮核对未改动。

## 已核对的既有接入

- 两件物品 `rig_meshes` 覆盖当前全部 25 个原生 profile（含后续复用 Super90 绑定的 M870），无缺口。
- 覆盖合同正确：手套缺省回退 `glove_covers` [2]（全指款隐藏手部与腕部过渡），衣袖 `world_covers` [0,1] 及 Body/Jason `rig_world_covers`，第一人称回退 profile `shirt_covers` [0,1]。
- 逐槽生产材质 `M_S90_glove_hardknuckle`/`M_S90_sleeve_st6_generalist` 与拾取网格均已保存；配方 `material` 为空，不整件覆盖。
- 目录、强化、军械库一次性发放与烘焙目录（`/Game/Characters/ModularOutfit20260924/Super90Source20261006`）齐全。

## 本轮改动

1. **手套图标重制为单只空右手套**：M4 原生派生生产网格取右侧，按共享手指松弛姿态摆放，沿用 `glove_hardknuckle` 生产 BaseColor/Normal；320×320 RGBA 透明底、正交镜头、主轴约 91% 填充、曝光按生产底色校准。旧版整对拾取网格散列构图按手套图标合同退役。
2. **衣袖图标重制**：该物品即双臂衣袖，按成套双袖展示；480×320（3×2 占格）、同一透明正交与曝光校准规则，肩口朝上成套排列。
3. **运行时图标路径**：两件物品的 `ue_equipment_icon_mesh` 置空，与既有衣物一致使用目录 PNG，不再用成对拾取网格生成捕获图标；`world_mesh` 保留为世界掉落网格。置空字符串经既有迁移把旧存档实例中的残留字段一并清空。
4. **后续入口同步**：`render_catalog_icons.py` 的手套/衣袖改调 `render_equipment_icons.py`，避免下次批量出图回退旧构图；`publish_catalog.py` 不再写 icon_mesh。弹药与整枪图标入口不变。

## 落盘

- 正式 PNG：`Content/ColdSteelData/Icons/Super90Source20261006/ue_hardknuckle_gloves.png`（320×320，填充 0.9125）、`ue_st6_sleeves.png`（480×320，填充 0.9125）。
- 作者副本、展示场景与回执：`SourceAssets/BenelliM4Super9020261006/EquipmentIcons/`；渲染日志 `render_equipment_icons.log`。
- 图标仅改展示副本，不回写穿戴网格、动画或掉落模型。

## 状态

后台 Blender 制作与保存已完成；未运行游戏、未做视觉验收。背包/仓库中的实机图标观感由用户体验。
