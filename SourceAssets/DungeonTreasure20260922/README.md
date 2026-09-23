# 随机地牢宝箱支房

- 室内主墙之间净尺寸 10 × 10 m，高 3.45 m，只有一个 3 m 宽、2.8 m 高的入口。中央放置现有仪式宝箱，暖光集中在箱体，四周保留绕行空间。
- 每个普通房间独立进行一次 10% 概率抽取，每房最多连接一间宝箱房。起始区、岔路间、连接通道和末端不参与抽取。
- 三种普通房间各有两处侧门候选；成功概率判定后依次尝试候选位置。两米门厅和完整宝箱房与主路线、既有支房和起始区同时计算占地，全部放得下才启用开门墙体变体。没有合适空间时跳过，因此最终出现率可能低于 10%。
- 宝箱房为侧路，不占用主路线每组 3～5 间的数量，也不会从宝箱房继续递归生成支房。房间图和灯光连通图只添加已成功连接的侧门。
- 房间的瓷砖破损继续使用原通道母版与相同表面种子；只有接入宝箱房的父房间才切换对应 Shell/Tiles/Frames，其余部件和未选中房间保持原模板。
- 中央箱体使用现有宝箱模型、材质和关闭姿态，独立标记 `DungeonTreasureChest`。本轮不复用仓库库存，不实现开箱掉落；后续奖励系统可使用房间中心 `treasure_chest` 锚点。

生产入口：`prepare_treasure.py` → Blender `author_treasure.py` → UE 桥 `import_treasure.py` → 原生必要编译 → UE 桥 `install_treasure.py`。概率在 `DungeonRoutes20260922/Config/rules.json` 的 `treasure_chance_per_room` 中配置；运行时随目录保存在生成器 Actor 中，不依赖本机 SourceAssets。

本轮未运行游戏测试或验收渲染。实际编译和接入状态以 Receipts 为准。

常规 `FPSGAMEEditor Win64 Development` 构建已完成，记录为 `Receipts/build-editor-03.log`；31 个新网格已导入保存，记录为 `Receipts/import-01.txt`。地图保存结果另见 `Receipts/install.json`。

当前地图已接入保存：预览种子 92247 保留前段 4 间、支路 4／5／3 间的主结构，另成功放置 2 间宝箱支房，总计 70 个模块。此为生产生成与地图保存记录，不是运行或视觉验收。
