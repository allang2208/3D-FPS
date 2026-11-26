# 废弃设施扫描资产写实升级（2026-11-08）

## 本次落盘结果

2026-11-08 后台制作进程退出码为 0，回执 `stage=map_saved`。已保存生产地图外部生成器 Actor、作者目录和布局库。

- 42 个模块中的 35 个具有新增细节；总计 104 处贴花（64 处干湿/锈水痕、40 处混凝土剥落）和 122 件摆件。
- 摆件为 72 组扫描碎块、40 个锈蚀管接头、10 个木制卷盘。以上是模块目录总量，并非每局同时生成的数量。
- 保存 17 个新资产：5 个母材质、9 个材质实例、3 个 Nanite 静态网格；共用已导入的扫描贴图。
- 原有 120 套布局的房间变换与连接保持不变，仅刷新外观合同摘要。
- Transit、Threshold、TreasureLink、BossApproach、StairDrop1080、AbandonedDataArchive、FacilityEntrancePassage 未找到满足本批贴合和空间限制的候选位置，保留原有细节。

完成日志：`SourceAssets/FacilityRealism20261108/Receipts/import-20261108-203726.log`。

## 制作范围

本批使用已导入的 Quixel Leakage、Damaged Concrete、Concrete Rubble、Rusty Pipe Joint、Wooden Cable Reel，为随机地牢制作稀疏、按房间用途区分的表面老化与设备区摆件。

- 潮湿/医疗/生态/泵房采用较深的渗水痕；机电/处理/货运区域使用锈水色，干燥与生活区域采用较淡的干涸痕。
- 水痕从实际墙面上沿下垂，使用扫描颜色和透明度。仅水平裁切/镜像，不把竖直水痕转成横向；投影深度半径 1.2 cm，减少污染邻近设备。
- 混凝土剥落使用配套颜色、法线和粗糙度，在下方搭配少量扫描碎块。未从颜色图伪造高度或几何位移。
- 卷盘放在货运/机电边缘空位，按约 80 cm 的原始尺寸落地；锈蚀管件保持约 20 cm 尺度。三类网格保留原始扫描资产，另建材质和 Nanite 副本。
- 接待大厅已接受的主灯、现有曝光、局部雾、蒸汽、浮尘、已移除的等候区家具不属于本批改写范围。

## 实际接入

- 生产地图：`/Game/GameMaps/L_Dungeon_Randomized`
- 新资产：`/Game/Dungeons/FacilityRealism20261108`
- 原始资产：`/Game/Dungeons/FacilityQuixel20261108`
- 制作脚本：`SourceAssets/FacilityRealism20261108/{assets,place_surfaces,recipe,install}.py`
- 后台入口：`SourceAssets/FacilityRealism20261108/run_background.ps1`
- 保存回执：`SourceAssets/FacilityRealism20261108/Receipts/install.json`
- 最终摆放：`SourceAssets/FacilityRealism20261108/surface-placements.json`
- 修改前备份：回执内 `backup` 路径，包含作者目录、布局库、生产地图及外部 Actor、保存前实际目录。

`install.json` 的 `stage=map_saved` 表示生产地图与作者配置已经落盘；仅有脚本或 `assets_saved` 不代表地图接入完成。数量以该回执为准。

## 制作规则与开销

摆放使用现有网格三角面：贴花矩形取样点必须位于同一实际墙面，摆件的完整占地必须落在同一水平地面，并让开已有几何、容器交互范围、门口、禁摆区。大卷盘额外让开路线折线和遭遇锚点。未找到合适位置时省略，不根据房间整体包围盒强塞道具。

三类扫描网格启用 Nanite、显式切线及完整后备网格；材质声明实例化与 Nanite 用途。碎块和废管无碰撞、不投动态阴影，2600 cm 剔除；卷盘保留阻挡碰撞与阴影，4200 cm 剔除，摆放在通行带之外。继续使用生成器现有实例化与房间剔除机制，不增加 Tick 或物理模拟。

共用原先导入的贴图，运行时最大 2048，保留原始 4K 源文件与流送。新增贴花使用屏幕尺寸淡出阈值 0.018，并按房间设置稀疏数量和近邻间距。以上是成本控制措施，未测量实际帧率提升。

作者目录与地图内目录独立增量修改，保留各自已有字段。布局库只刷新外观合同摘要，不改变布局条目、房间变换、端口、占用格、怪物和任务规则。`DungeonFacilityFlow20261007/extend_catalog.py` 已加入保存回执门控的重建挂钩；几何变化时需重新制作贴合数据。

## 交付边界

本批仅执行后台制作、必要的材质/Nanite 构建与保存。未启动交互编辑器、PIE、游戏、截图、渲染或性能测试。最终光照下的观感、通行和性能由用户进入随机地牢体验。
