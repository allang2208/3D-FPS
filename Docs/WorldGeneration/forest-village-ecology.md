# 丘陵林地 PCG 分层与组合

正式关卡是 `/Game/GameMaps/L_ForestPathVillage`。正式关卡由[丘陵景观与道路景观](hills-landscape-themes.md)两个组件分别装配。原全生态组合入口为 [PCG_ForestVillageSurroundings](../../Content/ForestPathStudy/VillageRegion/PCG_ForestVillageSurroundings.uasset)。打开主图可以看到七个带中文备注的子图节点，双击进入对应生态层。主图保留一个最终的点合并节点。

## 各层内容

内容浏览器目录为 `/Game/ForestPathStudy/VillageRegion/Ecology`。每个子图名为 `PCG_Forest<层名>`，配套点集名为 `DA_Forest<层名>_01`、`_02` 等。表中是本版有落点的生成器数量，一个变体占一路。

| 层标识 | 主图节点 | 内容 | 点集分页 |
|---|---|---|---:|
| `Trees` | 乔木树冠 | 两款烘焙的欧洲鹅耳枥 | 2 |
| `Shrubs` | 灌木 | 两款林下榛灌木 | 2 |
| `Grass` | 草类与草本 | 低草、铺展草、高草和六款林地阔叶草本 | 9 |
| `Rocks` | 岩石与碎石 | 林地岩石、小碎石和花岗岩随机池 | 24 + 17 |
| `Deadwood` | 枯木与松枝 | R30 历史组合包含细枝、倒木、苔木段和木桩。现行双主题只使用独立木体，见 [R41 退役清单](hills-landscape-themes.md#soil-wood-r41) | 14 |
| `Floor` | 林床装饰 | 林床组合网格、苔斑贴花与泥土贴花 | 3 |
| `Wetland` | 水坑与岸草 | 闭合水坑 Actor 以及对应的岸边莎草 | 2 |

每层只加载自己的点集。子图内用 Gather 传递原始数据，主图汇总一次。R29 的 79 个变体槽中有六个当前为空，烘焙时跳过，原槽位和资产池继续保留。以后槽内有点就会自动恢复生成器。单个加载节点最多 24 路，新增变体达到第 25 路时在同一生态层开下一页。UE 5.8 当前引擎的 63 路限制作用于单个上游节点的动态引脚裁剪，整张图可以有更多节点。

## 怎样组合

- **R30 的独立全生态组合**使用完整主图。正式丘陵从 R31 起由两个主题组件分别生成。水坑先由已保存的地形和闭合盆地数据确定；植被和木料落点在烘焙时已避让水面、道路和作业区。主图中各生态层可以并列连接。
- **只做林木植被**，选 [PCG_Trees_Shrubs_Grass](../../Content/ForestPathStudy/VillageRegion/Ecology/Combinations/PCG_Trees_Shrubs_Grass.uasset)。这个组合已在隔离关卡单独生成 704,161 个网格实例。
- **只做林床布景**，选 [PCG_Rocks_Deadwood_Floor](../../Content/ForestPathStudy/VillageRegion/Ecology/Combinations/PCG_Rocks_Deadwood_Floor.uasset)。单独生成 367,770 个网格实例和 89 个贴花。
- **自行组合**，在已有 UE 编辑器的 Python 控制台执行下面的示例。它创建或复用单独的组合资产，返回内容路径。可从表中选择任意有点集的层。组合引用相同子图，同一层更新时各组合随之更新。

```python
from pathlib import Path
import sys, unreal
tools = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())) / 'Tools/WorldGeneration/ForestVillage'
sys.path.insert(0, str(tools))
import forest_ecology
forest_ecology.compose('Trees', 'Shrubs', 'Wetland')
```

查看单独组合时，在隔离副本中用单个预览组件 Clean 后挂载该组合，并先停用覆盖同一区域的主题组件。恢复正式布局时启用丘陵、道路两个主题组件。点集使用原丘陵的世界坐标；把多个包含相同层的组合同时挂在同一片区域会重复布置。水面生成还依赖区域 Actor 已安装的盆地数据。

## 哪些内容由其他入口负责

玩家附近的细草由 `PCG_ForestGrassNear` 按需流送。全图草皮与路肩落叶位于地面材质，补充细草和远岸莎草另有自己的实例分区。黑杨、山毛榉的站立、砍伐和再生由采伐系统持有。正式林地子关卡里的原参考树冠、榛灌木、石块、草本和路面贴花也有自己的 PCG 图。切换主图的某个生态层只影响本表列出的批次。

## 怎样扩展与重建

1. 新变体沿用原来的放置输入。基础 16 个槽依照既有二进制布局分层；扩展网格按已登记的扫描家族、花岗岩目录和木料目录分类。新增的扩展网格也可在资产元数据中设置 `ForestEcologyLayer`，取值为表中的英文标识。未标注的普通装饰归入 `Floor`；拼错显式标识会报错并中止生成。层归属决定组织方式，放置规则、碰撞及裁剪规则仍由相应生成器决定。
2. 改了地形或水坑，走 [地形与水坑制作入口](../../Tools/WorldGeneration/ForestVillage/author_hill_relief_pools.py)，随后由原流程重算植被、湿岸和 R29 布景。改了倒木分布或落叶配方，走 [林道布景制作入口](../../Tools/WorldGeneration/ForestVillage/author_forest_litter.py)。两条路径都使用同一个原生分层构建器。
3. 只调整分层或重用已有点位时，在正式包的隔离宿主里运行 [forest_ecology.py](../../Tools/WorldGeneration/ForestVillage/forest_ecology.py)。`FPS_FOREST_REFERENCE_SOURCE` 指向 R29 的制作源目录，默认读取其 `Dressing` 子目录；可用 `FPS_FOREST_PLANTING_DIR` 指定其他同格式点集目录。需要 `planting.bin`、`reference-meshes.txt`、`harvest-trees.f32`、`study-granite.i32`。后台只制作组合时设置 `FPS_FOREST_ECOLOGY_LAYERS=Trees,Shrubs,Grass`；重建完整主图时不设置该变量。
4. 生态层资产和数据页由制作代码重建。长期调整写回 [分层与生成器代码](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/WorldGeneration/ForestVillageRegionPCG.cpp) 或源配方，手工组合保存在独立图里。

本次全图重新载入后，按网格比对 1,072,095 个实例的世界位置、四元数和缩放，位置精度为 0.1 厘米，四元数和缩放精度为 0.0001。另核对了 12 个水坑和 89 个贴花的位置。两种组合均在隔离宿主中实际生成，R30 当批的正式关卡保存了完整组合。当前正式关卡采用 R31 的双主题装配。[分层与组合检查结果](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestEcologyLayers-R30/audit.json) · [发布和恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestEcologyLayers-R30/published.json)
