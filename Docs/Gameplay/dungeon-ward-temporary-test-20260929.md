# 病区临时测试入口（已退役）

2026-09-29：用户确认测试没有问题，并要求删除此场景、剔除测试。已撤下出征入口、临时返回传送逻辑和打包地图项，移走临时地图、`WardWallArtSubject` 专用类及临时安装脚本，并移除主体安装器的临时模式。正式随机池中的病区和共用 `DungeonWallArt` 逻辑保留。

按工程归档规则，10 个文件保存在 `trash/ward-temporary-test-retired-20260929-231021`，不参与游戏或编译；路径与散列记录见该目录 `manifest.json` 和 `SourceAssets/DungeonIsolationWard20260929/Retirement20260929/retirement.json`。下文为已退役入口的历史制作记录，不代表当前仍有测试入口。

剔除后的正式 Editor 构建已完成：`Saved/BuildEditor/build-20260929-231035.log` 返回 Succeeded。没有额外运行测试或重开编辑器。

用户要求将独立入口临时加回，测试完成后再撤下并删除临时场景。

- 出征条目：`隔离病区 · 临时测试`，ID `isolation_ward_temporary`。
- 临时地图：`/Game/GameMaps/Design/L_IsolationWard_TemporaryTest`。
- 安装入口：`SourceAssets/DungeonIsolationWard20260929/TemporaryTest/install.py`。复用现有主体安装器，通过显式临时模式读取已保存模型、当前家具/血迹配置及正式模块的 `wall_art` 配方，不重导模型、重制材质或修改正式房池。
- 主走廊西侧出生，西门斗提供返回主场景的入口。两端加仅属于测试地图的封口，防止走出有限场景。
- 海报、房号与家具每次进入重新随机；海报使用和正式房池相同的 `DungeonWallArt::Build`，没有复制另一套选样规则。
- 保留放大后的地面血迹、独立玻璃门、玻璃破坏、病床、药车、输液架、长椅及故障灯。
- 本场景用于布景/交互体验，不生成怪物和战斗闸门。正式随机池的低频选择、精英战斗与落闸规则保持原配置。
- 地图保存回执为 `TemporaryTest/install.json`；构建状态另写 `TemporaryTest/build-output.log`。

用户确认测试完成后，移除出征条目、GameMode 对此地图的临时返回入口、MapsToCook 条目，并按工程退役规则归档临时地图和专用 `WardWallArtSubject` 类/安装脚本。保留原房池模块、海报资源、`DungeonWallArt` 共用生成逻辑及制作源。

本轮不代替用户运行测试，不启动 PIE、游戏或验收渲染；编辑器关闭后保持关闭。

已完成落盘：正式构建 `Saved/BuildEditor/build-20260929-225016.log` 返回 Succeeded；后台安装回执 `TemporaryTest/install.json` 为 `sample_map_saved`，包含 12 扇独立玻璃门叶、10 块观察窗、13 组长椅、当前随机海报及 2.5 倍地面血迹。没有运行游戏。
