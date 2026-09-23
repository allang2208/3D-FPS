# 随机地牢修复批次

**2026-09-23 Boss 接入更新：** 本文最后的 Boss 暂未启用状态已被后续接入取代。Boss 主泵房资产现已导入，唯一终点与手脑首领的入场战斗配置已保存到随机地图；见 [Boss 接入记录](../DungeonBossIntegration20260923/README.md)。未运行游戏测试。

目标：修复 `DungeonAudit20260922/AUDIT.md` 中的目录合并、门洞净空、导航、宝箱侧门和失败保存边界，并为独立制作的 Boss 大厅接上终端规划。

本批次保留原始起始工作间、仓库和神像样板，不修改两款新房和 Boss 的原始制作文件。墙面继续复用已认可的瓷砖剥落几何、UV 和材质；输出到独立 `/Game/Dungeons/RouteRepairs20260922`。

- 随机战斗房及连接件采用 300×280 cm 接口。Distribution/Drainage 的普通墙体和带宝箱侧门变体一并修正。固定起点入口仍为 132×238 cm，四面封闭过渡至新接口。
- VentilationLoop：北侧和西侧宝箱门；FreightTransfer：低层前厅左右两侧宝箱门。所有候选使用真实墙体变体，只有支房及入口全部放得下才开门。
- 目录合并以 catalog.modules 为唯一列表；完整重建在最后应用本修复层，防止宝箱扩展或房间扩展恢复旧墙体。
- 生成先解析资源，保留旧 Actor；新装配失败清理暂存 Actor，成功再提交。只有 `DungeonAssembly.Ready` 且没有 `DungeonAssembly.Failed` 才允许安装器保存。PendingManifest / PendingDescription 不提前发布。
- 安装时制作 100 cm 的导航模板 Brush；游戏中按本次布局包围范围移动、缩放并通知动态导航。导航准备阶段结束后才释放角色和启动伤害区域。运行时不调用编辑器建 Brush API。
- Boss 作为唯一终端。先预留汇流室、连接段和大厅，再将三条路线接向三个目标入口；可变长直线闭合段与 90° 转角连接件只用于接缝和路线联通，战斗房不缩放。规划失败回溯，不强行放置冲突房间。
- Boss 房不会进入双门普通房池；只在 Boss 独立导入回执为 `meshes_saved` 时启用。制作中时保留现有三个路线末端，不声称 Boss 已接入。

首次制作顺序：`prepare.py` → Blender `author.py` → 经项目桥运行 `import_assets.py`，然后在常规 Editor 构建完成且编辑器已加载新 DLL 后，经桥运行 `install.py`。53 个修复网格与两款新房间的导入已完成，恢复接入直接运行 `install.py`，不要重复制作和导入；旧组合导入、Live Coding、一次性补丁和安装诊断脚本已移至 `trash/dungeon-random-boss-retired-20260923`；保留独立作者、导入与安装入口，命令返回不代表基础 DLL 已更新。

Boss 后续完成导入后，运行本批 `install.py` 或完整目录重建会读取其终端目录并启用汇流规则。未自动监控或后台调度。

本轮按用户规则不启动 PIE、自测、截图或走位验收。构建、导入和保存结果写在 `Receipts`，不等同于实机效果或寻路验证。

2026-09-23 接入记录：已保存 `/Game/GameMaps/L_Dungeon_Randomized`，回执为 `Receipts/install.json` 和 `Receipts/install-20260923-04.txt`。实际房间池为 Distribution、Drainage、ShoredBreach、VentilationLoop、FreightTransfer。固定编辑器种子 92247 的装配结果为起始后 4 间、三条支线 5 / 3 / 5 间、71 个模块、1 个宝箱房；这是此次地图制作结果，不是多种子测试或概率验证。

安装器合并地图现有目录，保存修复接口、固定入口过渡和动态导航模板，并注册两款新房间供后续目录重建使用。安装失败时同时恢复原目录和资源引用，不保存不完整地图。Boss 导入回执尚未齐备，`boss_terminal_enabled` 仍为 false；终端汇流代码已准备，当前地图继续使用原有路线末端。未启动 PIE、运行测试、截图或渲染，由用户测试。
