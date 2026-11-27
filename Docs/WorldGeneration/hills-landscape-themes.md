# 丘陵景观与道路景观

FPSGAME 丘陵地图的构建与修改以这两个主题为单位。制作入口按中文主题名定位。需求提到路肩、泥路、采石场进场路或落叶时归入道路景观；山形、林内生态和蓄水洼地归入丘陵景观。明确要求联动或共享边界发生变化时，说明两个主题需要更新的部分。

| 主题 | 正式图和关卡组件 | 负责的内容 |
|---|---|---|
| **丘陵景观** | [PCG_HillsLandscape](../../Content/ForestPathStudy/VillageRegion/Themes/PCG_HillsLandscape.uasset) · `SurroundingForestPCG` | 丘陵高度场、地表草被、林内植被与岩石枯木、湿地和岸草、林雾。可采伐树木继续由原玩法系统管理。 |
| **道路景观** | [PCG_RoadLandscape](../../Content/ForestPathStudy/VillageRegion/Themes/PCG_RoadLandscape.uasset) · `RoadLandscapePCG` | 东门林道和采石场道路、B full 泥路、路肩侵草和落叶、道路带内的普通生态落点，以及沿路配方选中的倒木和松枝。 |

两张图同时装配在正式关卡 `/Game/GameMaps/L_ForestPathVillage` 的同一个区域 Actor 上。各自的 PCG 组件持有生成与清理资源。原七个生态层和 R30 组合仍可在编辑器中打开：每个生态层现在汇集两主题对应的子图。全生态主图用于一次查看完整组合；正式关卡已由两个主题组件承担布置。将全生态主图额外挂到同一区域会重复布置。

## 归属与共享数据

- 普通生态点用原始落点坐标对照两条中心线。13.3 米以内归道路，这是原路肩过渡带的外沿；其余归丘陵。R29 新增倒木、松枝、木桩按实际生成来源归属，沿路批次和林内批次各有独立点集。水坑及其岸边莎草归丘陵。
- 高度、既有树干、水岸、路床和保护区可被两边读取。同一种网格或材质可由两主题引用，每个烘焙落点只交给一个主题。道路地表和落叶仍渲染在现有地表上。村庄玩法、角色、存档与昼夜天气仍使用项目原有系统。
- 改路面配色、落叶图集或林雾时，只运行对应材质或天气配方。移动整条路线、改变路床或水岸时，高度、碰撞、边界归属和依附物需要同步；此类操作按跨主题改动登记。丘陵近草与全图草皮有独立流送/材质入口，路肩的形状改动可能涉及它们共用的遮罩。

## 按主题操作

[主题注册表](../../Tools/WorldGeneration/ForestVillage/landscape_themes.json) 保存中文名称、负责范围、读取的共享数据、图路径和制作入口。两个主题的可编辑点集分别在 [丘陵景观](../../SourceAssets/HillsForestPathThemes/HillsLandscape) 和 [道路景观](../../SourceAssets/HillsForestPathThemes/RoadLandscape)，各自包含 `theme.json`、`theme.id`、`planting.bin` 和素材顺序表。文件中的记录数是生成输入，水坑、水边依附和倒木支撑筛选由各自的构建步骤处理。

在隔离制作用宿主中使用 [landscape_themes.py](../../Tools/WorldGeneration/ForestVillage/landscape_themes.py)。编辑器 Python 已加入项目 `Tools/WorldGeneration/ForestVillage` 路径时，可以这样调用：

```python
import landscape_themes as themes

themes.preset("丘陵景观")       # 查看配置和实际配方入口
themes.build("道路景观")        # 只清理、重建道路组件并保存关卡
```

把中文名换成 `丘陵景观` 即可单独重建丘陵 PCG。后台脚本可设置 `FPS_LANDSCAPE_THEME` 为中文主题名后执行同一入口。默认从项目 `SourceAssets/HillsForestPathThemes` 读取正式点集；隔离工作副本可设置 `FPS_FOREST_THEMES_SOURCE`。需要重建两边时，显式调用 `themes.build_all()`，它使用各自最新的主题点集并统一保存关卡。

修改原散布算法后，可使用 [点集分配工具](../../Tools/WorldGeneration/ForestVillage/landscape_theme_points.py) 将新生成的组合输入拆到工作目录。命令参数依次为组合点集目录、含两条道路 CSV 的地形目录、输出目录；加 `--theme 道路景观` 或 `--theme 丘陵景观` 时只写指定主题。用 `themes.build("道路景观", source=该主题的工作目录)` 接入，再随发布回执保存改过的主题源。全量烘焙读取 `planting.roadbits`，其摘要与具体的 `planting.bin` 绑定；历史无标记输入可按既有路面涂层回退。素材池和各层分页仍遵循[七个生态层的组合规则](forest-village-ecology.md)。

[地图与主题图发布清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/LandscapeThemes-R31/published.json) · [主题制作源](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/LandscapeThemes-R31) · [上版文件](F:/FPSGAMEData/ArtProduction/HillsForestPath/LandscapeThemes-R31/Before)

## R32 村庄黄土与山脚

村内土地、墙脚高度和外围山形归 **丘陵景观**。高度源为 `VillageLoessFoothills-R32`。地形配方读取 R28 的参考地表和水坑、村墙布局、ChapelEarth 高度扫描。重新整地时应重建外围地块的碰撞，并使用两个主题各自保存的点集更新贴地位置；单改道路外观继续使用道路景观入口。两个主题共享路心和水岸的标高。[高度源、对照图与正式包恢复清单](../Production/HillsForestPathStudy.md#village-loess-r32)

R33 将村内黄土地表、东门马厩贴花衔接与墙外近草放在 **丘陵景观** 的 `village_finish_source` 下。整地重建继续使用 R32 高度场入口。重绘墙边时使用 `village_wall_grass.py` 基于已登记的原近草掩膜生成，只更新实际墙外的近草；林道与采石场路面继续由 **道路景观** 管理。[实际效果、包名与恢复记录](../Production/HillsForestPathStudy.md#village-loess-review-r33)

## 道路景观的落叶边缘

使用道路主题的 `leaf_scans` 作为输入、丘陵主题登记的高度场作为地形、道路主题的 `leaf_source` 作为输出，运行 `prepare_forest_litter.py <扫描目录> <地形目录> <输出目录> --leaves-only`，随后运行 `author_roadside_leaves.install(输出目录)`。这两个入口只更新落叶分布图、图集和两个地表材质。独立调整现有坡面苔斑或泥斑时，`refit_forest_floor_decals.refit(world,region,['HillsLandscape'])` 或 `['RoadLandscape']` 可按主题回写已有点表及关卡演员。常规 PCG 烘焙直接使用相同的地表投影算法。[R34 实景与恢复记录](../Production/HillsForestPathStudy.md#road-leaf-edges-r34)

## 丘陵与道路的陡坡露岩

R35 的共享高度场位于 `CliffExposure-R35/region.i16`。路心、路肩和切坡方向沿用道路主题的两条中心线，丘陵主题维护自然山面、水岸和村庄保护区。运行 `prepare_cliff_exposure.py <VillageLoessFoothills-R32> <CliffExposure-R35>` 生成高程、覆盖图和岩架点，再运行 `author_cliff_exposure.install()` 写回地形与两个主题的贴地实例。一般的 `themes.build("丘陵景观")` 或 `themes.build("道路景观")` 会复用地图中保存的本主题岩架点。只调岩面随机拼接时重编两个地表材质，沿用既有高程和落点。[制作配方及实景](../Production/HillsForestPathStudy.md#cliff-exposure-r35)

## 岩壁、岩架、坡脚碎石的分工

- **地形和地表材质**共享 R35 高度场、独立 Landscape 编辑层和岩面权重。调整露岩阈值、地形位移或岩面随机拼接时使用丘陵主题登记的地形与材质入口。
- **岩石与碎石（Rocks）**在丘陵与道路主题各有一份图。除了既有石块，两边的图均可组合苔岩架、裸岩架、坡脚细碎石（`TalusFine`）和断片（`TalusFragment`）。碎石按最终落点距两条路的中心线是否在 13.3 米以内分配。两种规格分别在 21–28 米和 31.5–42 米淡出。
- 露岩退草由 **Grass** 和近草掩膜负责；苔斑、泥斑归 **Floor**，路肩落叶仍由地表材质绘制。乔木、灌木、枯枝倒木分别由 **Trees、Shrubs、Deadwood** 管理，水坑与岸草由丘陵的 **Wetland** 子图管理。两个主题的 `layers` 条目保存实际图路径和各自职责。

正常重建调用 `themes.build("丘陵景观")` 或 `themes.build("道路景观")`，读取所选主题已保存的坡脚碎石点。两组点源分别位于 `CliffTalus-R36/HillsLandscape/Rocks` 和 `CliffTalus-R36/RoadLandscape/Rocks`。重新整地后，`author_cliff_exposure.install()` 会从新高程重新计算堆积区。只修改一个主题的碎石分布可调用 `author_cliff_talus.install("道路景观")` 或 `author_cliff_talus.install("丘陵景观")`，仅覆写所选主题的源文件与点集。两个主题一起更新时调用 `author_cliff_talus.install()`。[发布与恢复](../Production/HillsForestPathStudy.md#cliff-talus-r36)

## R39 枯木支撑与林内大块浅色苔岩

两个主题的 Deadwood 均使用木料原网格底部和最终三角地面。沿主轴取五段，每段按横向分三处求支撑，木桩、长木和细枝按自身厚度入土。木身另取样限制埋深。样板两款细枝也进入同一烘焙流程，原有倒木候选筛选与两主题点集继续提供密度、XY 和变体。[支点测量和入土](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/WorldGeneration/ForestWoodDressing.cpp)

丘陵景观的 Rocks 从参考林地之外、已有宽度至少 1.3 米的林内石位中选取代表点。按位置种子排序，同批相隔至少 48 米，用原位置的尺寸一对一换成样板里的 `wc1kedt`、`rgAsy` 或 `rgfoh`。三款复用样板实际绑定的扫描材质，使用 Rocks 的 HISM 和距离剔除。道路主题、水岸碎石和原参考镜头各自保留归属。[岩石选择与落地](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/WorldGeneration/ForestReferenceBoulders.cpp)

R39 隔离图烘焙与接触测量已完成。准备写回的包、原包哈希及隔离 DLL 见[制作回执](F:/FPSGAMEData/ArtProduction/HillsForestPath/WoodBoulders-R39/prepared.json)，逐素材数量与地面接触数据见[检查记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/WoodBoulders-R39/contacts.json)。

**R40 隔离候选**恢复了两款旧参考细枝原来的 75–100 米淡出距离，并移除烘焙时重复的几何读取。抽样木件与大石变换和 R39 相同。[R40 隔离包清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/VillageGateF6-R40/prepared.json) · [地编与城门性能复查](forest-village-f6-town-gate.md)

<a id="soil-wood-r41"></a>

## R41 移除带泥土和松针底座的木料

正式地图已合入 R40 的贴地与苔岩改动，并重烘丘陵、道路主题的 Deadwood 层。以扫描模型自带大片连续泥土或松针底座为选取条件。清理 9 款 PCG 扫描，共 724 个已生成实例。原样板和正式林道子关卡各移除 1 个单独摆放的同类树桩。10 个静态网格包合计 7,511,334 字节，已从正式 Content 删除。[模型外观对照](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/ForestSoilMeshes-R41/retired-and-retained.jpg) · [精确包名](../../Config/ForestVillageRetiredWood.txt)

- 带土倒木和倒松为 `rgzoN`、`rgtah`、`rfgxx`、`rfixH`，带土松枝为 `rfEcM`、`rfnth`，苔木段为 `rhfdj`，树桩为 `rgtan`、`ti3mdirda` 和样板的 `tg0qedqda`。
- 保留两款独立倒木 `wd1mbcvbw`、`wgyvfinaw`，独立木段 `pcwa5` 以及细枝 `relu7`、`rioqm`。丘陵和道路主题仍按各自点集生成，已落盘的 136 处外围浅色苔岩继续归 Rocks。
- 导入和点集准备共用退役包名。更新点集时按原槽号映射保留项，重排扩展槽时保持其坐标、朝向、缩放和所属主题。编辑器烘焙旧点集会跳过退役槽。恢复旧快照时按本批清单处理，旧 R39、R40 资产只作历史对照。

每个删除文件的相对路径、大小和 SHA-256、32 个写回包的哈希及制作输入均有记录。删除前的模型和地图在本批 `Before/Content` 下。[发布与恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestSoilMeshes-R41/published.json)

## 城内道路与屋间空地的实际高程

2026-11-25 的城内调整沿用正式地图 `L_ForestPathVillage` 的 119 × 146 个一米采样点。`SettlementOffsets` 继续保存整地基底，运行时在同一格点叠加以厘米计的道路和空地高差。路面长缓起伏配合横向路拱，空地沿实测地形的连续脊线和浅洼起伏。固定构件接触面外 1.42 米以内保留原高程，接下来的 3.15 米逐渐接入。修复前后的村庄使用同一套避让。草、碎石和地表查询沿用渲染与碰撞的三角网格。外墙和城门平顺接回现有标高。

重新制作时，以正式子关卡运行 `export_village_relief.py`，设置 `FPS_VILLAGE_CONTACTS_ONLY=1` 和 `FPS_VILLAGE_RELIEF_SOURCE` 导出落地边界。随后执行 `prepare_village_street_relief.py <基底目录> <实测 reference.f32> <contacts.json> <输出目录>` 并编译 `FPSGAMEEditor`。本版基底为 CliffExposure-R35 的 settlement.i16，实测原件沿用 VillageGroundRelief-R11；生成的附加高差只叠加一次。[生成记录与高度图](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageStreetRelief-20261125/generation.json) · [入口、构建与恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/VillageStreetRelief-20261125/published.json)。

## 村内 Forest Floor 地表斑块

教堂院内选较宽的斑块，路肩两侧按各自的里程抽样，围墙按墙段实际长度选择落点。密度、走向、长短轴分别变化，沿边缘混入三个尺度的扰动和小块裸土。建筑、门槛、墓位、重要作业面及道路中心使用退让场。种子只在离线制作阶段使用，正式图从村庄局部坐标采样同一张权重图。

权重图 R 为覆盖，G/B 为扫描裁剪偏移，A 为旋转。每个连通斑块采用项目现有 Forest Floor 颜色、法线及 ARH，基准尺度 2 米，线性 R/G/B 分别为 AO、粗糙度和微高度。仅在村庄泥路材质的已启用分支合成，斑块外跳过林床扫描。近处用微高度微调采样位置和混合边缘，并沿用天气湿润度。

重新制作使用 `prepare_village_forest_floor.py <输出目录> <contacts.json> --seed 251143`，再用 `author_village_forest_floor.install()` 导入并编译村庄地表。落地接触取正式村庄子关卡。[可编辑遮罩与生成记录](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageForestFloorPatches-20261125/generation.json) · [包与恢复记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/VillageForestFloorPatches-20261125/published.json)。

迁址枪店和扩建马厩的高度与草斑制作源已切到 VillageDeliveryAudit-20261125。新地基先消除旧林道高程的残余偏移，再接回周边地面。参见[村庄交付及主客机复查](village-delivery-review-20261125.md)。


<a id="shrine-shrubs-r43"></a>

## R43 村庄女神像旁灌木接入森林

丘陵景观的 Shrubs 层新增 21,511 株，原有两款榛灌木 21,511 株继续保留，该主题的灌木合计 43,022 株。新落点覆盖 254 个 64 米地块，其中 6,825 株位于正式地图的原参考林地范围，14,686 株位于外围。三组分别为 Normandy PlantTypeA 9,939 株、PlantTypeB 7,687 株、PlantTypeC 3,885 株，每组三款。较少的紫红叶用于点缀。叶片沿用女神像附近实际实例的覆盖材质，树皮沿用各自网格的树皮槽。

单独运行 `landscape_themes.build("丘陵景观")` 即可重建。烘焙从现有适生低草位置选点，仅保留林冠周围的候选，按世界坐标种子、斑块噪声和间距形成疏密变化。村庄地基、泥路、水岸、露岩和陡坡设有筛选。根部按最终地面取样下沉，打包后使用已保存的 PCG 数据页和实例。新增灌木的风动位移在 25 米关停，配置 75–100 米淡出，不启用碰撞、投影和光追。此次未进行新的 F6 帧耗采样。[放置配方](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/WorldGeneration/ForestCourtyardShrubs.cpp) · [实地网格与材质来源](F:/FPSGAMEData/ArtProduction/HillsForestPath/ShrineForestShrubs-R43/donors.json) · [分变体烘焙计数](F:/FPSGAMEData/ArtProduction/HillsForestPath/ShrineForestShrubs-R43/baked.json) · [正式包与恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/ShrineForestShrubs-R43/published.json)
<a id="hills-shadow-geometry-r44"></a>

## R44 丘陵地形和村庄静态模型的 Nanite 阴影

正式林图的 55 块外围地形和 55 款村庄设施、建筑与神像用刚体已构建 Nanite 数据。正式林道子关卡内的 Landscape 也已从 64 个原地形组件生成 Nanite 表示。制作范围包括瓦顶、教堂地基及墙体、五款神像、铁匠铺烟囱与楼板、风车和马厩等。独立林道样板仍使用自己的地形设置。[逐件网格与材质清单](../../Tools/WorldGeneration/ForestVillage/shadow_geometry.json)

外围网格把原始 UV4 的道路与路肩权重逐顶点复制到 UV3。专属实例 `MI_ForestTilePacked` 继承现有林地地表，启用 `UsePackedForestTileUV` 后读取四套 UV 范围内的数据。原始 UV4、地形顶点及独立的村内 UV5 分支继续可用。地形生成器同步写入两套权重，地块统一采用 0.25 厘米位置精度。碰撞沿用每个网格原来的配置，回退网格保留完整三角形。[地块构建](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/WorldGeneration/ForestVillageRegion.cpp) · [Nanite 构建](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/WorldGeneration/ForestNaniteAuthoring.cpp)

重导入上述资产后，可在制作宿主使用 `author_shadow_geometry.install()` 重新生成。编辑正式林道的岩壁高度层时，同步更新其 Landscape Nanite 表示。林下低草、铺展草和高草使用既有 LOD 和无投影实例；水面、透明材质和随修复状态改形的村内动态地面继续使用原渲染路径。[制作入口](../../Tools/WorldGeneration/ForestVillage/author_shadow_geometry.py) · [构建数据与道路权重读回](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsShadowGeometry-R44/readback.json) · [正式包哈希与恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsShadowGeometry-R44/published.json)

DX12 在后台按静态网格的默认材质槽实际检查了渲染代理资格，正式保留的 110 款全部通过。铸造台的淬火水槽使用 SingleLayerWater 着色，恢复原网格后继续走传统渲染。此批没有重新试玩或记录改动后同路线的溢出次数、显存及帧耗。[逐件处理与保留原因](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsShadowGeometry-R44/asset-inventory.json) · [DX12 代理检查](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsShadowGeometry-R44/dx12.json)

干草车、跳栏、鞍架和马具架以马厩最新交付的网格与材质为准。它们的导入流程在绑定材质、导入 LOD 和设置碰撞后，按同一份清单构建 Nanite。铁匠铺烟囱与马厩地面使用的组件覆盖材质也通过 DX12 代理检查。[马厩导入入口](../Publication/HillsForestLandscape20261126/Integration/index.json) · [组件覆盖材质检查](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsShadowGeometry-R44/overrides.json)

<a id="forest-road-mix-r45"></a>

## R45 村外道路的扫描材质混合

道路景观的 `B full` 使用原有泥路、两种 Stony Soil 和 Soil Tire Tracks。两种碎石土分别以 0.39 米为一张，车辙以 2.7 米为一张。连续的随机权重决定哪一块露出旧泥土或碎石，纹理按各自的实物尺度取样。采石场附近的粗料权重较高。车辙沿两条中心线截取，随机改变间隔、偏转角和边缘缺口。城内地面、水坑和采石作业面使用各自的保护掩膜。

重建时将 `ForestRoadMix-R45`、`CliffExposure-R35`、`GateRoadSurface-R25` 三个制作源目录依次传入 [地表准备脚本](../../Tools/WorldGeneration/ForestVillage/prepare_forest_road_mix.py)。再在制作宿主调用 [author_forest_road_mix.install](../../Tools/WorldGeneration/ForestVillage/author_forest_road_mix.py)，传入 R45 制作源和批次目录。它把纹理写入 `/Game/ForestPathStudy/VillageRegion/Reference/GateRoad/RoadMix`，并更新地形与外围网格共用的 `MF_TrailDirt`。只改道路材质时复用现有地形、道路点集和路肩落叶。更改路线时，用新中心线同步烘焙旧路面权重与 R45 分布图。[扫描原件与车辙点位](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/ForestRoadMix-R45/road-mix.json) · [发布包与改前版本](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestRoadMix-R45/published.json)

<a id="hills-nanite-streaming-r46"></a>

## R46 正式林图复用旧丘陵的流送和显示预算

正式林图与旧图共享带引用计数的 PCG、异步加载和关卡组件注册预算。进入后这三项分别请求 2、2、2 ms，已有更高优先级的设置以实际生效值为准。林图也使用居民外观顺序加载队列。完整预载在村庄可见后分帧查看已注册组件的渲染管线请求，快速进入和专用服务器沿用各自的就绪条件。六款家具、马具及酒桶复用原有中型店铺道具 55 米剔除上限。[旧图与正式林图共用的流送预算](../../Source/FPSGAME/WorldGeneration/TemperateHillsStreaming.cpp) · [林图进入流程](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/WorldGeneration/ForestVillage.cpp) · [材质与回退网格发布清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestNaniteStreaming-R46/published.json)

后台已为日志列出的 9 个材质补齐 Nanite 用途并编译 SM6。4 款使用简单碰撞的高面数道具沿用风车装饰件的 35% 回退网格目标，回退 LOD0 合计 154,686 → 54,138 个三角形。Nanite 主几何、角色碰撞和地形接缝精度沿用原方案。工程有独立的光追代理，回退网格面数不能直接折算为光追或整帧收益。两张春草纹理的正式包哈希与 R42 回执相符。最近一次改前试玩日志中，进程累计报告 100 次 PSO 创建卡顿；已有两份城镇与城门 F6 早于 R44。改后帧时间待实机采样。[场景剔除配方](../../Source/FPSGAME/WorldGeneration/VillageExteriorDetail.cpp) · [几何制作设置](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/WorldGeneration/ForestNaniteAuthoring.cpp) · [本地版本](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestNaniteStreaming-R46)

<a id="hills-perf-opt-r50"></a>

## R50 丘陵 GPU / VSM / 显存性能优化（`HillsPerfOpt-R50`）

- **实测基线（2026-11-26，用户 F6 导出 `UEDPIE_0_L_ForestPathVillage` `2552×1218` DX12 夜战东门视角）**：
  - 导出 1（90 帧）：`window_fps = 8.97`，`frame` P50 `128.93 ms`（P95 `192.62 ms`），`gpu0` P50 `131.58 ms`，`draw` P50 `131.37 ms`，`game` P50 `19.73 ms`，`rhi` P95 `107.23 ms`，本地显存 `11,365 / 11,061 MiB`（超预算 `+304 MiB`）。
  - 导出 2（69 帧 + `engine.utrace` 128 帧）：`window_fps = 6.80`，`frame` P50 `144.25 ms`（均值 `147.08 ms`），`gpu0` P50 `141.24 ms`（均值 `144.98 ms`），`draw` P50 `143.90 ms`（RenderThread 自身 CPU 仅约 `5.7 ms`，约 `134.4 ms` 在等待 GPU 遮挡查询），本地显存 `11,384 / 11,076 MiB`（超预算 `+305 MiB`）。
- **已落地优化（保留光线追踪、Lumen、VSM、草密、法线/视差与昼夜外观）**：
  - **Pass A — 关闭丘陵地形 Nanite 曲面细分**：`engine.utrace` 显示 `ShadowDepths -> RenderVirtualShadowMaps` 均值 `75.74 ms`、`Nanite::VisBuffer` 均值 `47.64 ms`，其中 `PatchSplit` 后的 `SW Rasterize (Patches)`（`FMicropolyRasterizeCS`）合计占用约 `100–115 ms/frame`。对 5 张继承 Sensei 细分设置的地形主材质（`M_ForestReferenceMesh`、`M_ForestVillageLandscape`、`M_ForestVillageFringe`、`M_ForestPathRoadVerge`、`M_EastRoad_Sensei`，原 `displacement_scaling={magnitude: 1.0, center: 0.5}`）设置 `bEnableTessellation=False` 并重编译保存（保留 `bUsedWithNanite=True`、R48 顶点微起伏、法线与视差）；同步修改 [author_reference_surface.py](../../Tools/WorldGeneration/ForestVillage/author_reference_surface.py)、[author_trail_cover_materials.py](../../Tools/WorldGeneration/ForestVillage/author_trail_cover_materials.py)、[author_surface.py](../../Tools/WorldGeneration/EastRiverRoad/author_surface.py)。只读核查 `ForestSpecies20261110` 4 份树材实例母版 `M_ForestPCG` 已为 `enable_tessellation=False`。
  - **VSM 静态缓存步进节流**：[FPSUDSBridgeComponent.cpp](../../Source/FPSGAME/FPSUDSBridgeComponent.cpp) 的 `ApplyClock()` 原每帧按 `0.01f` 单位更新 UDS `Time Of Day`，导致 `Moon` 方向光逐帧微旋、121/128 帧出现 `PagesAllocatedNew=591..609` 全量失效（命中缓存的 7 帧 `ShadowDepths` 仅 `4.6–6.2 ms`）。新增 `fps.UDS.SkyClockStepUnits`（默认 `0.5f` ≈ `0.45 s` 步进 / 约 `0.075°` 太阳角步长，保持 `AFPSWeatherManager::NormalizedDayTime` 连续不变）供按需调参。`FPSUDSBridgeComponent.cpp.obj`（19:07）及含该 CVar 的 `UnrealEditor-FPSGAME.dll`（19:33）已由后台编译落盘；未修改并发任务的 `VillageSiegeUpgrades.h` / `VillageHotOil.cpp`。
  - **Pass B — 漏控 8K/4K 贴图封顶（共 91 张已保存）**：修复 [optimize_hills_perf_r48b.py](../../Tools/WorldGeneration/ForestVillage/optimize_hills_perf_r48b.py) 中 `"mask"` 关键词误跳 `CommonHazel`/`EuropeanHornbeam` 8K 遮罩的缺陷并同步 [author_spring_grass_mips.py](../../Tools/WorldGeneration/ForestVillage/author_spring_grass_mips.py)；在 [optimize_hills_perf_r50.py](../../Tools/WorldGeneration/ForestVillage/optimize_hills_perf_r50.py) 中封顶 `springGrass_Albedo_8k_I / springGrass_Normal_springGrass_8k`（`2048`）与 `springGrass_Opacity_8k`（`4096`，保留 R42 覆盖率 Mip）、`T_rbpir / T_rbcuh`（`1024`）、`T_ForestFloor_* / Combined_Flowers_* / Foilage_Ground_Main_* / T_tjtjfinia`（`2048`）、9 张 8K 乔木遮罩（`TwoSided 2048 / 其余 1024`）及 69 张 `UnrealNormandy` 4K 贴图（`T_PlantTypeA/B/C_*` 封顶 `1024`，4K `Normal/RHAOM` 封顶 `2048`，跳过 `height/cloud/lookup/mask` 等数据图）。
  - **Pass C — 修复 5 项 ISM 材质使用标记**：`M_Baguette`、`M_Bread`、`M_TreasureV3_Gold/Iron/Wood` 启用 `bUsedWithInstancedStaticMeshes=True` 并重编译保存。
- **落盘与恢复**：`101` 份改动前 `.uasset` 及改动前 C++ 源码已按 SHA-256 备份至 `F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOpt-R50/Before/`，逐项校验写入 [published.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOpt-R50/published.json)（`待 NAS 归档 · 未实机测试，待实机进入 L_ForestPathVillage 同机位 F6 复测对比`；若并发 `LumberMill-R49` 后续从隔离区覆盖地形主材质，可幂等重跑 `optimize_hills_perf_r50.py`）。

<a id="hills-perf-opt-r52"></a>

## R52 丘陵着色器 / 草 WPO / 显存与第一人称发丝/UI 专项优化（`HillsPerfOpt-R52`）

- **R50 后实测基线与剩余瓶颈（2026-11-26，用户 F6 导出 `performance-20261126-132514` + `engine.utrace` 794 帧 @ `2552×1218`）**：
  - **R50 已验证收益**：GPU 从 R50 前 `~145 ms` 降至 **`33.69 ms` 均值**（`frame = 38.15 ms` 均值 / **`26.21 FPS`**，P50 `36.13 ms`）；`Nanite::VisBuffer` `47.64 → 4.19 ms`，`VSM Nanite` `75.74 → 4.65 ms`。
  - **剩余关键瓶颈**：`BasePass = 8.32 ms`（`NaniteBasePass = 6.85 ms`，`M_ForestReferenceMesh` `2,248` PS 指令 / `18` 采样器因未对非道路像素短路仍执行 `MF_TrailDirt`）；`RenderVelocities = 1.91 ms`（非 Nanite 草未设 WPO 禁用距离）；`Hair = 1.32 ms` + `NiagaraGpuComputeDispatch = 1.23 ms`（占 `399 MiB` `Hair.VoxelPageTexture`）；`GameThread = 20.10 ms`（`ColdSteelHUDWidget_Tick = 1.61 ms`、`Slate_PaintSlowPath = 2.69 ms`、`FPSArmJointCorrectiveComponent = 0.89 ms`、`VillageSiegeEngine = 0.44 ms`）；本地显存末段 `11,545 / 11,508 MiB`（`+37 MiB` 溢出）。
- **C++ 运行时优化（方案 B + 丘陵运行时，已编入 `FPSGAMEEditor Win64 Development`，`BUILD_EXIT=0`）**：
  - **直接关闭本地第一人称发丝计算（全图通用，按用户拍板）**：[FPSPlayerBodyAppearance.cpp](../../Source/FPSGAME/Characters/FPSPlayerBodyAppearance.cpp) 新增 `fps.body.FirstPersonHideGrooms`（默认 `1`，实时回调同步），本地第一人称隐藏 `HeadGrooms`、清除 `CastShadow / bCastHiddenShadow / bVisibleInRayTracing`、关闭 Groom Tick 并对每个 Groom Group 调用 `GetNiagaraComponent(Group)->DeactivateImmediate()` 停用发丝 Niagara 仿真；切回第三人称自动恢复可见、重激活 Niagara 并调用 `ResetSimulation()`，远端玩家不受影响。
  - **草与植被 WPO 距离收紧**：[ForestVillageGrassCover.cpp](../../Source/FPSGAME/WorldGeneration/ForestVillageGrassCover.cpp) 设置 `WorldPositionOffsetDisableDistance = 2600`（覆盖 `GrassDeform` 24 m 变形窗 + 2 m 裕量）；[ForestVillageRegionPCG.cpp](../../Source/FPSGAME/WorldGeneration/ForestVillageRegionPCG.cpp) 按层级收紧至 `2200–3500 cm`。
  - **Warmup / 攻城探测 / 骨骼纠偏 / HUD 缓存优化**：[TemperateHillsStreamingPreparation.cpp](../../Source/FPSGAME/WorldGeneration/TemperateHillsStreamingPreparation.cpp) 关闭 Warmup 组件阴影与动态 GI；[VillageSiegeEngine.cpp](../../Source/FPSGAME/WorldGeneration/VillageSiegeEngine.cpp) 新增 `0.35 s` 每世界 `CachedThreatCandidates` 零敌军早退（跳过 `OverlapMultiByObjectType`）；[FPSArmJointCorrectiveComponent.cpp](../../Source/FPSGAME/Characters/FPSArmJointCorrectiveComponent.cpp) 增加 `Rescan` 状态判等、Morph 权重缓存与 `0.05°` 姿态死区；[ColdSteelHUDWidget.cpp](../../Source/FPSGAME/UI/ColdSteelHUDWidget.cpp) · [ColdSteelQuickSlot.cpp](../../Source/FPSGAME/UI/ColdSteelQuickSlot.cpp) · [ColdSteelTopVitals.cpp](../../Source/FPSGAME/UI/ColdSteelTopVitals.cpp) · [ColdSteelAmmoReadout.cpp](../../Source/FPSGAME/UI/ColdSteelAmmoReadout.cpp) 缓存 Pawn 组件指针并对 Slate 文本/字体/颜色/透明度/位移写入加脏检查（保留准星/罗盘 `NativePaint` 实时重绘）。
- **HLSL 地形着色器 / 关卡 WPO / 显存资产批处理（[optimize_hills_perf_r52.py](../../Tools/WorldGeneration/ForestVillage/optimize_hills_perf_r52.py)）**：
  - **Pass A（着色器与材质重编，[compiled.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOpt-R52/compiled.json)）**：为 `MF_TrailDirt` 新增 `RoadWeight`（预览默认 `1.0`）与 `[branch] if(RoadWeight<=0.0005)` 路权短路并在 `M_ForestReferenceMesh` 接通 UV4/打包切换掩码（`wired_trail_dirt_calls=1`，非道路像素运行时跳过 ~27 次路床采样）；更新 [forest_road_mix.ush](../../Tools/WorldGeneration/ForestVillage/forest_road_mix.ush)、[trail_soil.ush](../../Tools/WorldGeneration/ForestVillage/trail_soil.ush)、[cliff_surface.ush](../../Tools/WorldGeneration/ForestVillage/cliff_surface.ush)、[roadside_leaves.ush](../../Tools/WorldGeneration/ForestVillage/roadside_leaves.ush)、[continuous_meadow.ush](../../Tools/WorldGeneration/ForestVillage/continuous_meadow.ush) 的距离剪枝与视差分支，并同步至 `M_ForestReferenceMesh`（`2248 → 2264` 静态 PS 指令 / `18` 采样器）与 `M_ForestVillageLandscape`（`753 → 768` / `8` 采样器，`ground_cover_hlsl.updated=true`）。
  - **Pass B（关卡草与植被 WPO 落盘）**：`L_ForestPathVillage` 调整 **`76`** 组 HISM 的 `WorldPositionOffsetDisableDistance`；`L_ForestPathForest` 调整 **`10`** 组 PCG ISM WPO 与 **`6`** 组动态 GI 开关；`TemperateHillsWorld` 只读审计确认 `PCGLayer0..3` 均启用分区流送。
  - **Pass C（Nanite 树木冗余 LOD 与 4K 贴图显存清理）**：对 4 个开启 Nanite 的树种网格（`SM_CommonHazel_Forest_01/02`、`SM_EuropeanHornbeam_Forest_04/05`，原含最高达 `348.4k–489.1k` 三角面的冗余 LOD1–LOD6）执行 `RemoveLods` 清理为仅保留源几何（`lods = 7 → 1`、`nanite_enabled = true`），并同步重置 `MinLOD = 0`（清除平台/分级覆盖且复检冷加载 **`0`** 条 `Min LOD` 警告）；将 `T_Voronoi_Perturbed_4k` 封顶至 `1024`，将 `T_Detail_Wood01a` 封顶至 `2048` 并开启流送与 `TMGS_SIMPLE_AVERAGE` Mip。
- **落盘与恢复**：`11` 份修改前 `.uasset/.umap` 已按 SHA-256 备份至 [Before](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOpt-R52/Before)，逐项前/后哈希与统计写入 [published.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOpt-R52/published.json)。当前状态：**未实机测试 · 待 NAS 备份（请进 `L_ForestPathVillage` 实测并用 F6 导出新一轮数据对比帧率与显存）**。

<a id="hills-perf-opt-r53"></a>

## R53 丘陵灯光 VSM/体积雾、远距城镇夜灯信标与 CPU/物理优化（`HillsPerfOpt-R53`）

针对 R50 后实测（`utrace_export_4` / `performance-20261126-132514` / `village-shadows.json` / `gpu_resource_inventory`）暴露的阴影点光/体积雾过载、僵尸尸体物理常驻、Tick 轮询与运行时覆盖 R52 树木 WPO 问题，在不降分辨率、不削减画质的前提下完成 R53 优化，并新增 60 m–1,200 m 极远距城镇夜灯信标系统：

- **A. 灯光 VSM 阴影 / 体积雾 / 运行时树木 WPO 修正**：
  - [VillageInteriorLighting.cpp](../../Source/FPSGAME/WorldGeneration/VillageInteriorLighting.cpp)：新增控制台开关 `fps.Hills.InteriorLightShadows`（默认 `0`）与 `fps.Hills.InteriorLightVolumetric`（默认 `0`），在 `UVillageInteriorLighting::Configure()` 与 `ApplyAppearance()` 中统一关闭村内室内与商铺点光源阴影及体积雾散射（不动玩家手持法杖）。
  - [SmithYardLamp.cpp](../../Source/FPSGAME/WorldGeneration/SmithYardLamp.cpp)：28 盏 `AVillageShopChainLamp` 点光默认 `bLightCastsShadows = false`。
  - [HillsBlacksmith.cpp](../../Source/FPSGAME/WorldGeneration/HillsBlacksmith.cpp)：关闭铁匠铺炉火光体积雾散射（`SetVolumetricScatteringIntensity(0.f)`）。
  - [HillsWindmill.cpp](../../Source/FPSGAME/WorldGeneration/HillsWindmill.cpp)：3 盏风车复原灯关闭阴影/体积雾散射，并补齐缺省剔除距离 `2200 cm`（渐变 `450 cm`）。
  - [BronzeTorch.cpp](../../Source/FPSGAME/Building/BronzeTorch.cpp)：在 `ApplyComponentOffsets()` 为缺省无限远火把（`BronzeTorch_2..7`）补齐 `MaxDrawDistance = 4500 cm`、`FadeRange = 600 cm`，并将非阴影火把体积雾散射清零（阴影火把降至 `0.04`）。
  - [ForestVillage.cpp](../../Source/FPSGAME/WorldGeneration/ForestVillage.cpp)：将运行时树木 `WorldPositionOffsetDisableDistance` 从 `8000/4000 cm` 收紧至 `3500/2200 cm`，不再覆盖 R52 已落盘的 WPO 优化。
- **B. 极远距城镇夜灯信标与山谷远景微光（60 m – 1,200 m，无阴影 / 白天零开销）**：
  - 源码接入：[VillageDistantGlow.h](../../Source/FPSGAME/WorldGeneration/VillageDistantGlow.h) · [VillageDistantGlow.cpp](../../Source/FPSGAME/WorldGeneration/VillageDistantGlow.cpp)，经 `TemperateHillsWorld` / `ForestVillage::LoadVillageSettlement()` 挂接（`L_ForestPathVillage` 与 `L_TemperateHills` 共用），CVar `fps.Hills.DistantVillageGlow = 1`（`0.5 s` 节流刷新，跳过专用服务器，白天隐身 `0` 开销）。
  - **Tier 1 单合批公告板光晕**：`1` 个 `UInstancedStaticMeshComponent`（29 处锚点：东西城门、主街站点、教堂、三层酒馆、铁匠铺、风车塔、商铺及 2 层高空山谷橘暖光晕），复用引擎 `/Engine/BasicShapes/Plane.Plane` 与新建正式材质 [/Game/WorldGeneration/TemperateHills/ShopLighting/M_VillageDistantBeacon](../../Content/WorldGeneration/TemperateHills/ShopLighting/M_VillageDistantBeacon.uasset)（脚本 [optimize_hills_perf_r53.py](../../Tools/WorldGeneration/ForestVillage/optimize_hills_perf_r53.py)）。0 贴图分析式 Unlit Additive 公告板，使用 5 个 `PerInstanceCustomData` 槽位实现近距自动隐去防穿帮、远距自动尺寸与亮度补偿；`PCD3D_SM6` 无头构建与冷加载探针复核均为 **0 警告 / 0 错误**（2 个 `Custom` 节点全引脚连接，`ps=230 / vs=385 / samplers=1`）。
  - **Tier 2 单盏无阴影远距城镇泛光**：`1` 盏 `CastShadows = false` 的 `UPointLightComponent`（半径 `8500 cm`，`MaxDrawDistance = 140000 cm`），仅夜间且相机距镇中心 `> 55 m` 时平滑亮起，进入城镇前淡出关闭。
- **C. GameThread CPU / 尸体物理泄漏 / NPC URO**：
  - [HumanoidKnockdownComponent.cpp](../../Source/FPSGAME/Monsters/HumanoidKnockdownComponent.cpp) 与 [FatZombie.h](../../Source/FPSGAME/Monsters/FatZombie.h) / [FatZombie.cpp](../../Source/FPSGAME/Monsters/FatZombie.cpp)：移除尸体冻结判定中的 `!bCorpse` 限制，使落地尸体在 `CorpseSettleDeadline`（`4 s`）后冻结物理并保留空中尸体自然坠落；`FatZombie` fallback 布娃娃补充 `FreezeDeathRagdoll()` `4.5 s` 定时器兜底冻结。
  - [FPSGAMECharacter.cpp](../../Source/FPSGAME/FPSGAMECharacter.cpp)：9 处 Win32 `GetAsyncKeyState` 调用仅在存在移动/冲刺输入时触发；Tick 尾部 12 处命令行 `FParse::Param` 检查改为 `static const bool` 一次性缓存。
  - [FPSPlayerBodyComponent.cpp](../../Source/FPSGAME/Characters/FPSPlayerBodyComponent.cpp)：非脏装备刷新与宿主可见性兜底轮询从 `0.2 s` 降至 `1.0 s`（装备变更脏标记仍即时响应）。
  - [VillageResidentDetail.cpp](../../Source/FPSGAME/NPC/VillageResidentDetail.cpp)：在 `ReducePoseWork()` 开启 `Mesh->bEnableUpdateRateOptimizations`，并将视锥外非战斗姿势降频距离从 `2600` 收紧至 `1800 cm`。
- **落盘、编译与恢复**：
  - 编译对照与回执：[compiled.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOpt-R53/compiled.json) · [published.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOpt-R53/published.json)（`after_sha256: 45f21f019296b6a54c60748c7a6032525faae9d433241f232455b88f4ae010c4`）。
  - 已完成 `FPSGAMEEditor Win64 Development` 增量编译（含 `TemperateHillsCompatibility.cpp` 内容指纹同步，退出码 `0`）。当前状态：**未实机测试 · 待 NAS 备份（建议夜晚在 `L_ForestPathVillage` 村内与 100–800 m 远山小径对比并导出新一轮 F6 性能数据）**。

<a id="hills-perf-opt-r54"></a>

## R54 丘陵显存治理、TSR 75% / Lumen 平衡预设与 HUD CPU 优化（`HillsPerfOpt-R54`）

针对 R53 后实测（`gpu-0F7EF11249D7EA3D12D38EBAD8CF6EE8` / `performance-20261126-155948` / `utrace_export_5` 875 帧 @ `2552×1218`）暴露的三大根因——① DXGI 本地显存溢出（`11.56–12.10 GB / 10.84 GB` 预算，第 `41879` 帧换页卡顿 `238 ms` + 光追 Proxy 驱逐 Ensure），② 原生 `100%` 渲染像素负担过重（`LumenScreenProbeGather = 14.91 ms` + `Nanite::BasePass = 11.48 ms`），③ `ColdSteelHUDWidget_Tick = 1.95 ms` 与 `Slate_PaintSlowPath = 3.17 ms`——完成 R54 组合优化并编入可实时切换的质量预设控制器：

- **1. 显存回收（目标 ~1.3 GB 含 TSR/GBuffer 节省）**：
  - **教堂修女远距发丝裁剪与光追关闭**（[ChapelNun.h](../../Source/FPSGAME/NPC/ChapelNun.h) · [ChapelNun.cpp](../../Source/FPSGAME/NPC/ChapelNun.cpp)）：新增 `fps.Hills.NunHairStrandsCullCm`（默认 `2200 cm`，`+200 cm` 滞回）；`> 24 m` 时自动隐藏 `HairCore`（`Nun_LowBun_Core_R5`）并关闭阴影、Tick 与 Niagara 求解器，释放其约 `833.1 MB` Hair Strands 瞬态显存池（`Hair.VoxelPageTexture` 等）与 `0.33–0.46 ms` GPU 开销，同时始终保留骨架 `NapeHair`；`≤ 22 m` 走近自动恢复全发丝用于对话近景。同步为 `HairCore` 与 `HairLoose` 关闭 `bVisibleInRayTracing`，缓解光追几何驱逐 Ensure。
  - **3 张超大贴图分辨率上限治理**（[optimize_hills_perf_r54.py](../../Tools/WorldGeneration/ForestVillage/optimize_hills_perf_r54.py)）：保持 `CompressionSettings` 不变（避免材质 `SamplerType` 冲突），按 `MaxTextureSize` 封顶：
    - `/Game/UndergroundTunnel/Textures/Effects/T_RainDrop01a`：`4096×4096`（`TC_EDITOR_ICON` 未压缩 `~85.4 MB`）`max_texture_size: 0 → 1024`（`~5.3 MB` 理论估算，`.uasset` 体积 `14,890,249 → 11,873,693 B`）；
    - `/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Body/Baked/T_Body_N`：`8192×8192`（`TC_NORMALMAP` `~85.4 MB`）`max_texture_size: 0 → 4096`（`~21.3 MB` 理论估算）；
    - `/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Body/Baked/T_Body_SRMF`：`8192×8192`（`TC_MASKS` `~85.4 MB`）`max_texture_size: 0 → 4096`（`~21.3 MB` 理论估算）。
- **2. TSR 75% + UE 5.8 平衡 Lumen 分级预设控制器（`fps.Hills.QualityPreset`）**：
  - [TemperateHillsStreaming.cpp](../../Source/FPSGAME/WorldGeneration/TemperateHillsStreaming.cpp) 新增 `fps.Hills.QualityPreset`（默认 `1`，支持运行时控制台即时热切换；使用 `ECVF_SetByPluginLowPriority` 标签层 `FPSGAME.HillsQualityPreset`，跳过 Commandlet / NullRHI / 专用服务器，退出丘陵世界时自动 `Unset` 全数还原，不污染主神空间或自动化审查脚本）：
    - `0`（原版 Epic）：恢复原始默认设定（`ScreenPercentage=100`、`DownsampleFactor=16`、`HWRT=1`）；
    - `1`（默认推荐平衡档）：`r.ScreenPercentage=75`、`r.TSR.History.ScreenPercentage=100`、`r.Lumen.ScreenProbeGather.DownsampleFactor=32`、`r.Lumen.ScreenProbeGather.RadianceCache.ProbeResolution=16` / `NumProbesToTraceBudget=100`、`r.Lumen.ScreenProbeGather.ShortRangeAO.DownsampleFactor=2`、`r.Lumen.ScreenProbeGather.TwoSidedFoliageBackfaceDiffuse=0`、`r.Lumen.HardwareRayTracing.HitLighting.Allowed=0`、`r.LumenScene.SurfaceCache.AtlasSize=3584` / `DirectLighting.UpdateFactor=64` / `Radiosity.UpdateFactor=128`、`r.Lumen.Reflections.DownsampleFactor=2` / `MaxRoughnessToTraceForFoliage=0.2` / `ScreenProbeGather.MaxRoughnessToEvaluateRoughSpecularForFoliage=0.4`（保留 HWRT GI/反射，大幅降低像素与探针开销及 TSR/GBuffer 显存）；
    - `2`（高帧率软光追档）：在 `1` 基础上关闭 `r.Lumen.HardwareRayTracing=0`。
- **3. 剩余 29 盏体积雾点光清零**：
  - [HillsNightPortal.cpp](../../Source/FPSGAME/WorldGeneration/HillsNightPortal.cpp)（`PurpleSpill`）与 [VillageHotOil.cpp](../../Source/FPSGAME/WorldGeneration/VillageHotOil.cpp)（`HearthGlow`）将 `VolumetricScatteringIntensity` 从默认 `1.0` 降至 `0.15`。
  - [VillageInteriorLighting.h](../../Source/FPSGAME/WorldGeneration/VillageInteriorLighting.h) / [.cpp](../../Source/FPSGAME/WorldGeneration/VillageInteriorLighting.cpp) 新增 `ApplyVolumetricBudget()`，并在 [HillsTavernSite.cpp](../../Source/FPSGAME/WorldGeneration/HillsTavernSite.cpp)（覆盖 `L_AbandonedVillage` 静态马厩院灯/主屋灯 13 盏）与 [ForestVillage.cpp](../../Source/FPSGAME/WorldGeneration/ForestVillage.cpp)（覆盖 `L_ForestPathVillage` `LumberMill_Compound` 14 盏）于运行时按 `fps.Hills.InteriorLightVolumetric` 自动清零，避免直接改写关卡 `.umap`。
- **4. HUD / Slate 逐帧布局失效与快捷栏轮询瘦身**：
  - [ColdSteelStaminaHUD.cpp](../../Source/FPSGAME/UI/ColdSteelStaminaHUD.cpp)、[ColdSteelEventTimeline.cpp](../../Source/FPSGAME/UI/ColdSteelEventTimeline.cpp)、[ColdSteelShopHUD.cpp](../../Source/FPSGAME/UI/ColdSteelShopHUD.cpp)、[ColdSteelForgingHUD.cpp](../../Source/FPSGAME/UI/ColdSteelForgingHUD.cpp)、[ColdSteelPanelNavigation.cpp](../../Source/FPSGAME/UI/ColdSteelPanelNavigation.cpp)、[ColdSteelFireballHUD.cpp](../../Source/FPSGAME/UI/ColdSteelFireballHUD.cpp)：为 `StaminaSlot` / `BottomHintsSlot` 位移/显隐/透明度加脏检查、将提示文本 `SetFont` 与行高内边距从逐帧移回尺度变更块；为 `UpdateEventTimelineLayout()` 新增几何/动画状态缓存命中早退；关闭中的商店/锻造面板早退；`RefreshQuickBar()` 跳过已折叠的 Q/E/X 退役槽位（零 `.h` 改动，全部动画与交互语义不变）。
- **落盘、编译与校验**：
  - 3 份原版贴图 `.uasset` 已按 SHA-256 备份至 [Before](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOpt-R54/Before)，前/后规格与校验清单见 [published.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOpt-R54/published.json)（无头运行 `UE_PY_EXIT=0`、`0` 错误，日志见 `Saved/Logs/HillsPerfOpt-R54.log`）。
  - `FPSGAMEEditor Win64 Development` 编译通过（`BUILD_EXIT=0`），已于 [UnrealEditor-FPSGAME.dll](../../Binaries/Win64/UnrealEditor-FPSGAME.dll) 二进制核验 `fps.Hills.QualityPreset` 与 `fps.Hills.NunHairStrandsCullCm` 符号就位。当前状态：**未实机测试 · 待 NAS 备份（请进 `L_ForestPathVillage` 实测并可用控制台切换 `fps.Hills.QualityPreset 0 / 1 / 2` 对比效果与 F6 数据）**。

<a id="hills-perf-opt-r55"></a>

## R55 远景夜灯接地剪影与修复建筑暖窗升级（`HillsPerfOpt-R55`）

针对实测反馈“远景城镇灯光剪影有悬空感”的问题，按第二档（方案 A+B+C+暖窗）重构极远距夜灯与剪影层次，维持无阴影低开销合批架构（新增 1 个 `UInstancedStaticMeshComponent`，0 新增实时光源）：

- **1. 消除悬空根因（`VillageDistantGlow.h/.cpp`）**：
  - **废弃全套硬编码悬浮估算点，改为锚定实景灯具与修复态**：[VillageDistantGlow.cpp](../../Source/FPSGAME/WorldGeneration/VillageDistantGlow.cpp) 于 `RebuildAnchors()` 实时采集流送/复原后的真实室外光源精确坐标——`AVillageRoadLamp`（联动城墙/酒馆修复）、外墙夜班挂灯 `AVillageShopChainLamp`（排除室内 `AlwaysLit` 与破败未亮 `Unlit`）、外立面火把 `ABronzeTorch`（排除教堂室内 `NaveTorch` 与角色持有物）及 `L_AbandonedVillage` 静态马厩院灯 `VillageStable.GroundDetailR4`（`75 cm` 去重），并经 [HillsTavernSite.cpp](../../Source/FPSGAME/WorldGeneration/HillsTavernSite.cpp) / [TemperateVillageStreetLighting.cpp](../../Source/FPSGAME/WorldGeneration/TemperateVillageStreetLighting.cpp) 与 `GetMapSurfaceRevision()` / `3 s` 挂件计数兜底自动刷新。
  - **消除近中距重影与前推鬼火感**：室外灯点（`Mode 0`）淡入延后至 `44–48 m`（无缝接力真实路灯 `50 m` 淡出）、远距最大放大倍数从 `2.8×` 收紧至 `1.55×`、取消 `-40 cm` 强行前推改为最多 `6 cm` 玻璃净空；在 [optimize_hills_perf_r55.py](../../Tools/WorldGeneration/ForestVillage/optimize_hills_perf_r55.py) 重建的 [/Game/WorldGeneration/TemperateHills/ShopLighting/M_VillageDistantBeacon](../../Content/WorldGeneration/TemperateHills/ShopLighting/M_VillageDistantBeacon.uasset) 中加入铁帽上遮蔽与自适应 `DepthFade`（`45 / 80 / 450 cm`）。
- **2. 接地三层剪影重构（低空逆光半穹顶 + 贴地光池 + 压低泛光）**：
  - **贴地扁平逆光半穹顶（`Mode 1`）**：用 2 个贴近地形锚定的扁平宽雾晕穹顶（基高 `+2.2/+2.6 m`、宽高比 `3.7:1`、Z 轴柱面朝向且底部嵌入地形下 `~4.3 m` 后柔和渐溶）替代原 `+11/+15 m` 高空正圆光球，把屋顶、教堂尖顶、风车叶与城墙垛口压出深色逆光剪影。
  - **地形法线贴合暖光池（`Mode 2`）**：每盏室外灯下方 `BeaconISM` 同合批叠加一张随 `ATemperateHillsWorld::Height()` 4 点差分法线贴合路面的水平暖色光池（`+14 cm`，`DepthFade = 45 cm`），远景直接给出地面落脚锚点。
  - **Tier 2 泛光下压**：`TownGlowLight` 从 `+18 m` 压低至 `+6.5 m`（`14,000 lm`、`AttenuationRadius = 68 m`、`Volumetric = 0.14`），只漫照村内下半立面而保持屋顶与夜空反差。
- **3. 物理嵌入型修复建筑暖窗（`M_VillageWarmWindow` + `WindowISM`）**：
  - 新建 Unlit Additive 材质 [/Game/WorldGeneration/TemperateHills/ShopLighting/M_VillageWarmWindow](../../Content/WorldGeneration/TemperateHills/ShopLighting/M_VillageWarmWindow.uasset)（0 贴图、无 WPO 位移、带窗棂花格/内室暖梯度/掠射角遮蔽衰减，`< 30 m` 彻底淡出不干扰近景室内）；新增开关 `fps.Hills.DistantVillageWindows`（默认 `1`，配合 `fps.Hills.DistantVillageGlow` 实时热切对比）。
  - 实时绑定并随修复状态点亮：旧教堂（7 扇哥特尖拱窗 + 西侧玫瑰花窗）、全部可见已修复 `AColdSteelWindow`（自动避开关闭态木窗扇外置 `+5.5 cm` 嵌于石窗框凹槽内）、已修复三层酒馆 1–3 层全部外窗、以及已修复个人仓库与铁匠铺阁楼窗。
- **落盘、编译与校验**：
  - 无头材质构建日志见 `Saved/Logs/HillsPerfOpt-R55-SM6.log`（`SM6_PY_EXIT=0`，`PCD3D_SM6` 无报错/无警告）；改前 `M_VillageDistantBeacon`（R53）按 SHA-256 备份至 [Before](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOpt-R55/Before)，完整回执见 [published.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOpt-R55/published.json)。
  - `FPSGAMEEditor Win64 Development` 编译通过（`BUILD_EXIT=0`），已于 [UnrealEditor-FPSGAME.dll](../../Binaries/Win64/UnrealEditor-FPSGAME.dll) 二进制确认 `fps.Hills.DistantVillageGlow`、`fps.Hills.DistantVillageWindows` 与 `M_VillageWarmWindow` 符号就位。当前状态：**未实机测试 · 待 NAS 备份**。

<a id="hills-perf-opt-r56"></a>

## R56 丘陵与村庄区域 P0 综合性能优化（`HillsPerfOpt-R56`）

围绕 `L_ForestPathVillage` 实测的四大核心瓶颈（Async Compute CAS VRS `5.52 ms`、路灯动态 VSM 与森林 518 m 单块 ISM 失效尖峰、`Slate_PaintSlowPath 3.17 ms` + `ColdSteelHUD_RefreshAmmo 1.50 ms`、以及 65 个常驻刷骨 + `RayTracingDynamicGeometry 1.30 ms`）完成纯 C++ 零画质妥协 P0 合集优化：

- **1. 关闭高耗 CAS VRS 并收紧丘陵光追剔除（[TemperateHillsStreaming.cpp](../../Source/FPSGAME/WorldGeneration/TemperateHillsStreaming.cpp)）**：
  - 在 `fps.Hills.QualityPreset`（1/2 档默认生效，`0` 或离场自动回退）新增：`r.VRS.ContrastAdaptiveShading=0`、`r.VRS.EnableSoftware=0`、`r.RayTracing.Culling=3`、`r.RayTracing.Culling.Radius=15000`（2 档 `10000`）、`r.RayTracing.Culling.Angle=2.0`（2 档 `3.0`）、`r.RayTracing.Geometry.LandscapeGrass=0`。
- **2. 路灯近距动态阴影预算与森林 ISM VSM/RT 卫生（[VillageRoadLamp.cpp](../../Source/FPSGAME/WorldGeneration/VillageRoadLamp.cpp)、[ForestVillage.cpp](../../Source/FPSGAME/WorldGeneration/ForestVillage.cpp)）**：
  - `AVillageRoadLamp` 接入 `fps.Hills.RoadLampShadowDistCm`（默认 `2200 cm`，`+400 cm` 滞回）与 `fps.Hills.RoadLampVolumetric`（默认 `0`：仅近身开影路灯保留 `0.025` 体积散射，且统一关闭体积阴影投射）。
  - 为林道及 `AForestVillageRegion` 鹅耳枥/榛灌 ISM 设置 `EShadowCacheInvalidationBehavior::Rigid`，补齐 WPO 距离封顶（`3500 / 2200 cm`）、关闭 RT WPO 求值，并对榛灌与无阴影地被关闭 `bVisibleInRayTracing`（原地设标志位，不改实例索引）。
- **3. HUD 叶子层重绘隔离、`UInvalidationBox` 缓存与数值公式版本缓存（[ColdSteelHUDWidget.h](../../Source/FPSGAME/UI/ColdSteelHUDWidget.h)/[.cpp](../../Source/FPSGAME/UI/ColdSteelHUDWidget.cpp)、[ColdSteelHUDConstruction.cpp](../../Source/FPSGAME/UI/ColdSteelHUDConstruction.cpp)、[ColdSteelCrosshair.cpp](../../Source/FPSGAME/UI/ColdSteelCrosshair.cpp)、[ColdSteelStatusModel.cpp](../../Source/FPSGAME/UI/ColdSteelStatusModel.cpp)、[ColdSteelSpellMana.cpp](../../Source/FPSGAME/Skills/ColdSteelSpellMana.cpp)）**：
  - 保留 `WidgetTree->RootWidget` 为 `UCanvasPanel` (`ColdSteelOuterRoot`)，在其下拆为 `BackPaintOverlay`（弓镜光学遮罩，`Z=-100`）、`UInvalidationBox` 包裹的 `ColdSteelRoot`（开关 `fps.HUD.InvalidationCache`，默认 `1`）与 `FrontPaintOverlay`（准星/受击/目标栏/导航绘制，`Z=200`）；移除每帧整树 `Invalidate(Paint)`，仅刷新独立叶子 `UColdSteelHUDPaintLayer` 并节流时间线脉冲透明度写入（`0.08 s` / `>= 0.015`）。
  - 在 `UColdSteelStatusModel` 按 `StatCacheVersion + Generation + Level + ActiveWeaponSlot + Items.Num() + Infection.Stage + bSanityDepleted` 缓存 `EquipmentBonus`、`Derived("maxHp"/"maxMp")` 与 `AdjustedManaCost` 乘区，去除 `EquipmentBonusFor` 内层堆上 `TArray` 构造，并缓存 `RefreshQuickBar` 与 `UColdSteelAmmoReadout` 的 Pawn 组件指针。
- **4. 骨骼 URO、离屏暂停与中远距光追代理剔除（[VillageResidentDetail.cpp](../../Source/FPSGAME/NPC/VillageResidentDetail.cpp)、[ChapelNun.cpp](../../Source/FPSGAME/NPC/ChapelNun.cpp)、[StableRidingHorse.cpp](../../Source/FPSGAME/Movement/StableRidingHorse.cpp)、[LumberMillWorkerActor.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.cpp)、[LumberMillTimberWagon.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillTimberWagon.cpp)、[WildlifeDistanceActivity.cpp](../../Source/FPSGAME/Monsters/WildlifeDistanceActivity.cpp)、[SwordTasselMeshComponent.cpp](../../Source/FPSGAME/Weapons/SwordTasselMeshComponent.cpp)）**：
  - 村内居民与修女在 `> 14–16 m` 启用 URO，`fps.Hills.ResidentRayTracingDistCm`（默认 `1800 cm`，`+300 cm` 滞回）控制 3P RT 代理；马厩战马与运木马车接入 URO 与 `fps.Hills.HorseRayTracingDistCm`（默认 `2200 cm`，骑乘中恒开）；伐木工 4 部位与野生动物接通 `OnlyTickPoseWhenRendered` / 离屏停 `MeshTick` 与 RT 剔除；`USwordTasselMeshComponent` 对本地 1P `bOwnerNoSee` 隐藏影分身与离屏实例跳过 `240 Hz × 20` 迭代物理（保留无头命令审计豁免）。
- **编译与校验**：
  - `FPSGAMEEditor Win64 Development` 编译通过（`BUILD_EXIT=0`），已于 [UnrealEditor-FPSGAME.dll](../../Binaries/Win64/UnrealEditor-FPSGAME.dll) 确认全部新增 CVar 与类符号就位。当前状态：**未实机 PIE/F6 复测 · 待 NAS 备份**。

<a id="hills-perf-opt-r57"></a>

## R57 丘陵与村庄区域 A 档零/无感画质减负、Slate 泄漏修复与 Tick 观测（`HillsPerfOpt-R57`）

承接 R56 F6 对比报告（`L_ForestPathVillage` 均帧 `26.76 → 45.64 fps`、`gpu0 p50 33.82 → 17.67 ms`、`HUDInvalidationCache` 偶现 `p95=3.74 ms`），按用户选定 **A 档（画质零妥协）** 完成以下纯 C++ 优化与插桩：

- **1. 半分辨率局部体积雾、雾袋距离封顶与 UE 5.8 High TSR CVar（[TemperateHillsStreaming.cpp](../../Source/FPSGAME/WorldGeneration/TemperateHillsStreaming.cpp)、[ForestVillageMistComponent.cpp](../../Source/FPSGAME/WorldGeneration/ForestVillageMistComponent.cpp)）**：
  - `fps.Hills.QualityPreset`（`Preset 1/2`）新增：`r.LocalFogVolume.HalfResolution=1`、`r.TSR.History.UpdateQuality=2`、`r.TSR.RejectionAntiAliasingQuality=1`；仅在 `Preset == 2` 追加 `r.Nanite.MaxPixelsPerEdge=1.5`（`Preset == 1` 保持原生 `1.0`），并在 `HILLS_QUALITY` 日志打印 `lfv_half` / `tsr_uq` / `nanite_edge`。
  - `UForestVillageMistComponent` 新增 `fps.Hills.ForestMistRangeCm`（默认 `18000 cm`，`<= 0` 恢复 `24500 cm`），淡出起止按 `[0.7 * Range, Range]` 随动。
- **2. Slate 缓存泄漏止血（[ColdSteelHUDConstruction.cpp](../../Source/FPSGAME/UI/ColdSteelHUDConstruction.cpp)、[ColdSteelHUDReadouts.cpp](../../Source/FPSGAME/UI/ColdSteelHUDReadouts.cpp)、[ColdSteelAmmoReadout.h](../../Source/FPSGAME/UI/ColdSteelAmmoReadout.h)/[.cpp](../../Source/FPSGAME/UI/ColdSteelAmmoReadout.cpp)、[ColdSteelStaffReadout.cpp](../../Source/FPSGAME/UI/ColdSteelStaffReadout.cpp)、[ColdSteelWorldClock.cpp](../../Source/FPSGAME/UI/ColdSteelWorldClock.cpp)、[ColdSteelHUDTimeline.cpp](../../Source/FPSGAME/UI/ColdSteelHUDTimeline.cpp)、[ColdSteelEventTimeline.cpp](../../Source/FPSGAME/UI/ColdSteelEventTimeline.cpp)、[ColdSteelHUDWidget.cpp](../../Source/FPSGAME/UI/ColdSteelHUDWidget.cpp)、[ColdSteelResourceMeter.cpp](../../Source/FPSGAME/UI/ColdSteelResourceMeter.cpp)）**：
  - `UpdateInteractHint()` 对 `InteractHintBlur` 与 `InteractHintTitle` 的 `SetVisibility`、`RefreshAmmo()` 抽屉隐藏时的 `AmmoReadout->SetVisibility(Collapsed)` 补充状态差异守卫；在 `UColdSteelAmmoReadout` 新增 `SetTextIfChanged` / `SetColorIfChanged`（`CachedTextColors`）、`LastDualVisible` / `LastStaffVisible` 与 `LastSlotPosition` / `bSlotAutoSizeSet` 守卫，清除 `Present*` / `PresentStaff` / `PresentSpellbook` / `UpdateLayout` 20 Hz 无变更重绘失效。
  - 补全剩余 3 处 HUD 缓存泄漏：`SColdSteelWorldClock::SetTime` 将日晷指针重绘按每日 `720` 步（`0.5°`）量化；`RefreshEventTimeline`（`GTimelineVisualCache`）、`TickEventTimelinePresentation`（`>= 0.002` + 临近降雨即时吸附）与 `NativeTick` 脉冲节流（折叠待机态恒定透明、`>= 0.15 s` / `>= 0.03`）消除天气时间轴无变更重刷；`UColdSteelResourceMeter::SetSemanticValue` / `SetValue` 加入 `0.0025` 亚像素死区并保留 `0 / 0.25 / 1` 边界实时穿透。
- **3. 残留远距火焰与尖塔点光减负（[BronzeTorch.h](../../Source/FPSGAME/Building/BronzeTorch.h)/[.cpp](../../Source/FPSGAME/Building/BronzeTorch.cpp)、[VillageRoadLamp.h](../../Source/FPSGAME/WorldGeneration/VillageRoadLamp.h)、[VillageLightningSpire.cpp](../../Source/FPSGAME/WorldGeneration/VillageLightningSpire.cpp)）**：
  - `ABronzeTorch` 新增 `ManagesOwnShadowBudget()`（`AVillageRoadLamp` 覆写为 `true` 保留自有预算）、`bInteriorLightingManaged`（`ConfigureShopInterior` 置位以保护 `fps.Hills.InteriorLightShadows=0` 不被外部火把预算覆盖）与 `UpdateTorchShadowBudget()`（`0.5 s` 节流，`NM_DedicatedServer` 早退，`bHasView && Range <= Cutoff` 配合 `fps.Hills.RoadLampShadowDistCm` + `400 cm` 滞回，关闭体积阴影并将体积散射压至 `0.03 / 0.0`，`ConfigureSceneLight` 后立即刷新）。
  - `AVillageLightningSpire::OnRep_Setup` 将 `CrownLight`（`SpireCrownGlow`）体积散射由默认 `1.0` 降至 `0.08` 并关闭体积阴影。
- **4. `AFPSGAMECharacter::Tick` 细分插桩与轻量冗余清理（[FPSGAMECharacter.cpp](../../Source/FPSGAME/FPSGAMECharacter.cpp)、[FPSGAMECharacterCamera.cpp](../../Source/FPSGAME/FPSGAMECharacterCamera.cpp)）**：
  - 不改 `FPSGAMECharacter.h`，在 `AFPSGAMECharacter::Tick` 植入 `FPSChar_Traversal`、`FPSChar_ProfileTick`、`FPSChar_MovementRefresh`、`FPSChar_WeaponState`、`FPSChar_CameraViewmodel`、`FPSChar_ActionPose` 6 段 `TRACE_CPUPROFILER_EVENT_SCOPE`；并复用 `UpdateCamera` 内 `UFPSPlayerBodyComponent` 局部指针以消除同帧 3 次重复 `FindComponentByClass`。
- **编译与校验**：
  - `FPSGAMEEditor Win64 Development` 编译通过（`BUILD_EXIT=0`），已于 [UnrealEditor-FPSGAME.dll](../../Binaries/Win64/UnrealEditor-FPSGAME.dll)（`55.26 MB`，`2026-11-27 19:01:20`）二进制确认 `r.LocalFogVolume.HalfResolution`、`r.TSR.History.UpdateQuality`、`r.TSR.RejectionAntiAliasingQuality`、`r.Nanite.MaxPixelsPerEdge`、`fps.Hills.ForestMistRangeCm`、`ManagesOwnShadowBudget` 等全部新增/修订符号就位。当前状态：**未实机 PIE/F6 复测 · 待 NAS 备份**。

<a id="road-upgrade-r48"></a>

## R48 道路写实高随机化全面升级（地形、材质、五分区 PCG 与路边杂物）

围绕东门林道（250.8 米）与采石场道路（398.5 米）完成四维写实升级，严格保留村庄、参考林地内域、采石作业面和水坑保护区零位移（`village_max_cm=0`、`ref_interior_max_cm=0`、`quarry_max_cm=0`）：

- **道路随机微地形与拓扑场**：基于 `CliffExposure-R35` 生成 [prepare_road_relief_r48.py](../../Tools/WorldGeneration/ForestVillage/prepare_road_relief_r48.py)，在 11,561 个道路格点叠加非周期域扭曲双车辙下凹、中心草脊微拱、路肩排水浅沟及 11 处自然积水浅洼（高差 `-19..+20 cm`，涉及 7 块外围地块，同步重算 `T_ContinuousMeadowField` 与 15,937 处远草实例），并输出 2048×512（0.3125 米/纹素）道路拓扑场 `road-topo.npz`。
- **路面 6 材质随机混合、流向连续车辙与 8 块路肩落叶碎屑**：复用现有 8 个纹理输入引脚与共享采样器（`MI_ForestTilePacked` 保持 18 采样器零新增、`M_ForestVillageLandscape` 保持 8 采样器），[prepare_road_mix_r48.py](../../Tools/WorldGeneration/ForestVillage/prepare_road_mix_r48.py) 将 `T_Stony*` 升级为 4096×4096 2×2 图集（碎石土 / 粗砾土路 / 潮湿泥土 / 裸露树根），`T_Tire*` 升级为 4096×2048 2×1 干湿车辙图集；[forest_road_mix.ush](../../Tools/WorldGeneration/ForestVillage/forest_road_mix.ush) 改用高度对比混合、曲线自适应 3-tap 流向对齐双车辙、宏观色变及随 `RainWetness` 联动的浅洼水膜反光（粗糙度下限放宽至 0.08）。[roadside_leaves.ush](../../Tools/WorldGeneration/ForestVillage/roadside_leaves.ush) 扩为 4×2 8 块路肩碎屑图集（4 落叶 + 松树皮 + 干松针 + 枯叶树枝 + 枯叶）。
- **Fab Quixel 资产增补与道路五分区 PCG**：下载并审查 42 套免费 Quixel Megascans（全部剔除 R41 带泥底座，含 6 材质、4 贴花、9 干净木料、5 岩石、8 路边草蕨、10 乡土中世纪路边杂物），经 [import_road_upgrade_r48.py](../../Tools/WorldGeneration/ForestVillage/import_road_upgrade_r48.py) 导入 50 个静态网格变体至 `/Game/ForestPathStudy/VillageRegion/RoadUpgrade/` 与 `WoodlandDressing/Wood/`。通过 [prepare_road_dressing_r48.py](../../Tools/WorldGeneration/ForestVillage/prepare_road_dressing_r48.py) 新增 2,274 个道路带落点（总计 14,973 点，57 个 Spawner 精调，1,593 点直立/Min.Z 贴地精调）：Zone 1 路心草脊杂草/三叶草（187）、Zone 2 内缘碎石/采石场碎石灰岩/干枯与野草簇/细枝（1,621）、Zone 3 树桩/倒木/林缘蕨类/R43 Normandy 灌木/苔岩（380）、Zone 4 路堑切坡角岩（43）、Zone 5 路边木篱笆/苔藓护坡矮石墙/直立橡木桩/旧木梁/木柴堆/木桶/木箱/断车轮/采石毛石（43）。
- **Nanite、LOD 与 HISM 性能收紧**：55 块外围地形保持 R44 Nanite + 0.25 cm 量化精度；26 个新增不透明模型均已配置简单盒/10-DOP 凸包碰撞（`CTF_USE_SIMPLE_AS_COMPLEX`）并经 `BuildSceneryNaniteMesh` 构建，6 款 ≥8,000 面模型自动启用 R46 35% 回退减面（回退总面 `73,673 → 25,781`，26 款合计 `162,346 → 114,454`）；24 个 Masked 路边草/蕨保持非 Nanite、清除无用碰撞并生成 3 级 LOD（`100% / 45% / 18%`）；57 个道路 Spawner 与实时 HISM 关闭光追，非投影小件关闭距离场、动态间接光与贴花接收，仅实体 `BlockAll` 设施影响导航。[优化脚本](../../Tools/WorldGeneration/ForestVillage/optimize_road_upgrade_r48.py) · [优化回执](F:/FPSGAMEData/ArtProduction/HillsForestPath/RoadUpgrade-R48/nanite-opt-r48.json)
- **R48b 物理结构复修与丘陵显存/帧率释放**：
  - **装饰物物理结构与零悬空重做**：模块化木篱笆改为平缓路肩（坡度 ≤19%，实测最大纵坡 6.0%）按精确端到端步距衔接、顺坡不侧倾并强制追加配套收尾立柱（`4` 跨 + `2` 根收尾柱，`unclosed_ends=0`，彻底消除悬臂横木与断节错位）；护坡矮石墙限纵坡 ≤13% 并按四角最低点深埋 14 cm；木桶/木箱/木柴堆限平地（坡度 ≤15%、四角高差 ≤8 cm）；破损车轮与旧木梁改纯贴坡并加入防架桥检测；长倒木加入防跨沟检测；24 款路边草蕨/三叶草限坡并按角点动态压实入土，全量 `>4 cm` 悬空实例由 263 降至 **0**（[fence-spans.json](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/RoadUpgrade-R48/Themes/RoadLandscape/fence-spans.json)）。
  - **纹理池、Nanite 与 HISM 性能释放**：对 8 个目录共 **301** 张未封顶/4K 贴图分级封顶（`RoadMix` 6、`Leaves` 2、`RoadUpgrade` 61、`WoodlandDressing/Wood` 30、`ForestPathStudy/Scans` 63、`VillageRegion/Granite` 105、`EuropeanHornbeam/Textures` 20、`CommonHazel/Textures` 14，预计释放 ~1.5–1.8 GB 纹理流送池以消除 `+1065 MB` 爆池）；12 cm 小石 `wjvsbay` 关闭 Nanite 改 2 级 LOD、25 款 R48 Nanite 扫描件收紧 `KeepPercentTriangles`（`0.50/0.75`）+ `35%` 回退；`DefaultEngine.ini` 设置 `r.Nanite.Streaming.StreamingPoolSize=512`；同步收紧丘陵与道路 52 组微小物/草/灌木 Spawner 与实时 HISM 剔除距离（`relu7` 21.1 万根细枝 `100→45 m`、`xjiifd1` 9.1 万颗小石 `100→40 m`、`rioqm` 5.3 万枝 `100→55 m`、`rbcuh/rbpir` 3.7 万草本 `100→50 m`、近草 60.2 万株 `64→52 m`、榛灌木 2.15 万株 `160→120 m` 且风动 25 m 关停），关闭全部非投影 HISM 的距离场、动态间接光、贴花与光追。[优化脚本](../../Tools/WorldGeneration/ForestVillage/optimize_hills_perf_r48b.py) · [性能回执](F:/FPSGAMEData/ArtProduction/HillsForestPath/RoadUpgrade-R48/perf-r48b.json)
- **C++ 与构建状态**：[ForestVillageRegion.cpp](../../Source/FPSGAME/WorldGeneration/ForestVillageRegion.cpp)、[ForestVillageRegionPCG.cpp](../../Source/FPSGAME/WorldGeneration/ForestVillageRegionPCG.cpp) 与 [FPSGAME.Build.cs](../../Source/FPSGAME/FPSGAME.Build.cs) 已补充 R48/R48b 分类、直立贴地、剔除碰撞与渲染优化规则及联机目录签名；所有正式资产与实时 HISM 已在隔离 Stage 完成无头烘焙并发布，未实机测试。

[主构建入口](../../Tools/WorldGeneration/ForestVillage/author_road_upgrade_r48.py) · [Fab 资产源与清单](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/RoadUpgrade-R48/fab-manifest.json) · [发布与恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/RoadUpgrade-R48/published.json) · [改前备份](F:/FPSGAMEData/ArtProduction/HillsForestPath/RoadUpgrade-R48/Before)

<a id="lumber-mill-r49"></a>

## R49 等高线伐木林道与三间屋伐木场（`LumberMill-R49`）

按 M 键世界地图红线与红圈定位，从村口道路拐弯处 `(88.85, 314.20) m` 衔接新增 **262.74 m 等高线随机弯曲伐木林道**，绕行水塘（最小干距 `23.53 m`）并跨越 `Y=+252 m` 接缝进入 `L_ForestPathForest` Landscape，终点抵达 `(154.0, 62.0) m, Z=+11.00 m` 平整后的 **`35 × 27 m` 伐木场院落**（最大纵坡 `14.5%`、均坡 `6.5%`）。

- **地形、Landscape 编辑层与三路共享材质**：[prepare_lumber_mill_terrain_r49.py](../../Tools/WorldGeneration/ForestVillage/prepare_lumber_mill_terrain_r49.py) 同步输出外围地块 `region.i16 / paint.rg8` 与 `L_ForestPathForest` Landscape 编辑层 `Lumber mill road & yard`（经 C++ `AForestVillageRegion::WriteLumberLandscapeLayer` 写入高度与 `C_LayerInfo` 路绘、重建 Landscape Nanite 并导出无缝 `reference.f32`，M 键世界地图自动同步显示林道与院场）；`T_RoadWearField / T_RoadMixField / T_TrackFrames / T_ShoulderLeafField` 范围扩展至 `X=[-480..+224], Y=[24..376]`（`2048×1024`），三条道路与伐木场院面零新增采样器复用 R48 多材质随机路面与路肩碎屑。
- **植被清场与沿路五分区 PCG**：清退伐木道与院场内重叠加木/草被（`L_ForestPathForest` 清退 103 棵乔木并精准 1× 重贴 192 棵边坡乔木；`HillsLandscape` 裁剪 2,231 处植被与 12 棵可采伐树；清退 15,734 株近草与重迭远草）；[prepare_lumber_road_dressing_r49.py](../../Tools/WorldGeneration/ForestVillage/prepare_lumber_road_dressing_r49.py) 为新林道生成 753 处 R48b 物理闭合五分区路边 PCG（含 3 组闭合木篱笆+收尾柱、护坡矮石墙、木柴堆/箱桶车轮场景、20 处树桩、13 根倒木、岩石与草蕨）。
- **三间屋伐木场与院落装配**：
  - [build_lumber_mill_arch.py](../../Tools/WorldGeneration/ForestVillage/build_lumber_mill_arch.py) 在 Blender 5.1 制作 8 件封闭零漏边网格（100% 复用 `OldChapel / VillageBlacksmith / VillageCarpenter / VillageTavern` 驻留 PBR 材质，建筑壳 **0 MiB** 额外纹理池）：**仓库** `SM_LM_Warehouse`（双开谷仓门、悬挑滑轮吊梁、室内互通门）、**工具间+锯木雨棚** `SM_LM_ToolRoom`（内置木工台与工具架、三柱石墩锯木棚）、**二层临时宿舍** `SM_LM_Bunkhouse`（1F 公共餐厅/石壁炉烟囱 + 16 级可走橡木楼梯 + 2F 悬挑廊窗宿舍与扶手护栏），以及锯木架 `SM_LM_SawbuckStation`、双层木床 `SM_LM_BunkBed`、三层悬臂木料架 `SM_LM_TimberRack`、场口木牌 `SM_LM_Signboard` 与木屑地垫 `SM_LM_MulchPatch`。
  - 复用既有木工/马厩/磨坊/酒馆/铁匠/Normandy 资产，并新增下载、经 Normandy 配色与粗糙度二次校准的 **20 款免费 Quixel Megascans** 木堆/板材/斧锯凿锤/滑轮绳桶梯袋/桌凳架 + 1 套 `Forest Mulch` 贴图（3 款 100× 尺度分体旧马车 glTF 改用项目 1:1 `SM_Stable_HayWagon` 与 `SM_MillBarrow`）；全部装配于单个 `LumberMill_Compound` Actor（3 栋主建筑 + 69 组 HISM 共 162 件陈设 + 7 盏无投影暖光灯笼，建筑内重叠 0）。
- **Nanite 与性能收紧**：`/Game/ForestPathStudy/VillageRegion/LumberMill` 全部网格启用 Nanite + `CTF_USE_SIMPLE_AS_COMPLEX` 精确盒碰撞（高面数自动 35% 回退、小件收紧 `KeepPercentTriangles`）；全部 **63/63** 新增贴图封顶 `≤1024 B / 512 N / 512 ORM`（中小型道具进一步收紧至 `512/512/256`，全区估算显存 `20.74 MB`）且开启流送（`never_stream=False`）；分级剔除（`44 / 72 / 135 m`）、关闭非投影与光追/距离场/GI；同步复跑 R48b 52 组丘陵/道路 HISM 性能配置。
- **R49b 伐木场院落专项精修与多轮自检复修（2026-11-26，保持已验收林道/地形/Landscape 不变）**：
  - **门洞零阻挡与零闪动重做**：重做 `add_wall_zero_flicker` 与 `add_prism_gable` 严格错厚分层（墙体 `20.0` / 门窗框 `22.4` / 立柱 `23.2` / 过梁 `24.0` / 门槛梁 `24.4` / 顶梁 `25.0` / 窗台 `26.0` / 石基 `26.4` / 角柱 `27.2` / 角基 `27.8 cm`）并采用 1 段倒角降面（三屋合计 `74k → 49k` 面，45,208 面三维共面检测可见 Z-fighting = **0**）；移除跨门洞门槛横木、工具间雨棚改为四柱宽中道（留出 `2.0 m` 直行入口）、补齐 `WH↔TR` 与 `TR↔BH` 门洞 `16 cm` 连续地板碰撞、修正仓库/工具间坡道倾角、补齐宿舍 1F/2F 周圈边梁消除楼梯上方透光缝，调整宿舍 1F 餐桌椅与 2F 书架/护栏净空；修复门扇碰撞 `Rotator(yaw=...)` 轴向并补齐 UE 5.8 `GeometryScript_Collision` 烘焙。通过 **23 条几何走廊** + **10/10 真实 Chaos 胶囊体（R=34 cm, H=172 cm）行进扫掠** 全绿校验。
  - **Nanite 架构复查与零撕裂策略**：12 机位原生 `r.Nanite 1` 无头 D3D12 离屏目检确认，多部件独立建筑壳启用 Nanite 在流送压力下会退化为撕裂粗根簇；据此仅对 3 栋单实例主建筑（`SM_LM_Warehouse` 12.3k / `SM_LM_ToolRoom` 14.7k / `SM_LM_Bunkhouse` 22.0k）与 Masked 木屑地垫保持非 Nanite（与村内马厩/铁匠铺/木工坊同标准且节省 Always-Resident Nanite 预算），其余全部 **32/32** 款密集木料/工具/家具/围栏/Quixel 扫描件保持 Nanite 启用（`nanite_fail=0`），并本地克隆启用 `used_with_nanite` 的 `M_LM_Res_Bark`（0 额外贴图、消除运行时 PSO 卡顿）。
  - **木屑地垫二次开发与碎屑边缘打散**：`M_LM_WoodchipMulch`（225 PS 指令 / 4 采样器）改为线性空间校准深褐湿木屑并采用 `BLEND_Masked` + 径向顶点色与木屑纹理驱动的自然打散边缘，配合 `pivot_z_at_ground=True` 贴地微埋，彻底消除硬边贴片感；同时清除东侧劈柴区亮黄碎木片。
  - **院落四区动线、劈柴区、锯具与马厩风木栏**：留出 `5.5 m` 中央主车道与三屋门前空地，清晰划分西侧卸料晾晒区、中棚锯木区、东侧劈柴区（2 处 `SM_LM_ChoppingStation` 橡木桩+铁箍+26° 嵌斧+劈柴）与北门入口；新增 3 把 `SM_LM_TwoManCrosscutSaw`（1 把卡入雨棚原木锯缝、1 把挂工具间加宽后窗实墙架、1 把挂仓库内墙）、2 把 `SM_LM_FramePitSaw` 及 `SM_LM_WorkbenchSawSet`；彻底移除院内残破木栏（`xfrobaziy`）与残破石墙（`r48_stonewall`），以 43 跨顺坡贴地马厩风三横梁木栏 `SM_LM_CampFencePanel` + 3 根收尾柱 + 带斧锯浮雕与双灯的 `5.58 m` 营地门楼 `SM_LM_CampGateArch` 完整围合（外部 PCG 侵入 `0`、围栏顺坡异常 `0`）。全部 **63/63** 新增贴图合规封顶（估算总显存 `20.74 MB`），已发布至正式 `Content` 并编译 `FPSGAMEEditor Win64 Development`，未实机测试。

- **R49c 伐木场 3A 精修、铁链挂灯、雨湿木屑过渡与性能优化（2026-11-26，仅发布院落与地图，完整保留 R50 地形与贴图优化）**：
  - **做旧砍痕木桩 + 项目正式伐木斧**：移除程序生成旧斧与方块劈柴（删除 `SM_LM_ChoppingStation`），在 Blender 5.1 精雕 2 座 60×22 树根外展、干裂深沟、凹陷斧砍痕与紧贴树皮铆钉铁箍的老橡木桩（`SM_LM_ChoppingStumpA/B`，扇形劈柴，入土 `-20 cm`），嵌入 2 把项目正式工具伐木斧 `/Game/Items/ProductionTools/BattleAxe20260919/SM_BattleAxe`（按实测斧刃 `4.6–4.8 cm` 咬合 V 形斧口，另 1 把靠放工具间木工台；`official_battle_axe_instances=3`）。
  - **零悬空铁链/壁挂灯具与村内店铺统一光色**：全部移除悬空光源，接入 `stable_lighting.py` 村内店铺标准硬件（`SM_ChainLink01a` + `M_CarpenterIron` 铆接顶板/弯铁支架，`40` 铁件 + `11` 铁链合批至 2 组静态 ISM、26 m 剔除）与 `SM_Props_Lantern_02A` / `MI_StaffLampWick`，覆盖 14 处实景光源（仓库横梁吊灯 2、工具间横梁吊灯 1 + 南墙实墙支架灯 1、雨棚正中椽梁吊灯 1、宿舍 1F 门厅壁灯/餐桌灯/石壁炉余烬火床、2F 吊灯/桌灯、大门门楼双铁链吊灯、院内双木柱挂钩灯）；14/14 全部复用 `UVillageInteriorLighting::Configure`（`InverseExposureBlend=1.0`、`GlowTint=(1.0, 0.70, 0.32)`、`CastShadows=False`），彻底消除门洞过曝发黄。
  - **雨湿联动木屑贴花与非圆形自然边缘淡出**：删除硬边贴片 `SM_LM_MulchPatch / M_LM_WoodchipMulch / MI_LM_WoodchipMulch`，新建 6 处 `M_LM_WoodchipDecal` 延迟贴花（5 采样器、`1275` PS 指令、`fade_screen_size=0.008`），接入 `/Game/Weather/Materials/MPC_FPS_Weather`（`WeatherWetness`）与驻留 `RoadMix/T_Stony*` 泥地基色/粗糙度，采用 4 阶世界空间域扭曲 FBM + 非对称散落裂叶 + 碎屑高度镂空实现干/雨双态同步湿润反光与自然零硬边淡出，并叠加 5 处 3D 树皮木屑簇（`SM_LM_BarkChipScatterA/B`）；全区 3 栋建筑与全部 HISM 道具关闭 `receives_decals`，杜绝木桩与室内地板串色。
  - **全组件 3A 自检升级与性能收紧**：三屋抬升 `+30 cm`（`FL1=+46 cm`）配 15 cm/级三步石阶与加长平缓货车坡道，彻底消除 1F 地面 Nanite 地形位移穿模；仓库滑轮升级锻铁吊梁套环与三股麻绳、宿舍 1F 石壁炉增设锻铁薪架与发光炭火柴堆、`SM_LM_BunkBed` 重做塌陷棉枕与悬垂毛毯、`SM_LM_SawbuckStation` 重做带节弯曲原木与顺纹橡木滑轨、`SM_LM_TimberRack` 改 1 段精锐榫卯加铁箍并替换为中世纪木箱（移除现代工具箱）。实施智能 Nanite + 3 级自动 LOD 分层（20 款 Quixel 扫描件 + 8 款雕塑/户外件共 **28** 款保持 Nanite 零失败；3 栋主建筑 + 7 款细木条/锯齿/高光边组件改非 Nanite + 3 级自动 LOD，彻底消除木料架远景撕裂并降低常驻 Nanite 内存）；全部 **63/63** 贴图合规封顶且 `never_stream=False`，总估算显存保持 **`20.74 MB`（`+0.00 MB`）**。隔离区 16 机位干/雨双态 D3D12 离屏目检 + 23 条几何走廊 + 10/10 Chaos 胶囊体物理扫掠全部通过（外部 PCG 侵入 `0`），已仅发布院落资产与关卡至正式 `Content` 并校验 `FPSGAMEEditor Win64 Development` 构建，未实机测试。

[主构建入口](../../Tools/WorldGeneration/ForestVillage/author_lumber_mill_r49.py) · [地形与等高线图](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/LumberMill-R49/terrain-plan.png) · [资产源与清单](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/LumberMill-R49/lumber-asset-catalog.json) · [R49b 烘焙与通行校验回执](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMill-R49/authored-r49b.json) · [R49c 3A 精修与校验回执](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMill-R49/authored-r49c.json) · [QA 回执](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMill-R49/qa-audit-r49.json) · [发布与恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMill-R49/published.json) · [改前备份](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMill-R49/Before)

<a id="lumber-mill-quest-r51"></a>

## R51 破败伐木场与「重建伐木场」任务线（`LumberMillQuest-R51`）

### 任务玩法合同（遵循 `TASK-WORKFLOW.md`）

| 字段 | 定义 |
| --- | --- |
| 任务 ID | `village.lumber_mill.rebuild` |
| 实例 ID | `WorldId / Generation`（`ResetVillageUpgrades` 递增 `Generation` 以隔离新轮次） |
| 目标 ID | `accept`（接取任务）、`briefing`（找修女了解情况）、`clear.witches`（0/2）、`clear.dogs`（0/4）、`clear.handbrain`（0/1）、`report`（回修女处汇报并恢复伐木场） |
| 触发与范围 | 仅在 `L_ForestPathVillage` 生效；修复木工工坊（`IsVillageCarpenterRepaired()`）后由服务器权威触发并自动接取；**全队共享** |
| 真实来源 | `ATemperateHillsWorld::LumberMillQuest`（复制状态 + `UTemperateHillsSave`）与 `ULumberMillQuestSubsystem`（服务端刷怪、绑定槽位真实死亡监听与 `ITaskTrackingSource`） |
| 数量与状态 | `accept`/`briefing`/`report` 均 `Target=0`；怪物目标按种计数 `巫婆 0/2`、`感染犬 0/4`、`手脑 0/1`。状态机：`Locked(0) → TalkToNun(1) → ClearMonsters(2) → ReportToNun(3) → Completed(4)` |
| 副作用与去重 | 全在服务器权威入口提交：`AdvanceLumberMillBriefing()` 校验 `TalkToNun`（提前清完全部 7 只怪则直通 `ReportToNun` 避免卡死）；仅绑定槽位 `UMonsterCombatComponent::IsDead()` 推进 `DefeatedMask`（非致死销毁不计数）；`CompleteLumberMillQuest()` 校验 `ReportToNun && DefeatedMask==0x7F` 后原子落盘并切换完整伐木场，重复 RPC 幂等返回 |
| 生命周期 | 完成后追踪栏保留划线 6 秒，任务日志永久保留「已完成」；F6 重置村庄递增 `Generation`、清理怪物并切回破败态 |
| 保存与联机 | 独立 `LumberMillQuestVersion=1` 持久化于 `UTemperateHillsSave`（保留 `VillagePlanVersion=11` 不变）；监听服/单机权威，客机经 `UChapelDialogueComponent::ServerAction` 推进并按复制状态同步破败/恢复表现与 M 键地图指引 |

- **破败伐木场 3A 资产与双态装配**：[build_lumber_mill_ruined.py](../../Tools/WorldGeneration/ForestVillage/build_lumber_mill_ruined.py) 导出 8 件破败网格（`SM_LM_Warehouse_Ruined`、`SM_LM_ToolRoom_Ruined`、`SM_LM_Bunkhouse_Ruined`、`SM_LM_CampGateArch_Ruined`、`SM_LM_CampFencePanel_Ruined`、`SM_LM_TimberRack_Ruined`、`SM_LM_RubblePileA/B`），100% 复用驻留材质（**`+0.00 MB` 显存**）；[author_lumber_mill_r49.py](../../Tools/WorldGeneration/ForestVillage/author_lumber_mill_r49.py) 将 `LumberMill_Compound` 升级为 `LumberMill.Ruin` / `LumberMill.Restored` / `LumberMill.Shared` + `LumberMill.Solid` 双态结构（默认破败无灯，含塌陷屋顶、倒伏马车、缺口木栏与碎石堆；恢复态完整保留 R49c 全部建筑、伐木斧木桩、14 盏铁链/壁挂灯与雨湿贴花）。隔离 Stage 烘焙校验通过：双态 `23/23` 走廊全通、`7/7` 怪物刷点无阻挡、`nanite_ok=32, nanite_fail=0`、总显存保持 `20.74 MB`（[authored-r51.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMill-R49/authored-r51.json)）。
- **怪物配置与 C++ 闭环**：[LumberMillQuestTypes.h](../../Source/FPSGAME/Tasks/LumberMillQuestTypes.h) · [LumberMillQuestSubsystem.h](../../Source/FPSGAME/WorldGeneration/LumberMillQuestSubsystem.h) · [LumberMillQuestSubsystem.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillQuestSubsystem.cpp) 异步预载并在破败伐木场刷新 **2 巫婆**（`AWitchRebuiltMonster`）、**4 感染犬**（`BP_InfectedDog`）、**1 手脑**（`BP_HandBrain`），接入 `BP_MonsterAIController` 与独立 NavInvoker；同步更新 [TemperateHillsWorld.h](../../Source/FPSGAME/WorldGeneration/TemperateHillsWorld.h)、[TemperateVillagePlans.cpp](../../Source/FPSGAME/WorldGeneration/TemperateVillagePlans.cpp)、[ChapelDialogueComponent.cpp](../../Source/FPSGAME/NPC/ChapelDialogueComponent.cpp)、[ColdSteelNpcDialogue.cpp](../../Source/FPSGAME/UI/ColdSteelNpcDialogue.cpp) 与 [ColdSteelWorldMapData.cpp](../../Source/FPSGAME/UI/ColdSteelWorldMapData.cpp)。
- **正式落盘与编译（2026-11-26）**：已通过 [publish_r49.ps1](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMill-R49/publish_r49.ps1) 完成仅限伐木场与地图的定向发布（新增 `8` / 更新 `62` / 跳过 `63`，`OUT_OF_SCOPE=0`，完整保留 `HillsPerfOpt-R50` 地形与贴图优化；R51 改前快照备份于 `F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMill-R49/Before_R51/`），回执见 [published.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMill-R49/published.json)；`FPSGAMEEditor Win64 Development` 编译与链接通过（`BUILD_EXIT=0`）。当前状态：**未实机测试 · 待 NAS 备份**。
- **M 键地图全面升级与伐木场修复后金色补给路线（2026-11-26）**：新增 [LumberMillSupplyRoute.h](../../Source/FPSGAME/WorldGeneration/LumberMillSupplyRoute.h)（直接由 `lumber-road.csv` / `gate-road.csv` + 村庄主街生成 77 节点精确道路折线，全长约 `352 m`），升级 [ForestVillage.cpp](../../Source/FPSGAME/WorldGeneration/ForestVillage.cpp)、[ColdSteelWorldMapData.h](../../Source/FPSGAME/UI/ColdSteelWorldMapData.h) / [ColdSteelWorldMapData.cpp](../../Source/FPSGAME/UI/ColdSteelWorldMapData.cpp)、[SColdSteelWorldMap.h](../../Source/FPSGAME/UI/SColdSteelWorldMap.h) / [SColdSteelWorldMap.cpp](../../Source/FPSGAME/UI/SColdSteelWorldMap.cpp) 与 [SColdSteelMapMarkerEditor.cpp](../../Source/FPSGAME/UI/SColdSteelMapMarkerEditor.cpp)：修复地图网格负取模/零步长隐患、增强 5 m/25 m 等高线与海拔层次着色并补绘伐木场建筑轮廓、补全村庄设施地标与可折叠「地标索引」跳转栏、增加实时昼夜时钟/光标坐标海拔测距与悬停详情卡、并实现伐木场修复后沿道路直达村庄中枢的**多层流光金色路线特效**（首次点亮扫光、4 股流光彗星、方向流箭、18 粒流萤金尘与起终点脉动金环）。当前状态：**未实机测试 · 待 NAS 备份**。

<a id="lumber-mill-ops-r52"></a>

## 伐木场日常作业、17:00 运木马车与 M 键地图全面升级（`LumberMillOps-R52`）

完成伐木场修复后的每日 `50` 木材自动化产运闭环（含联机全员结算、3 名伐木工、模块化运木马车、5 套 3P 专用骨骼动画）及 M 键地图全面升级与金色补给路线 VFX：

- **A. 模块化运木马车与马具（Blender 5.1，`+0.00 MB` 显存）**：
  - 制作源：[build_lumber_wagon_r52.py](../../Tools/WorldGeneration/ForestVillage/build_lumber_wagon_r52.py) → `F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/LumberMill-R49/TransportFBX/`。
  - 无头导入脚本：[author_lumber_ops_r52.py](../../Tools/WorldGeneration/ForestVillage/author_lumber_ops_r52.py)，正式资产落盘至 `/Game/ForestPathStudy/VillageRegion/LumberMill/Transport/`（`SM_LM_TimberWagon_Chassis`、`SM_LM_TimberWagon_FrontAxle`、`SM_LM_TimberWagon_Wheel`、`SM_LM_TimberWagon_TimberLoad`、`SM_LM_HorseHarness`，100% 复用常驻橡木/锻铁/黄铜/缰绳/马具皮革材质，零新增贴图；底盘与原木堆配精确 Chaos 简单盒碰撞，`TimberLoad` 启用 Nanite，其余动态件配 3 级 LOD）。
- **B. 5 套伐木工 3P 专用骨骼动画（精确 Jason / `SK_Smith_Body` 骨架，0.0 cm IK 误差）**：
  - 由 [author_lumber_ops_r52.py](../../Tools/WorldGeneration/ForestVillage/author_lumber_ops_r52.py) 经 UE 5.8 原生 `AnimPoseExtensions` + 解析二骨手臂 IK + 双脚落地锁定烘焙至 `/Game/ForestPathStudy/VillageRegion/LumberMill/Animations/`：`A_LJ_ChopTree_Loop`（1.60 s）、`A_LJ_SplitLog_Loop`（1.50 s）、`A_LJ_SawLog_Loop`（1.20 s）、`A_LJ_CarryLog_Walk`（1.50 s，继承 `J_MF_Unarmed_Walk_Fwd` 下半身零滑步）、`A_LJ_DriveWagon_Idle`（3.00 s，继承 `A_Rest_Bench_Idle` 坐姿双手拉缰）。
- **C. 日常排班、3 名伐木工、17:00 运木马车与联机全员每日 +50 木材结算**：
  - 新增源码：[LumberjackAnimInstance.h](../../Source/FPSGAME/WorldGeneration/LumberjackAnimInstance.h) / [.cpp](../../Source/FPSGAME/WorldGeneration/LumberjackAnimInstance.cpp) · [LumberMillWorkerActor.h](../../Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.h) / [.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.cpp) · [LumberMillTimberWagon.h](../../Source/FPSGAME/WorldGeneration/LumberMillTimberWagon.h) / [.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillTimberWagon.cpp) · [LumberMillOperationsSubsystem.h](../../Source/FPSGAME/WorldGeneration/LumberMillOperationsSubsystem.h) / [.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillOperationsSubsystem.cpp)。
  - **09:00–17:00 作业**：3 名不同外貌伐木工（均复用 `SK_Smith_Body` + 独立工匠头/工装/草帽）分别执行林缘砍树与木桩劈柴（`SM_BattleAxe` + 击打帧同步 `P_Destruction_Wood` 木屑与 `SC_Hatchet_Hit` 音效）、工具棚锯木架拉锯（`SM_LM_TwoManCrosscutSaw`）及扛木搬运装车（`SM_PoplarLog_Solid_A`）。夜间回宿舍隐身休整零开销，45 m 外自动剔除粒子与音效。
  - **17:00 运木抵村与全员入仓**：3 号工人登座驾车（动态皮革双缰连接 `SK_StableWarhorse` 衔铁，前轴随路况转向、四轮按里程滚转、坡面贴合、空间马蹄声），沿 352 m [LumberMillSupplyRoute.h](../../Source/FPSGAME/WorldGeneration/LumberMillSupplyRoute.h) 运抵村庄中枢卸货后，**房主与全部连入队友各自个人主仓库均获得 +50 `wood`**（[ColdSteelWarehouseModel.cpp](../../Source/FPSGAME/UI/ColdSteelWarehouseModel.cpp) / [ColdSteelPlayerProfileAdmission.cpp](../../Source/FPSGAME/Multiplayer/ColdSteelPlayerProfileAdmission.cpp)，`Container=""` 免疫储物箱/马背袋干扰，`CampfireInventoryRevision` 防回滚，`PendingLumberWood` 满仓暂存腾位自动补发，`UTemperateHillsSave` `CurrentLumberMillQuestVersion=2` 持久化 `LumberMillLastSettledDay` 支持跳日补结且防重复）。
- **D. M 键地图全面升级与金色补给路线 / 马车实时追踪 VFX**：
  - 源码：[ColdSteelWorldMapData.h](../../Source/FPSGAME/UI/ColdSteelWorldMapData.h) / [.cpp](../../Source/FPSGAME/UI/ColdSteelWorldMapData.cpp) · [SColdSteelWorldMap.h](../../Source/FPSGAME/UI/SColdSteelWorldMap.h) / [.cpp](../../Source/FPSGAME/UI/SColdSteelWorldMap.cpp) · [SColdSteelMapMarkerEditor.cpp](../../Source/FPSGAME/UI/SColdSteelMapMarkerEditor.cpp)。
  - 等高线（5 m/25 m）与高程色调分层、建筑屋顶描边、8 类分级地标与全村设施状态、冷钢顶栏/图层开关/可折叠快速定位列表/悬停测绘遥测卡；伐木场修复后解锁沿道路的 10 层动态金色补给线流光特效，并在 17:00 运输途中实时渲染脉冲金色「运木马车」移动标记。
- **落盘与恢复**：新增 10 份独立 `.uasset` 发布回执见 [published.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R52/published.json)（`total=10 new=10 modified=0`，零触碰 R50/R52/R53 地形与贴图包），烘焙与 IK 精度回执见 [authored-ops-r52.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R52/authored-ops-r52.json)。当前状态：**未实机测试 · 待 NAS 备份**。

<a id="lumber-mill-polish-r54"></a>

## 残破伐木场零悬空精修、巫婆布料尖刺根治、高级金色补给线/浮窗升级与任务完成自动取消追踪（`LumberMillPolish-R54`）

针对用户实测反馈的 5 项视觉与交互问题完成根因定位、后台重烘发布与 `FPSGAMEEditor Win64 Development` 编译（`BUILD_EXIT=0`）：

- **1. 残破伐木场悬空组件全面排查与零悬空重烘**：
  - 网格源修复（[build_lumber_mill_ruined.py](../../Tools/WorldGeneration/ForestVillage/build_lumber_mill_ruined.py) → 重导全部 8 件 `RuinedFBX`）：彻底删除 `SM_LM_CampFencePanel_Ruined` 右侧无立柱悬空横木（`CFR_Rail2R` / `CFR_Rail0B`），改为单柱自支撑断裂护栏（`CFR_PostL` 埋深至 `-63 cm`，横木斜插泥地 `-10 cm`，散木半埋 `-4 cm`）；`SM_LM_CampGateArch_Ruined` 加深石墩至 `-74 cm` 并补齐东柱与门梁 0 缝搭接；修复 `SM_LM_Bunkhouse_Ruined` 门廊断柱 72 cm 悬空、`SM_LM_ToolRoom_Ruined` 砸塌工作台反向倾斜与雨棚落木、`SM_LM_Warehouse_Ruined` 屋内悬浮梁与倒地门板、断桁架 `RafBrkB` 悬空端、`SM_LM_TimberRack_Ruined` 悬空散板及 `SM_LM_RubblePileA/B` 碎石基底埋深。
  - 院落装配与自动门禁（[author_lumber_mill_r49.py](../../Tools/WorldGeneration/ForestVillage/author_lumber_mill_r49.py)）：`place_on_z` 改用 8 顶点旋转精确 AABB 底高与地形 5 点采样最低值（修正全部翻倒马车、手推车、木桶、桌椅、车轮的旋转贴地）；`add_ruined_fence_run` 强制缺口前一段自动使用自支撑残破围栏；新增 `ZERO-FLOATING GROUND AUDIT` 硬门禁，离屏 Stage 烘焙校验 **`270 / 270` 零悬空**（`floating_count=0`，`max_gap_cm=-0.1 cm`），`WALKABILITY_AUDIT` **`all_clear=True / blockers=0`**，`VRAM_AUDIT` **`nanite_fail=0 / textures_uncapped=0`**；发布前已同步正式图保留 R50/R52/R53 优化。
- **2. 巫婆模型向上尖刺根因定性与彻底修复**：
  - **结论：100% 为衣物 `Chaos Cloth` 仿真/LOD 绑定异常，非基础身体/帽子/动画/材质问题**（Blender 5.1 离线核验 `SK_WitchRebuilt.fbx` 及全部 8 组动画，0 无权重顶点、高度严格 `[-0.018, 2.022] m`、材质 0 WPO）。
  - 源码根治（[WitchMonster.cpp](../../Source/FPSGAME/Monsters/WitchMonster.cpp) · [WitchRebuiltMonster.h](../../Source/FPSGAME/Monsters/WitchRebuiltMonster.h) / [.cpp](../../Source/FPSGAME/Monsters/WitchRebuiltMonster.cpp) · [WitchRebuiltAuthoring.cpp](../../Source/FPSGAME/Monsters/WitchRebuiltAuthoring.cpp) · [LumberMillQuestSubsystem.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillQuestSubsystem.cpp)）：关闭 `bCollideWithEnvironment`（阻断裙摆粒子与丘陵地形/HISM 碎石挤压向上弹射）；`BeginPlay` 先挂起布料并执行 `ForceClothNextUpdateTeleportAndReset()` 且收紧瞬移阈值（`90 cm / 35°`）；`Tick` 改为先锁定 `LOD 0` 并确认 `GetPredictedLODLevel() == 0` 后才恢复布料仿真（杜绝未稳定化的 LOD1/LOD2 高重心系数映射瞬时飞针）；新增运行时包围盒发散熔断保护（`BoxExtent.Z > 220 cm` 瞬时重置）；同步扩充编辑器 `BindToSkeletalMesh` 全 LOD 稳定化与 `LumberMillQuestSubsystem` 巫婆完整资产预载。
- **3. M 键地图金色补给路线高质感升级（[SColdSteelWorldMap.cpp](../../Source/FPSGAME/UI/SColdSteelWorldMap.cpp)）**：
  - 引入 4 倍细分的 Catmull-Rom 丝滑曲线拟合；改版为 3A 烫金古舆图商路：柔和纸面投影 + 呼吸暖金微光 + 暗铜墨底描边 + 平行双线古金细边轨 + 缎金主带 + 呼吸香槟丝芯 + 每 16 m 细刻里程刻度 + 3 道 16 段渐隐珠光流彗（配切线对齐菱形星芒）+ 14 枚纤细菱形微光尘（取代粗十字星）+ 起终点双环公会徽记与四向罗盘刻度 + 精致运木马车徽章（支持悬停点击追踪）。
- **4. M 键地图悬停浮窗格式与字体样式升级（[SColdSteelWorldMap.cpp](../../Source/FPSGAME/UI/SColdSteelWorldMap.cpp)）**：
  - 拆分 `TitleFont`（16 px Bold）、`BodyFont`（13 px Regular）、`BadgeFont`（11 px SemiBold）与 `Number` 字体层次；升级为带双层阴影、顶部强调条、四角微框、分类标签胶囊 + 右对齐语义状态徽章（`已贯通` / `运输中` / `已修复` / `待修复`）、蚀刻分隔线、多行结构化说明及暗底遥测脚栏（距离/方位/海拔 + 左键操作提示）的冷钢精绘卡片，新增运木马车专属悬停卡。
- **5. 任务完成后自动取消追踪**：
  - 源码（[TaskTrackingSubsystem.h](../../Source/FPSGAME/Tasks/TaskTrackingSubsystem.h) / [.cpp](../../Source/FPSGAME/Tasks/TaskTrackingSubsystem.cpp) · [ColdSteelDungeonTracker.cpp](../../Source/FPSGAME/UI/ColdSteelDungeonTracker.cpp) · [LumberMillQuestSubsystem.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillQuestSubsystem.cpp)）：新增 `UTaskTrackingSubsystem::ClearSelectedTask(...)`；`UColdSteelDungeonTracker::RefreshTracking()` 检测到任意已追踪任务进入 `ETrackedTaskState::Completed` 时自动解除追踪并清理持久化配置（J 键日志仍保留已完成记录）；伐木场任务完成时同步清零残留 `ShowCompletionUntil` 并立即取消追踪。
- **落盘与恢复**：Stage 校验回执 [authored-r51.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMill-R49/authored-r51.json) · 发布回执 [published.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMill-R49/published.json)。当前状态：**未实机测试 · 待 NAS 备份**。

<a id="lumber-mill-fix-r55"></a>

## `X=135, Y=251` 道路接缝统一、伐木工完整模型与人体工学动作重制及伐木斧材质修复（`LumberMillFix-R55`）

针对实测反馈的 5 项伐木场与林道问题完成根因实证、C++/美术管线修复、离屏 GPU Stage 重烘与 `FPSGAMEEditor Win64 Development` 编译（`BUILD_EXIT=0`）：

- **1. `X=135, Y=251`（`Y=+252 m` 边界）地面分割线与两侧材质/PCG 统一**：
  - **材质与地形层根因**：`Y=+252 m` 为 `L_ForestPathForest` Landscape（`MI_ForestVillageLandscape`）与外围 `SM_ForestGround_05_04`（`MI_ForestTilePacked`）交界；R49 `WriteLumberLandscapeLayer` 仅在新建编辑层写入 `C_LayerInfo=255`，未清零底层 `Layer` 的 `AutoMaterial_LayerInfo=255`，经 `FinalWeightBlending` 归一化后 `Y<252 m` 整段林道与院地被稀释为 `C=0.498 / AutoMaterial=0.498`（混入 50% 苔草），而北侧 `Y>=252 m` 为 `1.000` 纯路；同时 `M_ForestVillageLandscape` 的 `MF_TrailDirt.RoadWeight` 引脚悬空。
  - **修复与实证**：[ForestVillageCliffs.cpp](../../Source/FPSGAME/WorldGeneration/ForestVillageCliffs.cpp) 在写入 `C_LayerInfo` 时同步将底层持久化编辑层的竞态权重层钳制至 `<= 255 - PaintWeights`；离屏 D3D12 GPU 合并后实测 **`seam(135,251)` 与 `yard(154,62)` 由 `C=0.498/Auto=0.498` 转为 `C=1.000/Auto=0.000`**（路外草地 `grass(120,251)` 维持 `C=0.000/Auto=1.000`），重烘 Landscape Nanite 与 `MapRoadPaint`；`M_ForestVillageLandscape` 接入 `LandscapeLayerSample("C") -> MF_TrailDirt.RoadWeight`（保留 `enable_tessellation=False` 及 R52 着色器早退），`MF_TrailDirt` 默认 `PreviewValue=(1,1,1,1)`。
  - **PCG 接缝羽化**：[prepare_lumber_road_dressing_r49.py](../../Tools/WorldGeneration/ForestVillage/prepare_lumber_road_dressing_r49.py) 对 `Y=+252 m` 处骤断的 `HillsLandscape` 林下榛灌与地表蕨类/落枝（`SM_rbcuh`/`SM_rbpiR`/`xisgcic`/`xjiifd1`/`relu7`/`rioqm`）在 `X∈[105..168] m, Y∈[236..252] m` 增加 `+209` 个波浪边界有机羽化点（接缝两侧密度 `234 vs 291`，避让路面与既有树干），同步保留 R48b 剔除与 R52 `WPO` 禁用优化（`r52_wpo_tuned=76`）。
- **2. 伐木工缺失脸部与腿部修复**：
  - 根因为 [LumberMillWorkerActor.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.cpp) 与 [LumberMillOperationsSubsystem.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillOperationsSubsystem.cpp) 中 3 条头部/工装路径拼写失效（仅剩 `SK_Smith_Body` 裸臂颈脚）。全部更正为实盘校验路径（`SK_MasterArtisan_Head`、`Outfit/SK_Carpenter_Workwear`、`SK_Gunsmith_Head`），移除穿模草帽并增加缺载报错日志。
- **3. 5 套伐木工 3P 动作人体工学重制、真实立树判定与扛木零穿模**：
  - **骨架左右手系修正与自然动作**：[author_lumber_ops_r52.py](../../Tools/WorldGeneration/ForestVillage/author_lumber_ops_r52.py) 实测 `SK_Smith_Body` 左右手系（`+X=左, -X=右, +Y=前`，`right_sign=-1`），改用基于 `J_MM_Idle`/`A_Rest_Bench_Idle` 标定的解剖铰链平面 2-Bone IK、锁骨随动、腕部限位与 Jason V9 前臂/上臂扭转骨分配（`lowerarm_twist_01=80%`、`02=40%`、`upperarm_twist_01=-45%`），5 套新动作全部 `0.00 cm` IK 误差：`A_LJ_ChopTree_Loop`（54f，肘 `63.3°–110.4°`）、`A_LJ_SplitLog_Loop`（48f，肘 `17.8°–129.2°`）、`A_LJ_SawLog_Loop`（42f，肘 `64.2°–99.8°`）、`A_LJ_CarryLog_Walk`（45f，肘 `49.0°–109.7°`，3D 头部净空 `8.00 cm` / 颈部净空 `9.42 cm`）、`A_LJ_DriveWagon_Idle`（90f，肘 `88.4°–95.2°`）。
  - **真实立树砍伐与工具/座椅校准**：[LumberMillOperationsSubsystem.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillOperationsSubsystem.cpp) 新增 `FindNearbyStandingTree()` 与 `VerifyStandingTreeNearby()`，动态探测北门外真实鹅耳枥树干并按射线实测树皮半径定位站位与击打点，未命中真实立树时禁止空砍并回退至木桩劈柴；[LumberMillWorkerActor.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.cpp) 校准双人锯垂直木柄握持、战斧斧柄对齐、肩外侧扛木防穿模（缩放 `1.20×0.56×0.56`，外移 `+9 cm`/抬高 `+11.5 cm`）、2 号工休整不悬空木块及马车坐高偏移（`+37 cm`）。
- **4. 木桩白模伐木斧修复与伐木场全量材质门禁**：
  - 全量 86 件网格排查确认仅 `SM_BattleAxe` 因放入 HISM 而其武器母材质（`M_ToolHead_Master_Axe`/`M_BattleAxe`）未启用 `bUsedWithInstancedStaticMeshes` 退化为默认白模；[author_lumber_mill_r49.py](../../Tools/WorldGeneration/ForestVillage/author_lumber_mill_r49.py) 将 3 处伐木斧改为独立静态网格组件（零改动玩家武器资产）并新增 `MATERIAL_USAGE` 硬门禁，校验 **`124` 组件 / `385` 材质槽 `0` 异常**、`GROUNDING` **`269/269` 零悬空**、`WALKABILITY` **`all_clear=True`**、5 件运木马车材质槽 `0` 异常。
- **落盘与恢复**：回执与前版本 SHA-256 备份位于 [LumberMillFix-R55/published.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillFix-R55/published.json)（`25` 份正式资产）、[seam-audit.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillFix-R55/seam-audit.json) 与 [animations-audit.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillFix-R55/animations-audit.json)。当前状态：**未实机测试 · 待 NAS 备份**。

<a id="lumber-mill-wagon-fix-r56"></a>

## 运木马车模型、马具、车夫坐姿与行驶物理全面排查修复（`LumberMillWagonFix-R56`）

围绕 17:00 运木马车的 5 件模块化网格、挽具/战马贴合、车夫坐姿动作、动态缰绳、上下坡铰接及停放净空完成全量实测排查、重建修复与校验（`VERIFY_WAGON_R56_PASS`、`BUILD_EXIT=0`）：

- **1. 车夫驾驶室与坐姿脚踏板 IK 修复（原脚穿踏板 `17.7 cm`、脚尖穿出前挡板）**：
  - [build_lumber_wagon_r52.py](../../Tools/WorldGeneration/ForestVillage/build_lumber_wagon_r52.py) 扩深驾驶室：座面顶 `Z=136 cm`、双板脚踏 `Z=94 cm`（`42 cm` 垂直腿部空间）、前挡板前移至 `X=163 cm`（前倾 `16°`，内面 `X>=154.5 cm`），并增设锻铁挂钩固定原悬空的左侧盘绳 `SideTowRope`。
  - [author_lumber_ops_r52.py](../../Tools/WorldGeneration/ForestVillage/author_lumber_ops_r52.py) 为 `A_LJ_DriveWagon_Idle` 接入双腿脚踏板 2-Bone 铰链平面 IK 与驾驶室硬门禁：实测靴底 **`Z=94.00 cm`**（零下陷）、脚尖 `X=151.88 cm`（距前挡板 `+2.62 cm`）、膝 `91.5°`、肘 `91.5°–98.0°`、`IK 误差 0.00 cm`。
- **2. 转向截断式底盘、后栏杆穿木、车轴轮毂重叠与捆绳穿侧板修复**：
  - 前轮缩放由 `0.80` 调为 `0.72`（顶高 `74.88 cm`），主纵梁抬升至底面 `Z=78.5 cm`（`+3.62 cm` 净空），前上枕木收窄至 `Y=±32 cm`（`±35°` 满舵转向仍具 **`+4.06 cm`** 净空，原 `15°–30°` 深切纵梁 `14.8 cm`）。
  - 移除穿插底层 4 根原木的 `RearGuardBar`，改用齐平尾梁加外侧铁角撑；前后车轴木肩分别收至 `±62/±60 cm` 配铁垫圈消除轮毂重叠（`+2.2/+3.5 cm`）；`TimberLoad` 捆绳绕行侧板与上栏杆外侧（`Y=±73.2 cm`）。
- **3. 战马挽具按 `SK_StableWarhorse` 万面实测轮廓重塑 + 辕杆防踢蹄**：
  - 拉马距前轴前移 `+33 cm` 至 `218 cm`，横木（`Singletree`）位于马系 `X=-152 cm`（距步行马尾 `+19.0 cm`、后蹄 `+21.8 cm`，原被踢穿 `14 cm`）。
  - 基于 `SK_StableWarhorse.fbx`（`10,607` 顶点，含原鞍座与马镫 `|Y|_max=44.6 cm`）实测截面重构 `SM_LM_HorseHarness`：鞍垫与肚带移至鞍座凹槽 `X=-8 cm`（顶/侧/腹净空 `+2.71/+1.99/+2.23 cm`），颈圈贴合肩颈斜度，臀带后移至 `X=-104.5 cm`（净空 `+5.85 cm`），辕杆扩至 `Y=±49.5 cm`（内壁净空 `+9.51 cm`），与前轴拖环/拉绳扣实现 `0.00 cm` 对齐。
- **4. 双段缰绳、上下坡辕杆铰接与场院停放防穿模**：
  - [LumberMillTimberWagon.h](../../Source/FPSGAME/WorldGeneration/LumberMillTimberWagon.h) / [.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillTimberWagon.cpp)：改用双段铰接缰绳（车夫双手 → 鞍垫铜环 `ReinTerret` → 马口衔铁，`0.0 cm` 悬空偏移，卸货待命期间保持显隐连续）；`FrontAxlePivot` 沿坡度绕前轴 Y 轴铰接俯仰（`±12°`）并叠合马匹四蹄坡角，消除坡道 `15.9 cm` 垂直脱离且前轮零抬离。
  - [LumberMillOperationsSubsystem.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillOperationsSubsystem.cpp)：场院停放位由 `160 cm` 前移至 `320 cm`（尾木距 `SM_LM_ToolRoom` **`+135.9 cm`**，原重叠 `24 cm`；马鼻距北门 `+399.0 cm`），并修正 2 号搬运工从马车东侧（`+150, 310`）装车以消除穿车路径。
- **落盘与恢复**：6 份正式资产（5 件 `Transport` 网格 + `A_LJ_DriveWagon_Idle`）经 SHA-256 改前备份与原子发布，回执及离线净空审计位于 [LumberMillWagonFix-R56/published.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillWagonFix-R56/published.json)、[clearance-audit-r56.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillWagonFix-R56/clearance-audit-r56.json) 与 [verify-wagon-r56.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillWagonFix-R56/verify-wagon-r56.json)。当前状态：**未实机测试 · 待 NAS 备份**。

<a id="lumber-mill-ops-r57"></a>
### R57 东门自动开关、酒馆夜宿、入侵受阻红线告警与木材顶部提示优化（2026-11-27）

- **城门自动开关**：为木门 [VillageDefenseGate.cpp](../../Source/FPSGAME/WorldGeneration/VillageDefenseGate.cpp) 与升级石城铁闸 [HighVillageDefense.cpp](../../Source/FPSGAME/WorldGeneration/HighVillageDefense.cpp) 补齐幂等权威 `SetDoorOpen(bool)` / `IsDoorOpen()`；[LumberMillOperationsSubsystem.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillOperationsSubsystem.cpp) 距东门 16 m 提前开启、未开完平滑等待、车尾通过 9.5 m 后自动关闭。
- **酒馆门前终停、入内夜宿与入侵受阻拦截**：[LumberMillSupplyRoute.h](../../Source/FPSGAME/WorldGeneration/LumberMillSupplyRoute.h) 将路线延至酒馆正门外 5.6 m 宽 `hall_road` 空地；马车停靠后运输工沿正门进入酒馆坐于真实圆凳过夜（复用常驻 `A_Rest_Bench_Idle`，`+0.00 MB` 增量）；次日 `06:00` 后仅当夜间入侵结束且 [HillsNightRaidSubsystem.cpp](../../Source/FPSGAME/WorldGeneration/HillsNightRaidSubsystem.cpp) `HasUnresolvedInvasion() == false` 才返营；入侵未清时暂停发车与每日 `+50` 木材（含过日补领拦截与错过 `18:50` 窗口作废），并在 [SColdSteelWorldMap.cpp](../../Source/FPSGAME/UI/SColdSteelWorldMap.cpp) 切换为深红告警路线、红色沿线封锁 `×` 标、红色浮窗与地图状态条。
- **顶部木材提示修复**：修复 [ColdSteelWarehouseModel.cpp](../../Source/FPSGAME/UI/ColdSteelWarehouseModel.cpp) 与 [ColdSteelPlayerProfileAdmission.cpp](../../Source/FPSGAME/Multiplayer/ColdSteelPlayerProfileAdmission.cpp) 传入 `TEXT("wood")` 无扩展名导致显示字面量 `"wood "` 且无图标的缺陷，改为真实贴图 `Icons/wood.png`（44 px）并升级为 FIFO 队列 `PostBannerNotice()`（[ColdSteelAreaPickup.cpp](../../Source/FPSGAME/UI/ColdSteelAreaPickup.cpp)）与 E 盘 `game-dev` 四级语义配色（[ColdSteelProgressNotification.cpp](../../Source/FPSGAME/UI/ColdSteelProgressNotification.cpp)）。

<a id="lumber-mill-ops-r58"></a>
### R58 伐木工动作/腋下衣物防拉丝、木桩动态劈柴裂块、锯木对位与地面贴花防覆盖（2026-11-27）

- **玩家 3P 伐木动作排查结论**：玩家装备 `tool_axe` 使用独立第一人称骨骼视模 `SK_Harvest_Axe` + `A_Harvest_Axe_Swing` 经 [FPSPlayerBodyMotion.cpp](../../Source/FPSGAME/Characters/FPSPlayerBodyMotion.cpp) `NativeMelee` 驱动第三人称双手腕与 15 指关节，未与伐木工 `A_LJ_*` 共享动画。
- **腋下衣物扭曲拉丝与手部握持穿模根治**：定位到 `SK_Smith_Body` 自带 MetaHuman 后处理纠正蓝图 `ABP_Smith_R4_Correctives`，此前 [author_lumber_ops_r52.py](../../Tools/WorldGeneration/ForestVillage/author_lumber_ops_r52.py) 覆盖 `upperarm_twist_01`/`lowerarm_twist_01/02`（抹除了 28°–36° 绑定旋转）且 `SplitLog` 高举至 `Z=178 cm`（肩抬 >140°）引发腋下撕裂；R58 移除所有扭转骨覆盖、锁骨微抬收束至 ≤8°、全动作肩抬压至 `78.5°–96.2°`，并改用「握拳掌心中心反推手腕」IK 与 [LumberMillWorkerActor.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.cpp) `ComputePalmGripCenter()`（读取 `middle_01_palm`/`middle_01_mcp`），斧柄与锯把零穿手腕/手掌。
- **木桩静态斧动态隐藏 + 劈柴裂成两半落地**：Blender 5.1 脚本 [build_lumber_split_log_r58.py](../../Tools/WorldGeneration/ForestVillage/build_lumber_split_log_r58.py) 构建咬合两瓣原木 `SM_LM_SplitLog_HalfL/R`（各 236 面、复用 `M_LM_Res_Bark`/`M_CarpenterSawn`/`M_CarpenterCut`，`+0.00 MB` VRAM）；伐木工在木桩作业时自动隐藏木桩静态 `SM_BattleAxe` 并立放原木，劈中帧（`u=0.44`）裂为两瓣翻滚弹落地面并留存至多 3 组。
- **屋檐下锯木工对位与静态拉锯冲突消除**：Worker 1 移至锯缝法向 `(161.3, -20.4)` 面朝 `-82°` 直对锯架真实锯缝 `(179.7, -151.1, +95 cm)`，双手叠握竖直木柄（零穿铁夹/锯刃），锯木作业期间自动隐藏 `LumberMill_Compound` 锯架上对应 HISM 静态拉锯实例，离岗自动恢复。
- **木桩地面木屑材质覆盖玩家鞋腿修复**：为玩家本体 [FPSPlayerBodyComponent.cpp](../../Source/FPSGAME/Characters/FPSPlayerBodyComponent.cpp)、一视角下肢 [FPSPlayerFirstPersonBody.cpp](../../Source/FPSGAME/Characters/FPSPlayerFirstPersonBody.cpp)、模块化服装（鞋/裤/衣）[FPSModularOutfitComponent.cpp](../../Source/FPSGAME/Characters/FPSModularOutfitComponent.cpp)、外装 [FPSPlayerBodyEquipment.cpp](../../Source/FPSGAME/Characters/FPSPlayerBodyEquipment.cpp)、伐木工、马车及伐木场全体静态/HISM 道具统一设置 `SetReceivesDecals(false)`，并在 [LumberMillQuestSubsystem.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillQuestSubsystem.cpp) 与 [author_lumber_mill_r49.py](../../Tools/WorldGeneration/ForestVillage/author_lumber_mill_r49.py) 将 `M_LM_WoodchipDecal` 投影深度由 `55 cm` 压紧至 `12 cm` 仅贴地。
- **构建、发布与恢复**：7 份正式资产（`SM_LM_SplitLog_HalfL/R` + 5 套重烘 `A_LJ_*` 动作）经 SHA-256 改前备份与原子发布，回执位于 [LumberMillOps-R58/published.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R58/published.json) 与 [authored-ops-r58.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R58/authored-ops-r58.json)；`FPSGAMEEditor Win64 Development`（R57 + R58 合编）已通过，日志位于 [build-20261127-132553.log](../../Saved/BuildEditor/build-20261127-132553.log)。当前状态：**未实机测试 · 待 NAS 备份**。

<a id="lumber-mill-ops-r62"></a>
### R62 运木马车可站立乘车（双端联机零抖动）与全链路联机/性能专项审计（2026-11-27）

针对需求“调整运输马车可站人随车往返伐木场，并全量复核本轮功能遗漏、Bug、联机同步与性能友好度”，完成马车可乘载碰撞重构与双端/性能专项修复（纯 C++ 改造，+0.00 MB 显存，未改 `.umap` 与既有资产包）：

- **1. 运木马车可站人随车同行（[LumberMillTimberWagon.h](../../Source/FPSGAME/WorldGeneration/LumberMillTimberWagon.h) / [LumberMillTimberWagon.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillTimberWagon.cpp)）**：
  - 根治旧版无法入斗站立原因：`SM_LM_TimberWagon_Chassis` 烘焙的整体盒碰撞占据 `Z = 40..152 cm` 封死了 `Z = 95 cm` 货床内部。现将 `ChassisMesh`/`TimberLoadMesh` 降为 `QueryOnly`（仅保留 `ECC_Visibility` 射线命中），改由挂于 `WagonRoot` 的 9 组定名 `UBoxComponent` 默认子对象精确承载玩家碰撞（`MovementBaseUtility::UseRelativeLocation()` 房主/客机均生效、`ECC_Camera` 忽略防穿镜头）：
    - `BedWalkDeck`：空车态精准贴合橡木货床顶面 **`Z = 95.0 cm`**（`X ∈ [-146..+88], Y ∈ [-62..+62]`）；满载原木态动态切至木垛顶面 **`Z = 156.0 cm`**（站立玩家顶高 `332 cm <` 石城铁闸 `340..480 cm` 净空），若玩家在装木瞬间已在车斗内自动平稳托升至木垛顶面杜绝卡木。
    - `RearLowerStep`（顶 `36 cm`）+ `RearUpperStep`（顶 `72 cm`）：两级尾步台阶全部满足 `ΔZ <= 40 cm`（`FPSCharacterMovementComponent::MaxStepHeight`），玩家既可直接从车尾走上货床，也可从任意方向起跳登车。
    - `SideGuardL/R`（`Y = ±68 cm, Z = 95..165 cm`）、`DriverSeatDeck`（顶 `136 cm`）、`DriverFootboardDeck`（顶 `94 cm`）、`FrontDashGuard` 与 `UndercarriageBox`：弯道防滑落、前挡防误踩马背、底盘防地面穿车。
  - **零抖动移动平台与 180° 掉头保护**：`PrimaryActorTick.TickGroup = TG_PrePhysics` + `SyncRidingCharacterTickOrder()` 为当前立足马车的玩家 `UCharacterMovementComponent` 自动挂接 `AddTickPrerequisiteActor(this)`（离车/销毁清理），确保马车先更新位姿再执行玩家 `UpdateBasedMovement`；酒馆清晨 `ParkedAtTavern → ReturningToMill` 180° 原地掉头帧自动按马车局部坐标整体随转乘车玩家并刷新 `SaveBaseLocation()`，避免 `UpdateBasedMovement` 直线扫掠撞进 `DriverSeatDeck`。
- **2. 联机同步与性能专项修复（[LumberMillTimberWagon.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillTimberWagon.cpp)、[LumberMillWorkerActor.h](../../Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.h)/[.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.cpp)、[LumberMillOperationsSubsystem.h](../../Source/FPSGAME/WorldGeneration/LumberMillOperationsSubsystem.h)/[.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillOperationsSubsystem.cpp)）**：
  - **马车双端同步精度与停靠零耗**：房主 `VisualDistanceCm` 直随权威 `NetState.DistanceCm`（消除原 `FInterpTo(12)` 产生的 `32 cm` 稳态滞后）；客机改用速度前馈 + 残差 PD 纠偏（稳态漂移由 `~64 cm` 压至 `< 1 cm`）且补齐晚加入首包即刻对齐（`bHasInitialNetSync`）；行驶中动态 `12 Hz`、停靠期降频至 `1 Hz`；停靠落稳后跳过每帧 `ApplyRoutePose` 与 6 次 `SampleGroundZ` 地形采样。
  - **车夫/伐木工客机防抖与平滑行进**：覆写 `ALumberMillWorker::OnRep_ReplicatedMovement()`，车夫驾车时忽略服务器世界位姿快照避免每 `166 ms` 与客机本地 `DriverSeatAnchor` 互抢位置，同时将车夫 Tick 排在马车之后并即时 `RefreshDynamicReins()` 消除高速行进 1 帧缰绳滞后；自由步行期动态 `10 Hz` + 客机平滑插值，静置/作业/休息期降频至 `2 Hz`；`UpdateDynamicToolTransform` 在专用服务器早退。
  - **消除三处热路径 `TActorIterator` 扫描**：缓存 `LumberMill.R49` 院落（`ALumberMillWorker::CachedCompoundActor` + `1 s` 冷却，消除未流送前每帧全图扫 Actor）、缓存东门（`CachedEastGate` + `1 s` 冷却）、缓存酒馆正门（`CachedTavernDoor` + `1 s` 冷却）以及缓存客机端 `ResolveWagonActor()`（消除客机开 M 键大地图每帧两次 `TActorIterator<ALumberMillTimberWagon>`）。
- **构建与验证状态**：`FPSGAMEEditor Win64 Development` 编译与全模块 DLL 链接通过（`BUILD_EXIT=0`），已于 [UnrealEditor-FPSGAME.dll](../../Binaries/Win64/UnrealEditor-FPSGAME.dll) 二进制验证 `BedWalkDeck`、`RearLowerStep`、`RearUpperStep`、`SideGuardL`、`FrontDashGuard`、`UndercarriageBox`、`SyncRidingCharacterTickOrder`、`RefreshDynamicReins` 全部符号落盘。当前状态：**未实机测试 · 待 NAS 备份**。

<a id="lumber-mill-ops-r61"></a>
### R61 酒馆东侧马车停靠改位、双开门自动开关联动与自然坐姿重构（2026-11-27）

针对实测反馈“运木马车停靠挡在酒馆门口、运输工穿门进入酒馆、酒馆休息坐姿僵硬且错位”的问题，完成酒馆东侧（拴马位对侧）泊车改位、实体双开门联动及专用酒馆休息坐姿重构：

- **1. 马车停靠位迁至酒馆东侧（拴马位对侧，彻底让开正门）**：
  - 核查酒馆测绘平面确认西侧 `Tavern local X = [-675..-10], Y = [-1090..-818]` 为三马位拴马桩，正门双开门在 `X = [-62..+62], Y = -426`；旧补给路线末端直指 `X = +5.8` 堵在门口。
  - 在 [LumberMillSupplyRoute.h](../../Source/FPSGAME/WorldGeneration/LumberMillSupplyRoute.h) 将末段平滑右转引入东侧平坦空地（`ReliefZ` 落差仅 `5.5 cm`），马车驻停中心落在 `Tavern (+470, -825)`（`Village (-796.8, 2091.7)`）面朝正东与酒馆前墙平行：车尾木料距正门 **`+203 cm`**、距西侧拴马桩 **`+275 cm`**、车身距酒馆前墙 **`+312 cm`**、距路灯 **`+282 cm`**、马头距 07 号民居 **`+459 cm`**（一次性俯视核查图已归档至 [cleanup-summary.json](../Publication/LumberMillOps20261128/cleanup-summary.json)）。
- **2. 运输工进出酒馆自动开关双开门（零穿门）**：
  - 在 [LumberMillOperationsSubsystem.h](../../Source/FPSGAME/WorldGeneration/LumberMillOperationsSubsystem.h) / [LumberMillOperationsSubsystem.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillOperationsSubsystem.cpp) 新增 `FindTavernFrontDoor()`、`TickTavernDoorForWorker()` 与 `CloseAutoControlledTavernDoorIfAny()`，直接联动 `VillageHouseDoors` 挂载于酒馆正门洞的实体 `AColdSteelDoubleDoor::SetDoorOpenAuto()`：
    - 运输工从东侧马车面向酒馆一侧下车，经前院拐点 `(+235, -605)` 行至门前 `2.2 m` 内自动顺行走方向推开双开门（入内向内开、清晨出门向外开，带完整开关门音效与网络同步），并在门扇旋转到位前（`0.68 s`）自然驻足待机杜绝穿门；
    - 穿门过 `1.65 m` 后自动在身后关门（若玩家正站在门洞 `1.85 m` 内则礼让不关，次晨清剿入侵后返车同理）。
- **3. 酒馆休闲坐姿重制（`A_LJ_SitTavern_Relaxed`，120f / 4.00 s）**：
  - 针对旧复用 `A_Rest_Bench_Idle`（为 52 cm 高凳制作，导致在 `46.06 cm` `SM_TavernStool` 上悬空/脚陷地板且双手镜像僵直），新增 [author_tavern_sit_r61.py](../../Tools/WorldGeneration/ForestVillage/author_tavern_sit_r61.py) 精标酒馆家具实测尺寸（木凳面 `46.06 cm`、圆桌 `76.07 cm` 桌沿 `Fwd=+24 cm`）：
    - 角色胶囊底精确对齐地板 `FloorZ`（`Actor.Z = FloorZ + 88.0`，修复态 `86.6` / 残破态 `87.1`），双靴平贴地板；骨盆 `Z = 55.6 cm` 稳贴木凳面；双腿非对称自然错落（左脚前伸外展、右脚随意回收）；上身自然前倾 `19.5°`、右前臂与半松手掌平搭圆桌面（`Z = 79.4 cm`、距陶碗/木勺 `>= 14 cm`）、左手轻松搭于左大腿中上段（避开桌沿）；4 秒周期 C1 PCHIP 呼吸与环顾酒馆微动态。
    - 量化门禁与 4 视角实景家具 3D 核查：`max_reach_err_r/l = 0.000 cm`、`max_wrist_bend_r = 11.4°`、`max_arm_elev = 46.4°`（一次性 3D 审图已归档至 [cleanup-summary.json](../Publication/LumberMillOps20261128/cleanup-summary.json)）；新资产已原子发布至 `/Game/ForestPathStudy/VillageRegion/LumberMill/Animations/A_LJ_SitTavern_Relaxed`，回执见 [authored-sit-r61.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R61/authored-sit-r61.json) 与 [published.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R61/published.json)，同步接入 [LumberMillWorkerActor.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.cpp)。
- **编译与状态**：`FPSGAMEEditor Win64 Development` 编译与全模块 DLL 链接通过（`BUILD_EXIT=0`），已于 [UnrealEditor-FPSGAME.dll](../../Binaries/Win64/UnrealEditor-FPSGAME.dll) 二进制确认 `A_LJ_SitTavern_Relaxed` 与东侧停靠点坐标落盘。当前状态：**未实机测试 · 待 NAS 备份**。

<a id="lumber-mill-ops-r60"></a>
### R60 木桩劈木流畅挥斧重构与曲柄刚性斜握对位（2026-11-27）

针对实测反馈“木桩劈木动作僵硬不合格、斧头错位且抓握部位/姿势未对齐”的问题，参照工程 [ue5-fps-arms-animation](../../skills/ue5-fps-arms-animation/SKILL.md)（`pose-contact` 动力学曲线、`overhead-reach-wrist` 过顶伸展、`two-handed-tools` 双手刚性副手镜面、`FPSPlayerBodyToolGrip::FitShaft` 圆柱贴面指法）重构 [author_lumber_ops_r60.py](../../Tools/WorldGeneration/ForestVillage/author_lumber_ops_r60.py) 并同步改造运行时工具绑定：

- **1. 斧头错位与抓握姿势根因修复（实测 `SM_BattleAxe` 曲柄截面 + 刚性 `hand_r` 绑定）**：
  - 逐层采样 `SM_BattleAxe`（`12,693` 顶点）发现木柄整段沿 `-X` 明显弯曲（`X = -6.29..-2.19 cm`），旧版 [LumberMillWorkerActor.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.cpp) 按直线 `X = 0` 估算并由浮动掌心重算朝向，导致斧柄偏移 `~4.8 cm` 且挥斧滑移。
  - 改为在实测真实发力区确立双握点：左手下段皮缠柄 `(-4.88, 0.01, -27.50) cm`（半径 `3.18 cm`）、右手上段白蜡木柄 `(-3.61, 0.01, -7.50) cm`（距斧刃 `28.4 cm`、半径 `2.58 cm`），采用真实伐木工 **44° 旋前内包 + 42° 掌纹斜握** 与圆柱表面 `FitShaft` 十指贴合解算（双拇指朝斧头方向锁在食指外侧）；运行时直接改用唯一刚性变换 `AxeInHandR * HandRWorld`（`Pos=(-13.4449, 2.2296, 4.4388)`、`Quat=(-0.294757, 0.138579, 0.892663, -0.311555)`、`Scale=1.00`），两套动作（`A_LJ_SplitLog_Loop` / `A_LJ_ChopTree_Loop`）共享同一刚性契约，消除一切手部滑移与误抓斧头。
- **2. 僵硬分段动作根治（周期 C1 PCHIP 动力链甩鞭 + 全幅过顶弧线）**：
  - 废除逐段归零 `Ease(T)`，改用连续周期 C1 单调三次插值（`eval_periodic_pchip`）驱动 `48f / 30fps = 1.60 s` 循环：髋/脊柱提前 `2.5` 帧启动下压并带胸椎滞后甩鞭、双手高举过顶（`hand_r Z = 96.1..167.4 cm` 行程 `71.3 cm`，较旧版翻倍；斧刃最高 `208.5 cm`）、下挥舒展大弧、命中帧（整数帧 `f=24, u=0.500`）近水平 `-6.63°` 斧柄以钢刃精准劈入立木中心（`R = -0.01 cm, Fwd = 100.04 cm, Z = 80.75 cm`），随后重击吸能停顿并沿右侧椭圆 S 弧平滑收势；同步将 [LumberMillWorkerActor.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.cpp) 裂木/砍树命中触发相校准至 `0.50f` / `0.46f`。
- **3. 锯木工（Role 1）与全员三套工装腋下防撕裂/防漏孔统一收口（`LumberMillOps-R60b`）**：
  - 排查锯木工（Role 1）腋下穿模漏白定位双重遗留：`SK_MasterArtisan_Workwear`（`WorkwearR6` 靛蓝上衣 `comp[0]`）上轮未纳入 R59 外展重裁，腋下仍保留 `42.30×–42.73×`（单边拉裂至 `23.42 cm`、`246–252` 个撕裂面）的旧版粘连桥，且 [LumberMillWorkerActor.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.cpp) 未遮罩 Role 1 内层 `BodyMesh` 槽位 `3`（`SkinTorso`，其 `Z = 100.1..140 cm` 实际全在靛蓝衣与 `Flax` 领襟之下）。
  - 3D 近景审图同步抓出 R59 [repair_lumber_workwear_r59.py](../../Tools/WorldGeneration/ForestVillage/repair_lumber_workwear_r59.py) 外展裁领时未限定 `|X| < 13.5 cm` 而在双肩三角肌外侧误切出 `3 cm` 孔洞的问题；现已修正领口裁剪半径并在 [repair_master_artisan_workwear_r60.py](../../Tools/WorldGeneration/ForestVillage/repair_master_artisan_workwear_r60.py) / [bake_master_artisan_r60.py](../../Tools/WorldGeneration/ForestVillage/bake_master_artisan_r60.py) 中一次性重算烘焙全部 3 套工装（`SK_MasterArtisan_Workwear`、`SK_Carpenter_Workwear`、`SK_Smith_Outfit`，均保留全部原有材质槽与 3 级 LOD、`+0.00 MB` VRAM）：实测 `SK_MasterArtisan_Workwear` 腋下最大拉伸由 **`42.73× / 23.42 cm` 降至 `3.05×–3.12× / 1.47 cm`（`p99 = 1.67×`）**，三套上衣全部通过 **`boundary_loops == 3`（仅领口 + 双袖口，0 孔洞）** 门禁（一次性前后对比审图已归档至 [cleanup-summary.json](../Publication/LumberMillOps20261128/cleanup-summary.json)）；同步在 [LumberMillWorkerActor.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.cpp) 对全员 3 名伐木工统一遮罩 `BodyMesh` 槽位 `0` 与 `3`。
- **4. 量化门禁、原子发布与编译校验**：
  - 全 48 帧硬指标：`A_LJ_SplitLog_Loop` 实现 **`max_reach_err_r/l = 0.000 cm`、`max_left_grip_err = 0.000 cm`、`elbow_r = 31.2°..59.4°`、`max_arm_elev = 119.9°`**；`A_LJ_ChopTree_Loop` 同样 **`0.000 cm` 触达/副手误差、`max_arm_elev = 100.0°`、`max_wrist_bend_r = 30.7°`**。
  - 一次性动作与握斧 3D 审图已归档至 [cleanup-summary.json](../Publication/LumberMillOps20261128/cleanup-summary.json)；5 份正式资产（`A_LJ_SplitLog_Loop`、`A_LJ_ChopTree_Loop`、`SK_MasterArtisan_Workwear`、`SK_Carpenter_Workwear`、`SK_Smith_Outfit`）均按 SHA-256 改前备份并原子发布，回执位于 [authored-ops-r60.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R60/authored-ops-r60.json)、[published.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R60/published.json)、[master_artisan_armpit_audit.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R60/Workwear/master_artisan_armpit_audit.json) 与 [published_workwear_r60b.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R60/Workwear/published_workwear_r60b.json)。
  - `FPSGAMEEditor Win64 Development` 编译与 DLL 链接全部通过（`BUILD_EXIT=0`），已于 [UnrealEditor-FPSGAME.dll](../../Binaries/Win64/UnrealEditor-FPSGAME.dll) 二进制验证 `AxeInHandR` 与 `M_Smith_Covered` 常量及符号就位（含同批 `SupplyRouteVFX-R60` 方案 A 补给路线特效）。当前状态：**未实机测试 · 待 NAS 备份**。

<a id="supply-route-vfx-r60"></a>
### R60 M 键伐木补给路线特效重构：方案 A 冷钢鎏金丝流（2026-11-27）

- **参考图评审与选型**：按冷钢 UI 色阶与实景 `L_ForestPathVillage` 352 m 路线生成方案 A（冷钢鎏金丝流）与方案 B（冷钢战术测绘）两套 2560 × 1560 审查图；用户确认采用 **方案 A（冷钢鎏金丝流）**（一次性概念图与弃用的方案 B 废案图均已按 SHA-256 清单归档至隔离区，见 [cleanup-summary.json](../Publication/LumberMillOps20261128/cleanup-summary.json)）。
- **核心渲染重构（[SColdSteelWorldMap.cpp](../../Source/FPSGAME/UI/SColdSteelWorldMap.cpp)）**：
  - 废除原 7 层 `MakeLines` 硬边堆叠、双轨外框、16 m 刻度、空心线框菱形彗星/碎星与常驻同心圆脉冲，改由自研轻量 GPU 顶点画布 `FRouteSilkCanvas` 通过 `FSlateDrawElement::MakeCustomVerts` 输出 7 站对称高斯羽化三角丝带（`SampleUniformRibbon` 等弧长重采样，消除拐角毛刺与贴纸感）。
  - **日常正常态**：暖暗压地底影（`#090705`）+ 柔和暖金大气光晕（`#CFA456`）+ 单束渐变鎏金丝带（暗铜 `#756447` → 冷钢主金 `#D4B678` → 香槟丝光 `#F2E0A8`）+ 2 道长羽尾液态金扫光（`#FFF8E2`）+ 4 枚固定锚点实心微箭标（仅在扫光经过时顺带点亮）+ 5 颗真实径向柔焦光斑 + 实心暗铜鎏金端点徽章（伐木场 / 村庄酒馆）。
  - **17:00 马车运输联动**：将实车坐标精确投影至 352 m 路线弧长，车后已行经段回落为沉静暗铜，车前剩余段以鎏金丝流与引导扫光指向酒馆，配实心八辐鎏金车轮徽章与冷钢暗玻璃距酒馆米数标签。
  - **夜间入侵 / 残怪受阻态**：全线降饱和为克制的停运铁灰（`#3C4249` / `#959DA6`），仅在村庄东门封锁点（`ExteriorKnotsCm` 末节点）呈现局部羽化暗红渐晕（`#8C222D` / `#D85566` / `#FF92A2`）+ 单枚实心红盾 `!` 告警徽章与冷钢暗玻璃受阻人数标签。
- **构建与验证状态**：`SColdSteelWorldMap.cpp` 零错零警通过编译，已随 `LumberMillOps-R60b` 一并完成全模块 `UnrealEditor-FPSGAME.dll` 链接落盘（`BUILD_EXIT=0`）；无新增资产包、0 显存增量；当前状态：**未实机测试 · 待 NAS 备份**。

<a id="lumber-mill-ops-r59"></a>
### R59 工装腋下漏空穿模根治、手腕/手肘/握斧衔接重构与高速重击劈柴校准（2026-11-27）

- **1. 腋下漏空穿模双重根因与修复**：
  - **衣物拓扑根因**：定位 `FinishR2` `Continuous linen shirt`（`SK_Carpenter_Workwear` 与 `SK_Smith_Outfit` 共用）因在 A-pose 体素化 `marching_cubes` 阶段将内袖与肋侧焊成实心「蝠翼桥」，手臂前伸时单个 `0.54 cm` 腋下三角面被撕裂至 `22.74 cm`（`42.30×` 拉伸）；同时 `SK_Smith_Body` 槽位 `0 (DefaultSleeves)` 与 `3 (SkinTorso)` 未遮罩，直接从撕裂处穿出 `+4.85 cm`。
  - **外展 T-pose 重裁 + 遮罩**：新增 [repair_lumber_workwear_r59.py](../../Tools/WorldGeneration/ForestVillage/repair_lumber_workwear_r59.py) 与 [bake_workwear_r59.py](../../Tools/WorldGeneration/ForestVillage/bake_workwear_r59.py)，先将身体与袖筒外展 `+46°` 拉开 `8+ cm` 腋下净空重建连续衬衫并做下腋折缝平滑（`16` 轮），再经精确逆 LBS 还原至绑定姿态，保留全部口袋/领口/袖口/材质槽与 3 级 LOD（`+0.00 MB` VRAM），实测腋下最大拉伸由 **`42.30×` 降至 `3.05×`（`p99 = 1.67×`）**；同步于 [LumberMillWorkerActor.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.cpp) 对 `BodyMesh` 被衣袖/衣身完全覆盖的槽位 `0`（全员）与槽位 `3`（角色 0/2）套用 `M_Smith_Covered`，彻底杜绝内层裸肤穿出。
- **2. 手腕/手肘/握斧衔接与高速重击劈砍重制**：
  - [author_lumber_ops_r52.py](../../Tools/WorldGeneration/ForestVillage/author_lumber_ops_r52.py) 新增自然旋前握持解算器 `solve_arm_grip_ik()`（取同时正交于前臂与斧柄的掌心法向 `palm ~ ±(dl × haft)`），消除原 `54.6°` 鹅颈下折腕，并改为瞄准中指的解剖拇指扣合；`A_LJ_SplitLog_Loop` 缩短至 **`40f / 1.333 s`**（`ActionRateScale = 1.0`，较旧版 `1.91 s` 提速 **30%**），加入顶点蓄力停顿（`0.30–0.35`）与连续 5 帧（`0.167 s`）`strike_heavy (t^2.8)` 爆发下劈及重击停顿，实测 **`max_wrist_bend = 17.02°`、`elbow = [56.2°, 136.0°]`、`elev = 92.3°`、`ik_err = 0.00 cm`**；`A_LJ_ChopTree_Loop` 同步提速至 `45f / 1.50 s`（`wrist_bend = 28.97°`、`elbow = [77.9°, 138.6°]`）。
  - [LumberMillWorkerActor.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillWorkerActor.cpp) 将 `ComputePalmGripCenter()` 由噪声敏感的 `middle_01_palm - mcp` 升级为 `index_01 × pinky_01` 与真实握拳指环质心（`middle_01/02/03 + thumb_02`）1:1 混合中心，斧柄居中锁死于双拳环内；劈裂触发同步至 `u = 0.47f`（重置 `0.84f`）。
- **3. 斧刃与木块正中校准**：
  - `A_LJ_SplitLog_Loop` 命中帧（`f=19, u=0.475`）斧柄改为 **`-15.43°` 下倾**（原 `+9.8°` 上扬过冲 `+22.7 cm`），斧刃中心精准落于 `X = +0.45 cm / Fwd = 99.98 cm / Z = 83.6 cm`（直劈 `75.1..105.1 cm` 立木中段）；[LumberMillOperationsSubsystem.cpp](../../Source/FPSGAME/WorldGeneration/LumberMillOperationsSubsystem.cpp) 将 Role 0 对 Stump A/B 站位同步调至精确 **`100.0 cm`** 站距（`(724.9, 389.1)` / `(949.9, 484.1)`，`Yaw = 18°`）。
- **发布、编译与恢复**：7 份正式资产（5 套 `A_LJ_*` 动画 + `SK_Carpenter_Workwear` + `SK_Smith_Outfit`）经 SHA-256 改前备份与原子发布，回执与备份清单位于 [LumberMillOps-R59/published.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R59/published.json)、[authored-ops-r59.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R59/authored-ops-r59.json) 与 [workwear_armpit_audit.json](F:/FPSGAMEData/ArtProduction/HillsForestPath/LumberMillOps-R59/Workwear/workwear_armpit_audit.json)；`FPSGAMEEditor Win64 Development` 编译日志位于 [build-20261127-151028.log](../../Saved/BuildEditor/build-20261127-151028.log)。当前状态：**未实机测试 · 待 NAS 备份**。
