# 货运仓库与车站表面制作收尾

本批公开货运仓库、维修推车样板、全站墙面与地坪做旧的原创制作脚本、布局参数和地编技能经验。正式测试地图已在本机保存，入口为 `open /Game/GameMaps/Design/L_FreightTransit_Theme_Subject`。原墙地材质、布局和玩法按用户要求保留。

## 当前交付

- 最新增量入口是 `SourceAssets/FreightStationFinal20261113/complete_scene.py`，依次应用 `lighting.py`、`install_walls.py` 和 `install_patina.py`。它针对已具有前期车站资产的地图。
- 55 处浅表饰面替换旧 35 组重复饰面，保留洞口、拱口、维修推车和已认可对侧墙样板。新增饰面无碰撞且不影响导航。
- 对侧暗部调整现有 Light_5、Light_6，光强分别为 5200、4050，范围分别为 1400、1320 cm。对应参数写在 `lighting.py`；本批没有性能采样。
- 墙裙使用 `/Game/SceneTests/FreightOppositePlatform20261113/Meshes/SM_StationTiles_WestRepair`，三段局部颜色／粗糙度做旧层覆盖散乱浅色碎片。三个未采用的整网格复制方案已归档。
- 制作阶段按用户要求输出推车、对侧站台、站厅全景和斜向四组固定机位 UE 实景。最新地图散列为 `A31CFF3E0738905EFFBEBAF8105FBD5574F9FF9EC7D2B064F9001771BCE6DDFC`。用户随后要求阶段收尾和截图归档，画面认可与玩法测试仍由用户完成。

## 制作源与恢复依赖

保留的历史作者脚本用于对应阶段的增量重建，不能按目录日期把全部旧安装器依次重跑。

| 阶段 | 本机制作目录 | 作用 |
| --- | --- | --- |
| 包装区与货架 | FreightWarehouseWeathering20261110、FreightWarehouseEntranceSample20261111、FreightWarehouseDerelictPass20261111 | 杂物、接触积灰、支撑点和稀疏剥落。原墙地已回退到原混凝土 |
| 统一与设计 | FreightStationUnifiedPatina20261111、FreightStationDesign20261112、FreightSurfaceStudy20261112 | 位置语义、概念/布局、擦布、局部混凝土浮雕与推车涂层 |
| 推车样板 | FreightCameraMatch20261113、FreightCartBay20261113、FreightCartUpperWall20261113 | 固定机位、地坪分缝、墙裙厚度、上半墙颗粒 |
| 全站覆盖与对侧修订 | FreightStationSurfaces20261113、FreightOppositePlatform20261113 | 原几何承接面、地坪做旧、固定机位参数、WestRepair 墙裙 |
| 最新收尾 | FreightStationFinal20261113 | 独立墙段图集、错开板缝、三段墙裙做旧和暗部照明 |

以上路径均在 `SourceAssets/`。原创 `.py`、`.ps1`、`.ush` 与选定参数随 Git 发布。原始/派生扫描贴图、FBX、几何采样、UE 包、参考图和密集输入留本机。公开文件清单见 `source-manifest.json`，必要的本机文件及散列见 `local-assets.json`。

恢复当前画面优先从同版本本机或 NAS 内容备份恢复正式地图和 `Content/SceneTests/Freight*` 中的活动资产。`Content` 入口实际联接至 `F:/FPSGAMEData/Content`。相关基础内容还包括 `Dungeons/AtmosphereV2`、`Dungeons/WallUpgrade20260924`、原车站/仓库组件和 `UndergroundTunnel`。

最新表面源需要以下现有本机依赖。

- `FreightStationSurfaces20261113/done-01.json` 是作者输入清单，`panel_layout.py` 会读取它，因此保留。`Geometry/` 和 `FreightStationUnifiedPatina20261111/Geometry/` 提供原表面轮廓。
- `FreightOppositePlatform20261113/bake_surfaces.py` 提供遮罩辅助函数，最终 `ceramic.json.gz` 为局部做旧位置输入。它们不是可丢弃的过程日志。
- `DungeonWallUpgrade20260924/Authored/Textures` 和 `FacilityQuixel20261108/Sources/DamagedConcrete/Textures` 提供已许可扫描。较早阶段的材质辅助读取 `FacilitySurfaceUpgrade20261108/assets.py`。
- Python 作者环境使用 NumPy、SciPy、Pillow、Shapely，FBX 导出脚本在 Blender 中执行，资产导入在本机 UE 5.8 工程中执行。纯 Git 克隆还需恢复以上授权内容与原生 Editor 模块。

## 归档

用户要求将本次冗余、检测截图、GIF 和废案全部放入 `trash`。本批归档根为 `trash/FreightStation20261114/`，沿原项目相对路径保存，包含过程及最终截图、对比图、运行日志、已结束渲染/资产宿主、任务缓存、旧地图快照、明确退役的 `SurfaceRevision2`、失败的墙裙复制方案。

逐文件记录位于归档根的 `archive-manifest.json`，移动计划为 `move-plan.json`，完成回执为 `archive-receipt.json`。记录原路径、目标、大小、SHA-256 和分类原因，移动后读回散列。目录联接只移动对象并记录目标，不遍历或移动其目标。正式地图、共享 Content、当前模型/纹理源、概念/布局/参考图继续保留。原截图链接现应从归档根查找。

公开的 `cleanup-summary.json` 保存归档数量、尺寸、完整本机清单散列和恢复位置。trash 文件不进入 Git，也没有永久删除。

## 发布检查范围

本轮按 `WORKFLOW.md` 第 8 节核对授权远端、分支、待发布提交、精确暂存差异、文件大小、敏感信息和资产许可边界。其他任务的工作文件及暂存内容由原位精确提交保留。整理阶段没有启动 UE、构建、重新截图或玩法测试。

地编经验同步维护在项目与个人 `ue5-pcg-building` 的 `references/dungeon-surface-authoring.md`，覆盖大面积重复控制、真实承接面、墙裙槽索引与局部做旧、同机位对比及隔离宿主依赖。
