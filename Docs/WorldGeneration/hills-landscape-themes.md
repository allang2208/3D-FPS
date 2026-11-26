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
