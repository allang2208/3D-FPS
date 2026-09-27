> 本目录为历史记录。2026-09-27 整理时，已被替代／未选中的作者脚本、模型和导出移入本机 `trash/sword-publication-20260927/SourceAssets/HighlandClaymoreMeshy20260922/RidgePiercer20260927/`，可按归档清单恢复。当前制作从 [后继入口](../RidgePiercerRootV2_20260927/README.md) 开始。下文描述历史版本，不是重建入口。

# 高地双手剑专属剑身Ⅰ：棱脊穿甲刃

**当前几何已更新为 [收窄剑根 V2](../RidgePiercerRootV2_20260927/README.md)。** 原位更新同一个 UE 网格与菜单图标；本目录的几何尺寸和作者脚本保留为初版记录，后续制作使用 V2 入口。

2026-09-27，用户从三款概念中选择窄直的棱脊穿甲刃，要求制作。新模型、菜单图标和改造目录已导入保存；用户随后将属性调整为「第三段突刺伤害 +40%、第三段突刺韧性伤害 +40%、物理防御穿透 +10%、基础伤害 −10%」。没有运行游戏测试。

## 造型与接口

- 从当前 `JunctionBlendV5_20260927/Highland_ContinuousJunctionV5_Editable.blend` 的原装剑身派生，保留现有护手、凸出的蓝色宝石、握把及配重。
- 窄直主体，四面棱脊，长尖端；主体设计宽度从 3.8 cm 逐渐收至 3.3 cm，剑脊厚度 12 mm。剑尖坐标仍为 Z=88 cm，末段从约 72 cm 开始收尖、减薄。
- Z≤10.5 cm 的原接口位置及面角法线保持；上方连续过渡至窄刃。沿用 V5 的 `z=.058+.95*abs(x)` 接面与原 pivot，没有覆盖片或额外装饰环。
- 保留原生 UV、苍蓝纹样、顶点色和 Highland 材质；新增表面先生成角度加权法线，中脊两侧分组，UE 使用作者法线并重建 MikkTSpace 切线。
- 网格 11,211 顶点 / 22,418 三角形。UE 从当前原装网格继承 Nanite、LOD 及材质设置。
- 1024×1024 RGBA 菜单图标由本次真实剑身模型渲染，单件、透明底、剑尖水平朝左。该图是 UI 制作资产，没有追加验收渲染。

## 属性与接入

`blade_1 / highland_ridge_piercer` 仅允许 `ue_highland_claymore`，保留其他剑身选项。

| 属性 | 数据 |
| --- | --- |
| 第三段突刺伤害倍率 +40% | `combo_third_damage_mult: 1.4` |
| 第三段突刺韧性伤害 +40% | `combo_third_toughness_mult: 1.4` |
| 物理防御穿透 +10% | `physical_armor_penetration: 0.1` |
| 基础伤害 −10% | `damage_mult: 0.9` |

伤害加成复用现有 `Thrust` / 第三段连击倍率；韧性加成使用新增的 `ComboThirdToughness`，仅在非重击的第三段突刺快照中乘入，不影响前两段、重击、旋风或冲刺攻击。基础伤害 −10% 作用于武器基础伤害计算，第三段伤害倍率另行作用于该段攻击，不能据此将包含角色攻击和附加伤害的最终结果简化为两个倍率的乘积。

专属削韧倍率与全攻击削韧倍率相乘：例如蛮荒符文的 `1.3` 与本刃第三段的 `1.4` 组合，第三段韧性倍率为 `1.82`，其他攻击仍为 `1.3`；该倍率参与现有韧性伤害公式，不代表最终削韧数值本身。穿透另外参与物理防御结算，并可与蛮荒符文的 20% 穿透叠加。

新字段已接入数据加载、改造合并、攻击快照、枪匠总览/选中件详情及背包提示/比较。仍沿用模块装配与 `gunsmith_parts` 保存合同。这次新增原生属性字段，已在 UE 关闭时执行常规 Editor 构建，返回 `Succeeded / Target is up to date`；记录见 `Saved/BuildEditor/build-20260927-140710.log`。没有打开编辑器或运行测试。

已保存：

- UE 网格 `/Game/Weapons/HighlandClaymore20260922/RidgePiercer20260927/SM_Highland_Blade_RidgePiercer_V1`。
- PNG `Content/ColdSteelData/AttachmentIcons20260913/ue_highland_claymore_blade_1_highland_ridge_piercer.png` 和同名 UE Texture。
- `Content/ColdSteelData/highland-claymore-modules.json` 的独立模型条目，符文覆盖宽度适配为 3.8 cm。
- `Content/ColdSteelData/melee-gunsmith.json` 的专属选项、说明与属性。

通过已有编辑器互斥桥导入，最终结果 `HIGHLAND_RIDGE_PIERCER_INSTALLED` 记录于 `import-editor-02.txt` / `install_receipt.json`。回执保留首次导入时的 +25% 历史属性，当前属性以运行目录及上表为准。第一次导入在 PIE 状态下被脚本阻止，没有写入资产；结束游玩后完成保存。没有新开或重启编辑器，没有重新启动游戏。此次属性调整不需要重新导入模型或图标。

运行中的剑类模块目录有进程级缓存，新增槽位模型需在下次完整重开 UE 后读取；不要把仅退出再进入游玩当作已刷新模型目录。当前没有做运行或视觉验收，由用户测试。

## 可编辑源与维护

- `Reference/user_selected_ridge_piercer.png`：用户选中的造型。
- `Highland_RidgePiercer_Editable.blend`：新剑身与现有原装护手/握柄/配重的装配制作源。
- `Highland_RidgePiercer_MenuIcon_Editable.blend`：专用图标制作场景。
- `author_ridge_piercer.py`、`authoring.json`、`Export/`、`Icons/`：制作入口和产物。
- `import_ridge_piercer.py`：只导入本次新件与图标、重读并合并目录；不会重建原装组件或修改其他选项。
- `Before/<时间>/`：写入前的目录快照。恢复时只撤销本选项，不能整文件覆盖后续并行修改。

原高地剑与贴图来源/许可沿用 [原接入记录](../Integration/README.md)。概念由本对话内置 imagegen 生成，用户选定后通过本地 Blender 精确改形；没有调用收费图生 3D 服务。
