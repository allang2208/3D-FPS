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
