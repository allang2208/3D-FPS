# 旷野建造与地形采集

正式入口为 `scenes/scenic_valley.tscn`。按 B 打开统一建筑面板；按 6/7 直接进入斧/镐采集，F7 返回武器。建筑模式和地形工具互斥，不会让同一次鼠标输入同时放置与挖掘。

`BuildingSystem` 由场景显式注入玩家和 Terrain3D，并使用半米网格、地图安全边界及独立 `.wilderness-building` 旁车。首层构件在坡面按底面多点采样支撑；木、石、大理石、围栏和门继续读取同一构件目录，费用、占格、生命、承重、旋转和存档没有旷野专用副本。挖掘仍承托建筑的地面会被拒绝，需先拆除上方构件。

泥土、石块和矿物进入正式 RPG 背包；体素实验场的填充库存不重复增长。背包已满时不破坏地形。成功采集先写地形，再写背包；任一保存失败都会撤销地形并恢复旧背包，避免资源复制或丢失。

相关回归：`tests/test_wilderness_scene.gd`、`tests/test_wilderness_world.gd`、`tests/test_basic_toolkit.gd`、`tools/sky-base/test_build_history.gd`、`tools/sky-base/test_build_piece_foundation.gd`、`tools/sky-base/test_railing_component.gd`。
