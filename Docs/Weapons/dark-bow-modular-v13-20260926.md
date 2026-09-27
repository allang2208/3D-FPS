# 木弓五槽改造 V13

2026-09-26：用户批准按五槽方案继续制作。后台完成模型分离、导入保存、改造目录与 UI 接入、手持装配、图标制作和原生构建。没有启动交互式 UE 编辑器、游戏、自动测试或验收截图。实际操作和视觉效果由用户测试。

## 模型拆分

| 改造槽 | 本次实际资产 | 原装与首个选项 |
| --- | --- | --- |
| 弓体 `riser` | `SM_Bow_BodyModular` | 原装 / 强拉力调校，几何相同 |
| 握把缠带 `grip` | `SM_Bow_GripWrap` | 原装绿色 / 棕色蜡麻材质 |
| 弓弦 `string` | 既有两段动态弦 | 原装 / 更细的浅棕快弦 |
| 箭台 `arrow_rest` | `SM_Bow_ArrowRestWood`、`SM_Bow_ArrowRestLined` | 木托 / 皮垫木托 |
| 瞄具 `sight` | 既有 V12 木制瞄具 | 安装 / 拆除 |

弓胎是一整根连续木体，弓梢和弓臂绑绳仍归弓体；只按原网格的独立连通壳分出中心握把绳，保留原表面和 UV。没有把一体长弓硬切为上下可拆弓臂。新箭台在既有箭杆支撑点下方制作，安装底座按原弓表面采样贴合。手掌握持表面、动画和 V12 瞄具维持原数据。

新增网格/材质位于 `/Game/Weapons/DarkBow20260925/ModularV13`，共 4 个 StaticMesh 和 2 个 Material，已通过后台 commandlet 保存。弓体源为用户此前提供的木质长弓；源入口和原资产记录见 [木质长弓替换](dark-bow-wood-longbow-20260925.md)。本批箭台为本地原创几何，没有上传或公开发布源资产。

## 改造与结算

`Content/ColdSteelData/bow-gunsmith.json` 提供五栏和十个选项（每栏含原装）。`UGunsmithSystem` 复用现有草稿、撤销、实例定位、应用和 `CommitState` 保存。临时视觉数据只用于预览/装备解析，存档仅持久化 `gunsmith_parts` 选择，防止倍率重复写入基础属性。

- 强拉力：武器基础伤害 ×1.12、箭速 ×1.06、拉满耗时 ×1.10、体力消耗 ×1.15。
- 蜡麻缠带：稳持晃动 ×0.85、满弓保持时间 ×1.10。
- 快弦：拉满耗时 ×0.94、箭速 ×1.04、满弓保持时间 ×0.92。
- 皮垫箭台：搭箭耗时 ×0.93、腰射扩散 ×0.90。
- 拆除瞄具：删除实际瞄具网格，ADS 使用箭台对位分支，箭台锚点对到相机前方。

伤害倍率在角色属性与强化的现有共享结算前处理；拉弓改造与强化/弓精通继续相乘。其余参数由弓组件和 UI 的同一套改造倍率提供。改造台、物品详情和比较摘要显示实际组合值，满 ADS 的随机扩散仍为零。弓体调校没有另造外观，选项说明及图标来源均明确记录。

## 旧存档和箭矢

`bow_presentation_revision` 升至 25。旧版 `arrow_rest` 实际装的是箭，本次加载迁移把 `bow_part_arrow_rest_*` 移到 `bow_part_arrow_*`，再配置真正的支撑箭台。自定义箭网格按原迁移规则保留；实例 ID、强化、品质、摆放和箭袋数据沿用原存档。

`arrow` 是独立运行槽，不进入五栏改造。搭箭显示与射出箭使用该槽，换箭台不会同时更换箭矢。选箭与扣箭仍使用现有箭袋路径。

## 预览与图标

`ColdSteelBowAssembly` 负责纯展示装配，改造台和动态装备图标共用。展示对象不依赖角色手臂；部件资源异步加载，旧回调失效，面板关闭取消加载并释放组件。改造台支持旋转、缩放和当前/原装对比。

部件 PNG 从当前可编辑模型生成：5 张分类图、10 张原装/改造选项图，1024×1024 RGBA、安装方向侧视、单件透明背景。快弦图以实际满拉的双段弦形状呈现；强拉力复用原弓胎图；拆除瞄具复用中性移除符号。另更新 640×320 整弓回退图。16 张 PNG 及相应 UE Texture2D 均已保存。动态图标复用现有有界队列与缓存，按装配外观更新。

## 制作入口和完成凭据

- 可编辑模型：`SourceAssets/BowModular20260926/Bow_ModularParts.blend`。
- 图标场景：`SourceAssets/BowModular20260926/Bow_ModularIcons.blend`。
- 作者和执行脚本：同目录 `author_parts.py`、`import_assets.py`、`install_config.py`、`render_icons.py`、`install_icons.py`、`import_icons.py`。
- 已保存资产回执：`import-receipt.json`、`icon-import-receipt.json`。
- 目录和 PNG 安装回执：`install-receipt.json`、`icon-install-receipt.json`。
- 后台构建成功：`Saved/BowAudioStillNorth20260926/build-bow-modular-v13-20260926-r2.log`。
- 本批修改前副本：`Saved/BowModular20260926/Before`。

用户可在背包选择弓后点“改造武器”，或选中/装备弓按 J 打开。选择后点击应用保存；撤销或关闭未应用草稿不会写入装备。未运行游戏测试，编译和资源保存不代表手感、接触或 UI 已经过实机验收。
