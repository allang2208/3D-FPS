# 地下车站：随机地牢特殊战斗房

用户已认可扩大后的主体，要求接入随机池并删除独立场景与出征栏显示。本次保留原房间池，加入一个 `AbandonedTransitStation` 完整模块，不扩展尺寸变体、内装配方或重复模板。

## 房间与频率

- 保留主厅 48 × 33 m、拱顶 11.7 m、轨道区宽 10.5 m／深 1.8 m，以及柱脚到门框 0.60 m 的净空。完整房间只做刚体旋转和平移。
- 两处 300 × 280 cm 接口保留真实门洞，端部和侧向入口均可以作为进门。作者米制坐标转换为 UE 厘米时同时反转 Y，并重新排列占位盒 min/max。
- 初始配置在 `SourceAssets/DungeonTransitStation20260928/Config/pool.json`：每局 30% 候选资格、最多一间、限分岔前 `Approach` 主路线。30% 是获得候选资格的概率，不是最终出现率；几何冲突时仍使用其他房间完成布局。
- 候选资格由局种子和模块 ID 独立生成一次，不随布局回溯重抽；数量上限从当前已放置布局计算，回溯不会残留计数。短支路的跨度估算排除不在该路线候选中的车站，不放宽既有连通和碰撞约束。

## 战斗与资源

复用当前 FreightTransfer 的怪物池、等级和品阶，车站初始编成为 4–6 只。`sealed_encounter` 接入已有 `DungeonRoomEncounter` 的进入触发、两个门口封锁、清房解锁和死亡登记；封门选择与精英品阶分开，不因车站封门把普通怪或领主统一改成精英。现有全局刷怪上限继续生效。

12 个刷怪锚点放在站厅和双侧站台。三块 `walk_mask` 限制候选散点，避开中央轨道坑、楼梯及门斗；保留正常楼梯和坑内返回路径。用经过站厅和侧站台的折线路径表达通行长度，避免直线穿过轨道坑来低估路线。

模块包含 20 个主体网格、11 个复用灯具和 1 个配电柜。11 盏点光及 6 盏阴影灯沿用已认可样板参数，并接入现有房间灯调度；提供明确照射范围，避免高位补光被普通小房的默认 3 m 半径截断。网格碰撞、Nanite 和完整回退几何保持现有保存状态。

## 接入与样板退役

`Scripts/extend_catalog.py` 生成单一模块，`Scripts/install_pool.py` 从地图实际生成器读取现行目录，增加车站、依赖硬引用，再保存生成器的包。不会启动布局生成、PIE 或导航测试。后续 RouteRepairs 重建目录末尾重新叠加已安装车站，旧刷怪扩展接受模块自带怪物池，避免下一次重建将新房丢失。

移除 `ColdSteelExpeditionController.cpp` 的车站条目、对应旅行分支，以及 `FPSGAMEGameMode.cpp` 的车站返回传送门生成代码；从地图打包清单移除独立样板。池模块不包含 `SamplePortCaps`、玩家出生点、返回传送门或样板曝光 Volume。

独立关卡和样板封板从 Content 中退役到 `trash/dungeon-transit-station-standalone-20260929`，保留可恢复副本；建模源、实际使用的主体资产和参数继续保留。旧独立地图安装器、入口安装器和草稿移至 `SourceBackup/StandaloneRetired20260929`。今后重导走 `import_assets.py` → `install_pool.py`，不会重新创建独立关卡。

## 交付状态

已完成地图保存、样板退役和正式 Editor 构建：

- `Receipts/pool-install.json` 状态 `map_saved`，现行房池包含原五种与 `AbandonedTransitStation`，生成器外部 Actor 包已保存；后台日志 `Receipts/pool-commandlet-02.log`，退出码 0。
- 独立 `.umap` 和样板封板已从 Content 移除，归档路径、大小及源散列记录在 `Receipts/standalone-retirement.json`；当前出征菜单和原生 GameMode 不再保留车站单独入口／返回门。
- 正式 `FPSGAMEEditor Win64 Development` 构建成功，退出码 0；日志 `Saved/BuildEditor/build-20260929-094449.log`。首次构建因现有后台 commandlet 占用而未开始，未关闭该进程，待其结束后完成。
- 综合回执：`Receipts/pool-delivery.json`。

本轮没有打开编辑器、运行游戏、多种子布局、寻路、战斗、视觉或性能测试；由用户从主场景“地下设施”入口体验。
