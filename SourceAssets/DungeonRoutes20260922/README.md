# 保留作者空间的随机地牢 · 2026-09-22

目标地图 `/Game/GameMaps/L_Dungeon_Randomized`，以实际 `Receipts/install.json` 的 `map_saved` 为接入完成依据。原始样板与三房展示地图保留。

## 空间公式

固定标准通道（工作间、仓库工具柜、遗迹神像侧室） → 3～5 个作者房间 → 12 m 纯连接通道 → 一进三出岔路间 → 三条独立路线各 3～5 个房间 → 12 m 连接通道 → 末端检修开间。

- 房间候选：管线分配间、排水检修室、破损支护室的贯通变体。按真实门洞做刚体位移/转向，可交换出入口，不缩放房间或改变墙砖、管道、破墙比例。
- 起始检修通道通过 `DungeonDoorTransitions20260922` 的封闭扩宽段，从 1.32 × 2.38 m 净截面过渡到随机连接件的 2.76 × 3.15 m 净截面；墙面、顶面与地面一起衔接。`Config/start_connection.json` 随随机模块制作更新，避免重建时恢复尺寸不匹配的旧连接件。
- 岔路间 14 × 12 m，3.65 m 顶棚，四个 3 m 宽/2.8 m 高门洞；柱梁保留中央穿行与周边绕行，沿墙管线和冷暖光分别提示不同方向。
- 每个房间组独立抽取 3～5 的数量。相邻门洞优先使用 0.8 m 短门厅；必要时增加到 1.6、2.4 或 4 m，给不同外轮廓留足空间。组间纯通道为 12 m，不重复生成工作间。
- 三个岔路出口先各预留 24 m 起步通道，再向三块不同的扇区延伸。房间、破墙侧室与通道同时计入占地；与已有布局冲突时回溯换模板、入门方向或连接长度。
- 所有路线完整排布成功后才替换现有场景，防止失败时留下半个房间链。末端是可返回的检修开间，带 `future_route` 扩展锚点，不把一个开放门洞直接贴到另一堵墙上。
- 普通房间各有 10% 概率尝试附带一间 10 × 10 m 宝箱支房，每房最多一间，不占主链数量。侧门、两米门厅和宝箱房同时满足占地条件后才启用开门变体；无空间时维持原墙。规则与源资产见 `DungeonTreasure20260922`，概率为 `Config/rules.json` 的 `treasure_chance_per_room`。

## 交互与后续位置

红色工具柜由 `ADungeonStorageCabinet` 承接现有 `AColdSteelWarehouseChest` 的瞄准/E 交互、仓库面板与持久数据；保留原红色柜体和细节，不生成第二份库存。工作台标记 `DungeonStart.Workbench`；起始遗迹侧室放 Diana 神像，标记 `DungeonStart.Shrine`。改造、附魔、强化面板和神像赐福/任务按用户要求留待后续开发。

## 实现与恢复

- 生成器 `Source/FPSGAME/Dungeons/AuthoredDungeonGenerator.h/.cpp`，独立于已退回的 `DungeonAssembler` 方房生成器。
- `Config/rules.json` 保存数量、连接长度和起始区边界；`build_catalog.py` 生成门洞、占地、静态几何、灯光、伤害积液与后续事件锚点目录。
- `GeneratePreview` 用 `PreviewSeed` 生成并保存编辑器布局；进入游戏默认产生新种子。关卡 URL `?DungeonSeed=92247` 可指定种子复现同一布局。
- 引用目录和所有网格/材质引用保存在生成器 Actor 上，运行时不依赖 Blender、Editor Python 或本机 SourceAssets 路径。
- `LayoutManifestJson` 保存节点、路线归属、相邻门洞与世界变换，场景对象标记 `DungeonModule.<节点号>.<模板>`。后续战斗、路线选择和奖励可按同一图接入；本次保存图位于 `Receipts/installed-layout.json`。
- 新增内容 `/Game/Dungeons/Routes20260922`；粘液复用上一轮倒三角液膜和圆形积液，并将方向性位移/法线转换到世界空间，随房间转向。
- 本轮实现生成/连通与仓库接入，不重新启用退回版本的刷怪、封门、结算和存档流程；战斗/奖励配置通过每个房间已有锚点继续接入。
- 生产顺序：`prepare_modules.py` → Blender `author_modules.py` → 桥 `import_modules.py`、`route_fluid_materials.py` → `build_catalog.py` → 常规 Editor 目标构建并重新加载 → 桥 `install_routes.py`。
- 起始过渡随 `author_modules.py` 制作，在 `integrate_assets.py` 中导入；手工分步导入时另运行 `DungeonDoorTransitions20260922/Scripts/import_transition.py`。已有地图可用该目录 `Scripts/install_transition.py` 局部更新，无需重新排列房间。

未进行 PIE、运行回归或视觉验收；实际地图保存与原生构建记录分别放入 Receipts，最终效果由用户体验。

## 已接入状态

随机地图、红色工具柜与神像起始侧室已接入，起始通道尺寸过渡和宝箱支房也已更新。当前布局种子 92247：前段 4 个房间，三条支路分别 4、5、3 个房间，另有 2 间宝箱支房，共 70 个模块（包含连接件、岔路间和末端开间）。主场景入口标识为 `DUNGEON / Random Routes`。宝箱支房的最新保存记录见 `DungeonTreasure20260922/Receipts/install.json`。

初次接入的历史构建阻塞记录保留在 Receipts。宝箱支房接入阶段已完成常规 Editor 目标构建（`DungeonTreasure20260922/Receipts/build-editor-03.log`），并使用重新加载的原生代码生成和保存地图。未进行游戏测试或视觉验收。
