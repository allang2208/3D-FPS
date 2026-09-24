# 地牢最终宝箱房（2026-09-23）

用户确认：先支持开箱，具体奖励之后再配置。本次不新增掉落表、背包发奖或额外击杀奖励。

## 布置与外观

- 宝箱房是地下 BOSS 房后方的固定附属空间，约 12 × 10.5 米，与战斗区同层，入口在后墙两根承重柱之间。没有增加远距离连接走廊。
- 沿用地牢的混凝土、破损瓷砖、做旧钢件、顶部服务管线与冷暖灯光。
- 复用装配间机械门的几何和 PBR 材质，派生为固定门框与可升降门体；上方增加空心收纳罩。原装配间的资产路径和功能保留。
- BOSS 后墙的 Shell / Tiles / Frames 使用带真实洞口的独立变体；保留原有二楼平台、楼梯、机械掩体。
- 一个最终宝箱与一个返回基地入口分开放置，避免两者的 E 键交互范围重合。

## 运行逻辑

1. 每次进入随机地牢时，BOSS 模块一并预留宝箱房空间；结构、地板碰撞、机械门、宝箱与返程入口进入既有分阶段加载流程。
2. 战斗前宝箱房机械门关闭，宝箱与返程入口带 `DungeonReward.Locked` 标签。
3. 现有首领控制器确认本次生成的首领生命值归零后，机械门在约 2.8 秒内向上升起 340 厘米。
4. 完全升起后移除门口阻挡，并同时解除宝箱和返回入口的交互锁定。玩家死亡、离场或首领生成失败不会解锁。
5. 对准宝箱按 E，复用既有开箱动画与一次开启状态；当前不发放物品。
6. 靠近返程入口按 E，复用现有地图切换和加载界面，返回 `/Game/GameMaps/DayNight_Lighting`。

## 制作与接入文件

- `SourceAssets/DungeonFinalReward20260923/Scripts/author.py`：Blender 后台制作，输出 14 个网格与源工程。
- `Scripts/import_assets.py`：导入到 `/Game/Dungeons/FinalReward20260923/Meshes`，继承已有材质，保存完整精度碰撞回退网格。
- `Scripts/extend_catalog.py`：在当前目录上追加宝箱房、灯光、宝箱及返程配置。
- `Scripts/install.py`：合并随机地牢地图现有目录，追加资源硬引用并保存；不生成验收预览，不运行游戏。
- `Scripts/install_background.py`：在一个无界面 commandlet 内执行导入和保存。
- `DungeonRouteRepairs20260922/Scripts/extend_catalog.py`：完整落盘后保留最终宝箱房扩展，避免重新生成目录时丢失。
- `Receipts/import.json` / `Receipts/install.json`：分别记录实际导入与地图保存状态；仅脚本存在不代表已接入。

原地图与目录备份位于本任务 `Sources` 目录。运行时根据新目录重新生成；本次不重建地图中旧的编辑器预览。

按用户规则不运行 PIE、回归、截图或渲染验收。实际效果和游玩由用户测试。

## 本次交付状态

- 后台标准构建成功：`Saved/Logs/DungeonFinalReward20260923-build-02.log`。
- 14 个网格实际导入并保存，`Receipts/import.json` 为 `meshes_saved`。
- 随机地牢地图与目录实际保存，`Receipts/install.json` 为 `map_saved`。
- 接入日志：`Saved/Logs/DungeonFinalReward20260923-install-01.log`。
- 未打开 UE 编辑器窗口，未启动游戏或执行验收测试。
