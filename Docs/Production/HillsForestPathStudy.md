# 丘陵林道 · Magnet VFX 教程复刻

制作批次为 20261123-Tutorial。作者用 UE 5.4.4 搭建约 504 米见方的 Landscape，沿一条林道布置摄影区域。样板使用 UE 5.8 独立制作工程。原始资料、作者资源、可改的 PCG 图和地图分层保存，便于继续向 FPSGAME 的种子丘陵移植。[原作者视频](https://www.youtube.com/watch?v=QM8YPp9hBis) · [B 站中文版](https://www.bilibili.com/video/BV19mBeYpEF8/)

## 文件入口

### FPSGAME 独立制作的丘陵高度图

**ForestSaddle-R1** 是为 FPSGAME 独立生成的 16 位灰度 PNG。生成器从双山脊、浅谷和自定义林道曲线计算高程，种子为 `673841`，输入高度图为空。有效地块为 504 × 504 米，最高点和最低点相差约 24.8 米。路线由生成脚本的 `trail_y(x)` 给出，以地块中心为原点，单位为米，可用来布置后续道路样条。导入 UE Landscape 时使用 505 × 505 顶点、8 × 8 个组件、每组件一个 63 × 63 四边形分区，XYZ 缩放为 `100 / 100 / 10`。本版交付为制作源。下方正式林道仍使用教程版地形。[高度图](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/Original/ForestSaddle-R1/H_ForestSaddle_R1.png) · [可复现生成脚本](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/Original/ForestSaddle-R1/generate_heightmap.py) · [参数和文件哈希](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/Original/ForestSaddle-R1/heightmap.json)

### 正式林道关卡

FPSGAME 编辑器播放期间打开控制台即可进入正式工程内的林道关卡。

```text
open /Game/ForestPathStudy/Maps/L_ForestPathForest
```

当前正式版本为 **FPSGAMEIntegration-R3**。道路两种贴花原先重复叠加俯仰，54 个投影轴的世界坐标 Z 分量均为 0。R3 将已生成的落叶和干草贴花转向地面，道路 PCG 图只随机偏航，由贴花组件提供向下的俯仰。苔地的 Mossy Branch 密度由 241.40 降至 28，Wooden Branch 由 59.59 降至 7，平台与画质设置同步。[原始投影方向](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/FPSGAMEIntegration-R3/probe.json) · [散布参数及生成数量](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/FPSGAMEIntegration-R3/changes.json)

乔木与榛树使用林道专用风材质。原 SimpleWind 的树干旋转读取 `Object Pivot Location`。林道版本按每株实例的原点旋转，按树高渐入摆动，竖向位移为零；各株的局部摆动有不同相位。鹅耳枥和榛树的水平位移上限分别为 8 和 2.2 厘米，远景替身关闭风动平移。已将材质写入当前 4 种网格的实例组件及对应的两张 PCG 图。R3 共发布 20 个包，修改前的 5 个包在批次的 Before 目录。此次未进游戏验收。[正式林道风材质](../../Content/ForestPathStudy/Materials/Wind) · [发布清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/FPSGAMEIntegration-R3/published.json) · [恢复备份](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/FPSGAMEIntegration-R3/Before)

FPSGAMEIntegration-R2 的林道全长 94.18 米，进图位置取在林道中心，面向样条前进方向。沿路每 2.5 米抽取的 38 个点，泥土 C 层权重为 0.999–1.000。上版进图日志记录了 UE 未选出可用出生点。R2 在泥土权重为 1 的路段布置四个出生位，间距 2 米，若引擎排除全部候选，FPSGAME 的 GameMode 会从带有 `ForestPathEntrance` 标记的入口为玩家分配位置。[入口坐标](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/FPSGAMEIntegration-R2/entrance.json) · [出生点实现](../../Source/FPSGAME/FPSGAMEGameMode.cpp)

R2 修正 19 个场景扫描材质实例的 Nanite 和实例化用途。三种存在半透明冲突的林下植株改用 Fab 原件的带透明度底色图和双面遮罩材质。地表岩簇的散布密度从 5 降到 0.55，统一缩放从 1 改为 0.36–0.60。小石从 94.38 降到 12，缩放从 0.20–0.50 改为 0.18–0.38。各石种的平台和画质密度采用相同设定。摄影区 PCG 岩石密度过滤下限从 0.89 升为 0.974，重新生成后从 250 个实例降为 62 个。下文按教程时间码记录的数值保留为 R3 原稿。[R2 材质与散布参数](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/FPSGAMEIntegration-R2/surface-assets.json)

R2 正式发布 25 个资产包，逐文件 SHA-256 和旧版对应关系见[发布清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/FPSGAMEIntegration-R2/published.json)。替换前的 22 个包在 [Before](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/FPSGAMEIntegration-R2/Before)，制作脚本、编辑器模块源码及地图副本在[制作批次](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/FPSGAMEIntegration-R2)。出生点的正式代码差异单独保存在[恢复补丁](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/FPSGAMEIntegration-R2/forest-entry.patch)。本次未运行游戏或进行画面验收。

FPSGAMEIntegration-R1 以 R3 森林场景为底稿，沿用项目第一人称角色。关卡将摄影机调色应用到玩家视图，20 秒镜头由关卡中的 Level Sequence Actor 引用，默认由玩家控制视角。正式地图已加入 MapsToCook。

正式资产由 D 盘工程 Content 联接至 `F:/FPSGAMEData/Content/`。本批写入 234 个包并复用 27 个内容相同的已有包。逐文件清单列出操作及 SHA-256，恢复时分别取用接入批次的地图副本和独立制作工程的源资产。[正式地图](../../Content/ForestPathStudy/Maps/L_ForestPathForest.umap) · [接入批次](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/FPSGAMEIntegration-R1) · [文件清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/FPSGAMEIntegration-R1/published.json)

| 用途 | 位置 |
|---|---|
| 独立 UE 工程 | [ForestPathStudy.uproject](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/ForestPathStudy/ForestPathStudy.uproject) |
| 原图、材质包、扫描件和树包 | [制作源](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/MagnetVFX) |
| 章节与画面对照 | [原片英文自动字幕](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/MagnetVFX/MagnetVFX.en-orig.vtt) · [B 站视频本地参考](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/MagnetVFX/BV19mBeYpEF8-mp4720.mp4) |
| 地形底板 R1 | [L_ForestPathTerrain.umap](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/ForestPathStudy/Content/ForestPathStudy/Maps/L_ForestPathTerrain.umap) |
| 道路及地表 R2 | [L_ForestPathStudy.umap](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/ForestPathStudy/Content/ForestPathStudy/Maps/L_ForestPathStudy.umap) |
| 依照镜头修正的林道 R2b | [L_ForestPathCameraRoute.umap](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/ForestPathStudy/Content/ForestPathStudy/Maps/L_ForestPathCameraRoute.umap) |
| 森林场景 R3 · 默认打开 | [L_ForestPathForest.umap](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/ForestPathStudy/Content/ForestPathStudy/Maps/L_ForestPathForest.umap) · [PCG 图和道路蓝图](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/ForestPathStudy/Content/ForestPathStudy/PCG) |
| 林道镜头 | [LS_ForestPathWalk.uasset](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/ForestPathStudy/Content/ForestPathStudy/Sequence/LS_ForestPathWalk.uasset) · [镜头晃动蓝图](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/ForestPathStudy/Content/ForestPathStudy/Sequence/BP_ForestPathCameraShake.uasset) |
| 可编辑制作逻辑 | [地形及道路](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/ForestPathStudy/Source/ForestPathStudy/ForestPathTerrainCommandlet.cpp) · [绘制地表材质](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/ForestPathStudy/Scripts/author_surface.py) · [林冠采样与样条](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/ForestPathStudy/Scripts/author_canopy.py) |
| 地形母材 | [Unreal Sensei 下载页](https://www.unrealsensei.com/asset/ue5landscape) · [本次使用的源包](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/MagnetVFX/UnrealSensei) |

## 按视频定位

R3 的生成记录为林冠 8,746 个实例、榛树 568 个、PCG 岩石 250 个、路旁阔叶草 985 个，并沿道路样条生成 54 个贴花 Actor。林冠体积覆盖全图，其余三个实例图层集中在 195 × 102 米的摄影区域。道路图保留两条可改的贴花生成分支。以上计数来自制作命令的落盘记录。[森林生成记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/ForestPathStudy/../dress-author.log)

| 时间 | 作者的操作 | 样板中可复用的内容 |
|---|---|---|
| 00:00–04:39 | 展示成片，创建空关卡、环境光和雾，导入高度图。 | 用作者提供的 1009 × 1009 PNG；按 8 × 8 个组件、每组件 1 个 63 四边形的分区创建 505 × 505 个顶点。UE 居中取样，XY 步距 100 cm，Z 缩放 10，位置约为 (−25200, −25200, 100) cm。[作者的高度图](https://drive.google.com/file/d/1M6N9kpYyryRS5vN0QzZQ7Y4lh1qsiJNJ/view) |
| 04:40–13:00 | 接入 Unreal Sensei 地形材质，导入苔地和裸露树根，用 C 层刷路。 | `M_Landscape_NaniteEx` 的 A 层用 Nordic Moss，C 层用 Nordic Forest Ground Roots Coarse。两组原版 2K 贴图，颜色、法线与打包粗糙度分别绑定。A 的 Size 为 0.075；C 的最终值见 29:19。 |
| 13:00–18:34 | 将 Leafy Weeds 和小岩石加入 Landscape Grass Type，边看尺度边改密度。 | 保留两套 Leafy Weeds 原件。近路林下层单独设定种子、体量与退距。 |
| 18:35–28:54 | 获取 European Hornbeam 与 Common Hazel；用地形采样、密度噪声和实例生成铺设第一层林冠。 | 22:07 可读出 `SM_EuropeanHornbeam_Forest_05`。点采样 0.1 点/m²、范围 100 cm、Looseness 1；密度过滤下限 0.679997。树统一缩放 0.8–1.2、下沉 20 cm，绕竖轴随机旋转。第二棵树的缩略图按同包 Forest_04 配对。 |
| 28:55–37:59 | 放人物做尺度参照，再调树根平铺；沿手绘道路拉样条，用 Difference 排除路中的树。 | 最终 `Size C = 0.498`。样条投影到地形后采样，点范围按 (1, 50, 50) 倍增。这个数作用于 PCG 点范围；实际路面宽度单独由笔刷决定。 |
| 38:00–45:59 | 用 15 mm 相机看构图，调整焦点、光束与林地细节，再压低路面并柔化两侧。 | 相机用 16:9 DSLR。40:48 时间线可见光圈 1.67222，77:39 可见手动对焦距离约 580.54 cm。曝光补偿 10，卷积泛光 0.02，眩光 0.01，暗角约 0.508，胶片颗粒 0.5。道路下凹、边缘宽度及走势靠画面重建。 |
| 46:00–53:59 | 建立 PCG_road，将落叶等贴花沿样条分支散布，分别调整旋转和大小。 | 落叶、干草使用两种扫描贴花；材质读取底色透明通道、法线与粗糙度。 |
| 54:00–69:59 | 分开布置林下榛树、岩块、大树、路旁杂草，各层调整随机种子、尺寸和离路距离。 | 保留独立图层。高树直立，贴地物沿地面朝向。植株和岩块放在镜头周围的林道地块。 |
| 70:00–76:59 | 引入旧版 Megascans – Forest Path，用枯叶、落枝补地表，手摆前景石块、树桩。 | 作者在 70:23 指出旧合集为可选。公开 Fab 单品和旧合集分别登记；单品名称相似不足以确认是同一套资产。 |
| 77:00–86:37 | 20 秒相机沿路缓进，先低头看路，再看两侧和前方；调晃动、输出与成片。 | 原序列时间线为 30 fps。作者演示 MRQ 的 16 个时间采样、帧末快门和 16-bit EXR。 |

## 原作资源与分组

每个 Fab 源目录内的 `source.json` 记录官方条目。两套树保留 Epic 原始 UE 包路径；扫描件按 Quixel 资产号存放。领取时所列的免费价格与各自的使用许可分别记录。

| 类别 | 本次采用的资源 | 来源 |
|---|---|---|
| 基础地貌与地表 | 作者的 `MAGNET_VFX_HIGHT_MAP.png`，Unreal Sensei UE5.4+ 2026 版；Nordic Moss 与 Nordic Forest Ground Roots Coarse | [苔地](https://www.fab.com/listings/c24e3a49-0194-4fa0-9dde-72ec490393ac) · [树根地表](https://www.fab.com/listings/039ecc0c-f329-4e4d-8b77-2fd172ea376c) |
| 林冠与林下灌木 | Megascans Trees 的早期原生包，SimpleWind 系列 | [European Hornbeam](https://www.fab.com/listings/c6f917b6-ffcb-4b86-9d9f-5274ba7f6a8e) · [Common Hazel](https://www.fab.com/listings/81bc7ba6-4686-4f94-9d2b-83eb1fdc4079) |
| 阔叶地被 | Leafy Weeds，`rbpir`、`rbcuh` | [植株 A](https://www.fab.com/listings/850cd660-4a20-4a96-ae4d-837d0d3cb14d) · [植株 B](https://www.fab.com/listings/e91cd481-2704-45e2-8a53-d5f2883e425a) |
| 岩石 | Nordic Forest Cluster Rock Small / Large、Nordic Forest Rock Small、Mossy Forest Rock 两款、Mossy Forest Boulder | [小岩簇](https://www.fab.com/listings/f186c225-178a-482b-a122-5508a318a4f0) · [大岩簇](https://www.fab.com/listings/37fe30a2-d452-485e-b13a-109c12781f82) · [单石](https://www.fab.com/listings/c87eb89b-d25b-4ec2-bf89-5527487d571c) · [苔石 A](https://www.fab.com/listings/bf4d00a4-6f3b-4555-8c13-97b2f8b65d04) · [苔石 B](https://www.fab.com/listings/957f0b2e-59a4-42dd-976f-11edc1bb7bc4) · [巨石](https://www.fab.com/listings/c790fa59-8a05-4d40-b645-3bc28eaf5982) |
| 贴花 | Dried Leaf Pile、Buffalo Grass；另外备好两款 Moss Patch | [落叶](https://www.fab.com/listings/711c707a-2678-4600-b89d-32b890671318) · [干草](https://www.fab.com/listings/09c8060b-e40d-4e15-82be-b94ef6177e71) · [苔斑 A](https://www.fab.com/listings/87c8469d-4ed8-46cc-bac8-d7d3d3c7d356) · [苔斑 B](https://www.fab.com/listings/b5fad446-5ca0-44b1-96cf-74051936b0e6) |

## 摄影区手摆参照

以下位置是 UE Details 面板中的世界坐标，单位厘米。截图反映各自时间点。拍摄机位在 38:12 为 (−10502.60, 23732.50, −404.63)，俯仰 −3.475°、偏航 −77.725°。81:02 面板显示后段机位 (−10152.06, 21975.56, −423.69)。R2b 据此把近路中心线校准到镜头推进方向。旋转及完整小数记录在[摆放与镜头脚本](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/ForestPathStudy/Scripts/author_forest_shot.py)。

| 画面时间 | Fab 原件 | XYZ 与统一缩放 |
|---|---|---|
| 75:50 | [Mossy Granite Rock · rgfoh](https://www.fab.com/listings/9512244b-56e8-4421-b5fb-080331958308) | (−9630.84, 21773.46, −631.86)，4.9691 |
| 76:07 | [Mossy Granite Rock · rgAsy](https://www.fab.com/listings/a358c488-9d69-4310-940d-1551ebf67af2) | (−9891.75, 23188.75, −631.60)，3.6797 |
| 76:15 | [Mossy Stump · tg0qedqda](https://www.fab.com/listings/022c92d0-a0c5-4d85-baee-070b269d81d8) | (−10635.54, 23589.29, −613.83)，3.8896 |
| 76:20 | [Mossy Stones Pack · tlljeeyva](https://www.fab.com/listings/901e3521-0a32-4a34-9cf8-9539addd4d77) | (−10690.56, 23745.12, −643.94)，5.0658 |
| 76:35 | [Nordic Beach Rocks · vepkcelqx](https://www.fab.com/listings/20816266-f544-4b15-898d-79b83d6091c5) | (−8671.26, 22005.41, −608.41)，1 |
| 76:40 | [Oak Branch · vfspfcjaw](https://www.fab.com/listings/db555a49-99ca-47bb-a292-f91554b1060f) | (−9009.19, 22201.20, −590.89)，1 |
| 77:00 | [Blue Lupin · tjtjfinia，VarE](https://www.fab.com/listings/e652a744-2003-407e-abdf-745de209776a) | (−10346.03, 21946.59, −579.01)，1 |

72:45 的定向光为可移动白光，10 lux，光源角度 4°。面板 XYZ 旋转约为 (−105°, −36.73°, 125.80°)。

### 地表近景散布

在 A 层的 `LG_A` 中，16:33、42:35、43:30、44:00 可读出下表设置。每行共享 10000 cm 的剔除距离。C 层覆盖 A 层后，道面可以从苔地散布中让开。

| 地表槽位 | Grass Density | 统一缩放 |
|---|---:|---:|
| [Nordic Forest Cluster Medium · xisgcic](https://www.fab.com/listings/b10a5b93-0ef7-4eb0-acef-4d5353f0220b) | 5 | 1 |
| [Nordic Forest Rock Small · xjiifd1](https://www.fab.com/listings/720455d3-89e2-4073-881c-267835a0a982) | 94.380165 | 0.2–0.5 |
| [Mossy Branch · relu7](https://www.fab.com/listings/92f00c70-17fb-4fd7-ae0f-3391c0704828) | 241.404968 | 0.3–0.8 |
| [Wooden Branch · rioqm](https://www.fab.com/listings/af48796f-f448-4e47-b277-610b7ed9ef0d) | 59.586777 | 0.2–0.8 |

## 接回 FPSGAME 丘陵时的顺序

先确定山脊、谷底、道路与村庄之间的高差和通行坡度，再由同一份高程和道路数据驱动路面权重、树林退距、林缘和贴花。对于整张种子丘陵，项目本身能从 XY、Seed 与地貌版本生成高度，教程的 PNG 适合固定样板。正式接入时应从项目高度查询取样，按区块投影林道和植被，并沿用现有村庄、河道与通行区的约束。[丘陵高程实现](../../Source/FPSGAME/WorldGeneration/TemperateHillsSurface.h)

R3 的背景制作命令已保存最终地图、七个可辨识的近景物件、启用 A 层散布的地表实例、20 秒镜头序列及 Perlin 相机晃动。最后一次保存正常退出。UE 对四个扫描件的 LOD 命名和材质包内两张贴图缺少版本标识给出了提示。未运行游戏、渲染或进行画面对照。[最后一次制作记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/ForestPathStudy/../shot-author.log)

本批次保留可回退的地形底板和已绘路面。没有作者工程中的完整笔刷轨迹、全部最终变换和随机状态。远段路线、第二种林冠网格、部分密度、镜头中间关键帧和旧合集的手刷细节存在重建成分。

<a id="village-surface-policy"></a>

## 林道村庄的地形起伏与统一地表策略

本节记录 ForestVillage-R2 的对照结果及下一版制作标准。参照物为已认可的 `L_ForestPathForest`，实施范围为 `L_ForestPathVillage` 的扩建外围和村门外露地面。本轮只制定策略。

### 测量与参考

从正式工程制作源提取两个高度场，在整体坡度同为 2°–4° 的地面比较局部起伏。沿东西、南北各取等长线段，测中心高程偏离两端连线的距离，合并两向后取中位数。两边均先用 1 米尺度平滑，削弱参考源高度量化台阶的影响。外围采样避开原林地、村庄地基及其 50 米过渡带。数值描述局部凹凸，不能直接当作路面下挖深度。[测量脚本](F:/FPSGAMEData/ArtReviews/HillsForestPath/ForestVillage-SurfacePlan-20261123/compare_relief.py) · [数据](F:/FPSGAMEData/ArtReviews/HillsForestPath/ForestVillage-SurfacePlan-20261123/relief.json) · [剖面对比图](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/ForestVillage-SurfacePlan-20261123/gentle-ground-comparison.png)

| 地面样本 | 4 米跨度 | 8 米跨度 | 16 米跨度 |
|---|---:|---:|---:|
| 测试林地，9,145 点 | 3.90 cm | 12.64 cm | 45.23 cm |
| 扩建外围，78,500 点 | 0.25 cm | 0.93 cm | 3.62 cm |

外围将平地、坡肩、山脊的大轮廓分开，但平地区域先从参考高程取 4 米与 22 米高斯平滑结果之差，再将归一化细节乘以 15 厘米。这个做法把人走几步就能察觉的坡折也压平了。教程中作者用人物校准树根纹理的尺度，以样条为树林让出道路，再局部压低路床、柔化路肩；最终画面中路中央连贯，较高的苔石和裸根集中在林缘。这些关系决定近景的层次。[外围生成配方](../../Tools/WorldGeneration/ForestVillage/generate_region.py) · [教程中段](https://www.bilibili.com/video/BV19mBeYpEF8/?t=2280) · [教程完工镜头](F:/FPSGAMEData/ArtProduction/HillsForestPath/20261123-Tutorial/Work/frame-15.jpg)

### 高度场怎么改

1. **先画地形骨架。** 沿用现有山脊和低地的大致标高，先标出鞍部、坡肩、坡脚、汇水线和村门通行带。在 25–80 米尺度用非对称缓坡、宽浅洼和沟口堆积衔接高低，顺坡把浅沟接到下游。草甸保留视野和通行空间，林地坡脚允许起伏更明显。
2. **再塑造步行尺度。** 在 4–16 米范围安排缓凸、根盘土包和浅槽；相邻凸起之间留平段。试段采用上表的 8 米指标，开阔草甸暂取 4–8 厘米、林缘取 8–14 厘米作为中位数目标。路中局部浅压，起伏放在两侧路肩，道路纵坡顺着原有行进方向。原林地交界同时承接边缘高程和坡向，城门门槛、建筑基底以及通行净宽为控制点。
3. **按网格尺度分工。** 常走路线附近按约 1 米间距取样，外围 2 米间距处以至少 6–8 米宽的地形特征为主。肉眼能改变地面轮廓的土包进入真实高度场，并让渲染网格、碰撞和 PCG 落点共用高程。细根、土粒、草绒用材质法线与高度混合表现。降低石头、枯枝散布的既有设定继续作为布置基准。

### 统一户外地表

实际读回显示，测试林地使用 `MI_ForestPathForest`，外围 55 块都使用原河岸道路的 `MI_EastRiverRoad`，村庄地基另取 `M_PebbleShoreGround`。测试区和外围的 A、C 层颜色与法线贴图相同，但 A、C 的 Size 从 0.075、0.498 变为 0.150、0.330，法线强度从 1、1 变为 0.65、0.90。外围绿草 B 的粗糙度还继承了 `T_BeachCliff_01_Roughness`。外围接缝只承接原林地的泥土权重，另把苔地权重推到 1；更远处的泥和苔又随同一个林地噪声增加。[正式关卡材质与参数读回](F:/FPSGAMEData/ArtReviews/HillsForestPath/ForestVillage-SurfacePlan-20261123/bindings.json) · [边界与权重生成](../../Tools/WorldGeneration/ForestVillage/generate_region.py)

| 户外地表 | 唯一指定的基础表面 | 出现位置与边界 |
|---|---|---|
| A 苔地 | Nordic Moss，取测试林地外观 | 林下阴湿处、坡脚和石根周围形成连续斑块；向开阔草地逐渐退出。 |
| B 丘陵绿草 | 项目现用 PN Grass Library 的 `ground_I` | 草甸、向阳林窗、村外草坡的主底色。采用同源且通道明确的粗糙度，缺源时使用按草面标定的常数。 |
| C 根土 | Nordic Forest Ground Roots Coarse，取测试林道路面外观 | 路心连续，路肩过渡，裸根与冲刷处少量露土。落叶贴花集中在路边和停积处。 |

保留 Unreal Sensei 地形母材质。Landscape 从绘制层读取权重，外围网格从已有网格数据读取权重，两端共用表面采样函数和唯一一组参数。按世界厘米统一平铺尺度、原点与方向，逐层明确法线强度、粗糙度、AO 和高度通道，统一混合顺序。先用人物和原林道校准根纹宽度，再以同一尺度向外围延伸。接缝传递完整的有效图层权重；道路优先，其余按林冠、湿度、坡位分配苔与草。PCG 用同一份路面和林缘权重决定树木退距与点缀位置。村门外露地基按同一规则过渡；村内专用铺装、院地和室内地板按原设计使用。[Epic 地形图层表达式](https://dev.epicgames.com/documentation/unreal-engine/landscape-material-expressions-in-unreal-engine)

### 实施顺序

首批选原林地边缘到外围草甸的一段约 80 × 120 米地面，另取村门内外短段处理地基衔接。依次完成裸地塑形、三层用材、PCG 与局部贴花。评审时以同一人物视高、机位和光照对照原林道；分别看裸地剖面、开阔草地、路心以及跨边界的粗糙度与纹理尺度。样段获认可后，再将同一配方推到其余外围地块。[策略修订前文档](F:/FPSGAMEData/ArtReviews/HillsForestPath/ForestVillage-SurfacePlan-20261123/Before/Docs/Production)



<a id="village-grass-sample-r3"></a>

## ForestVillage R3 林缘草甸与村门样段

正式地图为 `/Game/GameMaps/L_ForestPathVillage`。世界平面坐标以米计，林缘草甸从 (−54, 252) 到 (26, 372)，共 80 × 120 米。村门在 (−108, 258)，沿原林地北缘向世界 +X 约 54 米到达样段西南角。门前 8 米地基单独承接原林道，在靠村内的 4 米过渡回原村庄地面。原样板 Landscape 继续作为高程和外观参照。

新高度场在 R2 底板上叠入宽浅洼、弯曲的浅沟、单侧堆积和较短的林下土包，林缘的起伏强于开阔地。原地形边界的高程保留，草、原有植被与碰撞使用同一三角网格高度。Sensei 网格材质中的已连接表达式生成一份共享材质函数。苔地和根土取样板的平铺与法线强度，丘陵绿草使用 `ground_I`，缺少的草面粗糙度使用 199/255 的线性常量。网格核心、地块过渡带和村门前沿共用此表面。外围旧面和村内原面只在各自的过渡区参与混合。[制作脚本](../../Tools/WorldGeneration/ForestVillage/author_surface_sample.py) · [材质与四块网格](../../Content/ForestPathStudy/VillageRegion/SurfaceSample)

`PCG_ForestVillageSurroundings` 使用雨林原有 Low、Spreading、Tall 三件绿草网格及其风动材质。固定种子先生成不规则草簇，再用林冠开度、泥土权重和坡度筛选，按实际树木、灌木、石块和枯枝点位留空。门前通行带避让，外侧只用矮草与横展草。发布时生成短草 4,095 丛、横展草 1,956 丛、高草 369 丛，共 6,420 丛，含门外两侧 45 丛。三类草使用静态分层实例，无碰撞、无导航影响；短草和横展草在 30 米止绘，高草在 38 米止绘。现行完整外围制作入口会在基础地形重建后重新应用样段。[生成配方](../../Tools/WorldGeneration/ForestVillage/generate_surface_sample.py) · [草网格与风动材质](../../Content/WorldGeneration/TemperateHills/WetForest/CarpetGrass) · [PCG 图](../../Content/ForestPathStudy/VillageRegion/PCG_ForestVillageSurroundings.uasset)

[16 位高度场、权重与草点](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/ForestVillage-SurfaceGrass-R3) · [地图发布回执](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestVillage-SurfaceGrass-R3/published.json) · [发布前 R2 地图、PCG 与制作文件](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestVillage-SurfaceGrass-R3/Before)

Windows D3D12 SM6 制作时，Sensei 函数使用线性颜色采样的遮蔽、粗糙度和高度槽均改绑样段专用线性贴图。村门沿用原村地的通行面做过渡，省去河岸、额外林下落叶与干砾石分支。核心地面、林缘过渡与门前地面已完成 SM6 编译；本批未运行 PIE 或游戏。[材质编译回执](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestVillage-SurfaceGrass-R3/compiled.json) · [本批改前与发布文件清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestVillage-SurfaceGrass-R3/files.json)


<a id="hills-road-wild-grass-r4"></a>

## R4 道路与丘陵草地

正式林道村庄和东门至河岸的丘陵道路使用 Quixel Megascans **Wild Grass**（`oilox20`）。4K 扫描以世界 XY 每 200 厘米平铺一次，原扫描的粗糙度和遮蔽合并为线性贴图，法线强度取 0.28。纯草地的像素深度偏移为零；泥路继续使用原有 C 层及其绘制权重、法线和深度。植被 PCG 和高度场沿用 R3。

丘陵外围和道路网格在原有草地层内采样。连续浓苔保留，零散混合的草面采用统一草色。原林道的 Landscape 使用同一份草面函数，并以已保存的道路样条生成局部权重。距中心线 5.3 米以内为主，至 13.3 米平滑退出，陡坡保留原表面。村门外侧的 R3 过渡用同一路肩权重。独立测试林道与正式村庄共用该段 Landscape 材质，打开两张地图都会看到这段路肩的更新。

[Fab 素材与扫描规格](https://www.fab.com/listings/0d62cc63-d6e9-45ef-b5d8-0dfaf4d9d027?lang=en) · [原始下载与许可记录](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/WildGrass-oilox20/source.json) · [正式地表资产](../../Content/ForestPathStudy/VillageRegion/WildGrass) · [制作入口](../../Tools/WorldGeneration/ForestVillage/author_wild_grass.py) · [SM6 编译与发布记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsRoadWildGrass-R4/published.json) · [R4 发布前后文件与恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsRoadWildGrass-R4/files.json)


<a id="hills-road-forest-floor-r5"></a>

## R5 林道路肩与丘陵林地 Forest Floor

原 Wild Grass 所在的草地层改用 Quixel Forest Floor（`sfjmafua`）。颜色、法线、遮蔽、粗糙度和高度取自同一份 4K 扫描，每 2 米平铺一次。线性贴图 R、G、B 分别存储 AO、粗糙度与位移。既有草地函数保留原包名，使正式村庄、外围丘陵网格和独立样板沿用相同的材质引用。

`ForestFloorReliefCm` 默认为 1.8 厘米（沿地表法线的高度范围）。第一人称视点距地表 3.5 米以内使用完整高度，至 12 米平滑退出；掠射角减弱。颜色、法线及粗糙度使用同一个高度场求交后的 UV，正向像素深度偏移按草地覆盖权重混入。道路 C 层继续使用原配方，同一地表上的浓苔仍由原权重控制。区域形状、行走碰撞及 PCG 布置沿用上版。可在东门外泥路中央、路肩和两侧林地依次对照。此批后台制作，实机画面由用户试用。

[Fab 扫描](https://www.fab.com/listings/dae56d09-862c-4f77-9e72-a41281c49633) · [原始下载与许可记录](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/ForestFloor-Quixel/source.json) · [贴图处理入口](../../Tools/WorldGeneration/ForestVillage/prepare_forest_floor.py) · [UE 材质制作入口](../../Tools/WorldGeneration/ForestVillage/author_forest_floor.py) · [正式贴图](../../Content/ForestPathStudy/VillageRegion/ForestFloor) · [发布记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsRoadForestFloor-R5/published.json) · [本批改前版本及发布文件清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsRoadForestFloor-R5/files.json)

<a id="hills-nordic-moss-r6"></a>

## R6 丘陵 Nordic Moss 苔地尺度

Nordic Moss 与 Forest Floor 现在都按世界 XY 每 2 米覆盖一张扫描。A 层使用原有 2K 苔地颜色、法线、粗糙度与高度。局部 Sensei 函数按厘米读取世界坐标，换算成米后乘以 `Size A = 0.5`；原有随机错位与宏观明暗叠加继续作用。该尺度对应水平投影，和 Forest Floor 一致。

正式林道的 Landscape、外围丘陵网格、东门流式道路，以及村门过渡中从样板复制的林地层使用同一投影。村庄外围网格每米一个 UV 单位，而流式道路段原生 UV 每四米一个单位，按世界坐标取样消除了这项差异。独立测试林道与正式图共用 Landscape 材质实例。恢复到 R5 可使用本批的 `Before` 与文件清单。

[苔地投影函数](../../Content/ForestPathStudy/VillageRegion/ForestFloor/MF_NordicMossWorldMeters.uasset) · [制作入口](../../Tools/WorldGeneration/ForestVillage/author_nordic_moss.py) · [发布记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsNordicMoss-R6/published.json) · [改前及发布文件清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsNordicMoss-R6/files.json)

<a id="hills-slope-grass-r7"></a>

## R7 山坡草地与苔地的密集草簇

正式图 `L_ForestPathVillage` 的 `PCG_ForestVillageSurroundings` 在原有林缘草甸之外扩展到原林地 Landscape 及外围丘陵。新增 229,456 个草簇实例，其中原林地 116,013 个、外围丘陵 113,443 个。低矮草、铺展草与高草沿用既有三个绿草网格及风动材质。单个候选草堆由 7 至 12 簇组成，在苔地降低高度、减少高草比例。原 33,271 个种植与装饰点继续保留。

按米制高度场生成坡度；原林地读取实际 C 层泥路，外围使用 R3 地表绘制权重。路边还保留缓冲。村庄基座、陡坡与现有树根、岩块周边过滤。每个 16 × 16 米地块给新草留出的上限为 144 减去已有草簇数，草堆整体优先保留。草簇由 PCG 烘焙为 HISM，低草与铺展草在 30 米剔除，高草在 38 米剔除。草实例关闭碰撞、投影、光追可见性、距离场照明与导航影响。实机观感与帧耗由用户试用。

[坡面草簇生成](../../Tools/WorldGeneration/ForestVillage/generate_slope_grass.py) · [PCG 烘焙](../../Tools/WorldGeneration/ForestVillage/author_slope_grass.py) · [权重、点位与分布记录](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/HillsSlopeGrass-R7/generation.json) · [地图与 PCG 发布回执](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsSlopeGrass-R7/published.json) · [恢复至 R6 的文件清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsSlopeGrass-R7/files.json)

<a id="hills-continuous-grass-r8"></a>

## R8 丘陵连续草地覆盖

正式图 `L_ForestPathVillage` 的草地与苔地采用错行排布的连续草簇。行内间距 40 厘米，行距约 35 厘米，每平方米约 7.19 个候选根部。平地、坡脚和山坡共用格点，原泥路、村庄基座、树干、岩石和陡壁按原场景数据避让。苔地更多使用低草。既有点位由 R3 底稿恢复后与新底层合并，替换 R7 的随机草堆。

地图共有 7,099,533 个有效点位。中景层 789,555 簇由村庄原 PCG 烘焙，低草及铺展草在 64 米剔除，高草在 76 米剔除。近景层 6,309,978 个位置使用 7,536,640 字节的地块掩码。三种原网格各保留四级 LOD。正式游戏按本地镜头、编辑器按当前透视视口请求 16 米地块；40 米内开始预加载，52 米外释放。近景草在 29.5 至 33 米完成淡出。每次最多提交一个地块，同时最多三个在生成。两层都使用 HISM、植被密度分级与距离裁剪，草实例免碰撞、导航、光追和投射阴影。专用服务器跳过近景生成。此批完成后台制作和编辑器目标编译，尚未做实机画面与性能测量。

[点位制作入口](../../Tools/WorldGeneration/ForestVillage/generate_slope_grass.py) · [地块 PCG 与相机加载](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/WorldGeneration/ForestVillageGrassCover.cpp) · [密度和分层记录](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/HillsGrassCover-R8/generation.json) · [发布记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsGrassCover-R8/published.json) · [R7 改前文件及恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsGrassCover-R8/files.json)
2026-11-24 对正式 R8 做了四处第一人称截图。林内坡面近景连片，树根周围有明显的裸苔边界。泥路中央清晰。外围缓坡的草层延续至林间，朝阳近处草色偏亮，草簇之间仍能见到泥土。四个机位载入的近景 PCG 实例分别为道路 28,224、林坡 41,426、坡上远眺 50,004、外围缓坡 29,448。截图采用独立存档和上午 10:30 的游戏光照，画面检查未测帧率。[坡面近景](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/HillsGrassCover-R8/slope.png) · [泥路](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/HillsGrassCover-R8/road.png) · [坡上远眺](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/HillsGrassCover-R8/distance.png) · [外围缓坡](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/HillsGrassCover-R8/outer.png) · [机位与实例数](F:/FPSGAMEData/ArtReviews/HillsForestPath/HillsGrassCover-R8/camera.json)

<a id="hills-woodland-pools-r9"></a>

## R9 林间浅水坑与树根草地过渡

`L_ForestPathVillage` 在新地图的地形上运行旧雨林的米级洼地填水和水边三角形裁剪算法。村内地基、泥路和原林道子关卡的固有植被、石块及装饰参与选址排除。种子 237855 本次生成 5 处水坑，面积 16–100 平方米，最深位置距水面 11–29 厘米。同一份种子与输入可恢复相同的位置。最近东门的一处中心在世界坐标 (-4050, 27900) 厘米。地形碰撞沿用烘焙高度场。

`PCG_ForestVillageSurroundings` 的 WoodlandPool 分支生成每处独立岸线的水面，使用原 `M_ForestPond`。正式游戏把当前地形的水位交给原水体交互子系统。水域覆盖按 25 厘米栅格供制作期散布采样，近景和中景草均避开积水，岸边使用较低、较稀的草。树干周围从保护范围向外渐增草高及密度。三种本图专用材质实例将继承的亮度乘以 0.80、0.84、0.86，透光强度乘以 0.76、0.80、0.82。近景仍由镜头周围的 PCG 地块加载，本次未运行画面或帧率测试。

[浅水坑点位及水深](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/HillsWoodlandPools-R9/ponds.csv) · [散布输入与制作源](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/HillsWoodlandPools-R9) · [原水文代码](../Publication/HillsForestLandscape20261126/Integration/index.json) · [新图水坑制作与水面](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/WorldGeneration/ForestVillagePools.cpp) · [正式发布记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsWoodlandPools-R9/published.json) · [R8 改前文件与恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsWoodlandPools-R9/files.json)

<a id="village-ground-edges-r10"></a>

## R10 东门山肩与村边地表候选设计

正式地图仍使用 R9。2026-11-24 在 `L_ForestPathVillage` 以第一人称采集东门、墙内侧及村外草甸，结合地基代码与米级高度场定位接边。靠林一侧从原 Landscape 边界到村庄地基标高只有 6 米，横向约 118 米；最高侧落差 14.38 米，东门路心两端相平。村庄基座绑定 `M_PebbleShoreGround`，东门只有 8 米接入现有林地地表，外围草还受矩形排除条件限制。[门侧高坡](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/VillageGroundEdges-R10/CutBefore/bank.png) · [村边草线](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/VillageGroundEdges-R10/Before/west.png) · [地表材质读回](F:/FPSGAMEData/ArtReviews/HillsForestPath/VillageGroundEdges-R10/Before/ground-materials.json) · [第一人称机位](F:/FPSGAMEData/ArtReviews/HillsForestPath/VillageGroundEdges-R10/Before/camera.json)

候选高度场从墙外向林侧削坡。高侧 X = −170 米处调整约 53 米，低侧 X = −65 米处约 18 米。图中穿过墙线的 A–A′ 剖面位于 X = −155 米，比较 Y = 199–259 米间相邻米级采样的最大纵坡；当前为 66.9°，候选为 27.9°。东门路心、村内平台和本区水坑栅格的高度差值为零。正式接入时须将受影响的树根、枯枝、岩石和贴花随新地表重新贴地，并同步碰撞。建议使用村庄专用的林地子关卡副本承载削坡。[地形平面与剖面](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/VillageGroundEdges-R10/transition-design.png) · [候选高度差值，厘米](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageGroundEdges-R10/east-gate-grade.npz) · [测量数据和生成参数](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageGroundEdges-R10/design.json)

村边 10–18 米使用现有 Sensei 地表层。Forest Floor 与 Nordic Moss 沿用 2 米世界投影、原法线和高度偏移，东门路心延续 Nordic Forest Ground Roots Coarse，沿既有道路遮罩向内约 20–24 米接压实路面。门洞、硬地、工作院与墙身使用已有村庄道路、院地与陈设数据避让。PCG 用同一组地表权重，从林外草过渡到路肩低草和泥土。候选遮罩分辨率为 0.5 米，通道依次为林地地表覆盖、泥土、非泥土部分的苔地、草密度乘数。高度和遮罩均为离线制作源，未写入游戏包。发布基线与恢复位置见上方 R9 条目。[地表与草候选权重](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageGroundEdges-R10/village-edge-surface.npz) · [生成脚本](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageGroundEdges-R10/design.py)

<a id="village-slope-relief-r11"></a>

## R11 正式村庄地面的山坡起伏

正式图 `/Game/GameMaps/L_ForestPathVillage` 在载入时重建东门过渡面和村庄基座。地表覆盖 118 × 145 米，119 × 146 个高程节点，间距 1 米。制作时从正式林地 Landscape 重新读取高程，取世界坐标（−189，−63）至（−91，59）米的连续山坡。99 × 123 个原始节点高差 22.09 米。先在完整林地高程图上按 0.85、3.5 与 10 米三个尺度平滑，取尺度间的差值恢复浅洼与土丘，再将起伏映射到村庄平面。[实测山坡高度图](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageGroundRelief-R11/H_MeasuredSlope.png) · [提取的局部起伏](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageGroundRelief-R11/H_SlopeRelief.png) · [村庄完整高度图](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageGroundRelief-R11/H_Village.png) · [本次增减高度](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageGroundRelief-R11/H_VillageDelta.png)

9 处房屋使用正式布局的房基、入口和门前踏步。另取独立村庄子关卡的 3,962 条近地构件包围盒，区分随地面移动的散布和固定构件。教堂、马厩、院地、墙脚、铁匠铺修复区与既有路口保留原有承托。主路与广场的中心新增起伏限于 ±5 厘米。村庄数据中有 8,160 个节点高度发生变化，全区新增下凹最多 58 厘米、隆起最高 78 厘米。较开阔地面的高度变化第 10 和第 90 百分位为 −47 和 +70 厘米。[生成数据](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageGroundRelief-R11/generation.json) · [近地构件记录](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageGroundRelief-R11/contacts.json)

生成器将厘米差值编入独立的村庄高度表。载入村庄或切换铁匠铺修复状态时，现有院地高度与新表组合为最终顶点，同时用于地表、碰撞和按三角形的地面查询。子关卡显示时将已烘焙的草、散石、野花和枯枝实例按高度差贴地。地块公共边和门外已有 PCG 的前几行平滑回到接边标高。R10 东门外大坡的削坡仍为单独的候选设计。16 位 PNG 以 32768 对应 0 厘米；世界坐标 Y 随行号增加。完整高度图记录默认院地状态，修复后高度由游戏内原有规则更新。

[正式地表入口](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/WorldGeneration/ForestVillage.cpp) · [高度采样与原有实例贴地](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/WorldGeneration/ForestVillageRelief.cpp) · [后台提取](../../Tools/WorldGeneration/ForestVillage/export_village_relief.py) · [高度场制作](../../Tools/WorldGeneration/ForestVillage/generate_village_relief.py) · [接入文件和恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/VillageGroundRelief-R11/published.json)

<a id="reference-hill-r12"></a>

## R12 原村址整山与东侧村庄

正式图 `/Game/GameMaps/L_ForestPathVillage` 的原村址已回填为山体。山峰在世界坐标（−171，377）米，标高 64.30 米；原林道路口标高 −6.05 米，两者相差 70.35 米。原村庄矩形范围现在从 −7.43 米起伏至 64.30 米。作者源保留全图 1 米高程，峰顶、主要坡面以及新村址按米级网格烘焙，外围继续使用工程的较疏网格。高度图为 16 位，每单位 1 厘米，32768 为零。[地形与剖面图](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/ReferenceHill-R12/Hill-and-village.png) · [全图 16 位高度场](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/ReferenceHill-R12/H_ReferenceHill_1m.png) · [村庄选址前的山体高度场](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/ReferenceHill-R12/H_HillBeforeSettlement.png)

参考来自正式林地 Landscape 的同一段 99 × 123 高程节点，世界范围为（−189，−63）至（−91，59）米。沿该段的平均上坡方向提取长剖面，设计弯折的主脊、错开的山肩与两条坡沟。制作源分别提取 0.65–3.2 米、3.2–12 米平滑尺度间的高差，再将采样片旋转、错位、重叠融合，并恢复各层在参考地形上的高差分布。山脚承接原林地边缘高度和坡向。此前图中的 5 处浅水坑沿用原来的岸线、水位与避让数据。[山体生成器](../../Tools/WorldGeneration/ForestVillage/generate_reference_hill.py) · [山体、坐标和采样参数](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/ReferenceHill-R12/hill.json)

完成山体后，按整个村庄的地块高差、所需挖填、与水岸的间距和到原林道的距离选址。村心从（−113，323）移至（84，392）米，位移 208.7 米，地基标高 −5.86 米。村内建筑、院地、门槛沿用原子关卡的相对布局，固定承托范围之外的地面随新地形过渡。东门泥路按地面标高绕开湿岸，与原林道相连，全长 253.2 米。原地块与新路的草、岩石、枯枝、乔灌木和贴花重新烘焙，近景继续使用原有的草地加载距离。角色出生和村庄传送读取新村址。此批未改写玩家存档。[泥路的世界坐标和路面标高](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/ReferenceHill-R12/gate-road.csv) · [新村地面修正](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/ReferenceHill-R12/settlement.i16) · [后台地形与 PCG 烘焙](../../Tools/WorldGeneration/ForestVillage/author_reference_hill.py) · [正式包、构建与 R11 恢复记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/ReferenceHill-R12/published.json)

## TreeRootsWorldMap-R13 树根贴地与 M 键地图

外围林带和村庄树苗在中心与根盘边缘八个方向取地面高度。鹅耳枥和榛树的半径来自模型基部顶点，PCG 按实例缩放调整半径和埋深。原林道两张 PCG 图在随机变换和网格生成之间增加根系贴地节点。林道原有 8,746 株鹅耳枥中有 7,911 株进一步下沉，568 株榛树原有深度已足够。外围 13,494 株乔灌木的水平位置及树种逐株对应，下沉中位数 9.52 厘米。

林道村庄的 M 键底图覆盖 1,024 米见方，每像素 2 米。地面标高取自林道 Landscape、村庄最终地面以及外围地形网格。道路取自地表绘制权重与村庄道路布局，水面来自当前积水计划，村内建筑轮廓取自已加载建筑的碰撞。底图在地图打开时分帧绘制，地形、村庄修复状态或可见关卡变化会触发更新。世界与种子变化后重新绑定当前地图的标记。

[根系算法](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/WorldGeneration/ForestRootFit.cpp) · [地形制图](../../Source/FPSGAME/UI/ColdSteelWorldMapData.cpp) · [两张关卡的制作脚本](../../Tools/WorldGeneration/ForestVillage/author_roots_and_map.py) · [R12 高度场与道路制作源](../../SourceAssets/WorldGeneration/HillsForestPath/ReferenceHill-R12) · [正式包清单与制作回执](F:/FPSGAMEData/ArtProduction/HillsForestPath/TreeRootsWorldMap-R13/published.json) · [改动前版本](F:/FPSGAMEData/ArtProduction/HillsForestPath/TreeRootsWorldMap-R13/Before)

<a id="forest-reference-r14"></a>
## ForestReference-R14 原林道标准

正式入口为 `/Game/GameMaps/L_ForestPathVillage`。林道 Landscape 保留 `MI_ForestPathForest`，外围 55 块地表及村内运行时地面使用 `/Game/ForestPathStudy/VillageRegion/Reference/MI_ForestReference`。网格材质从林道当前母材质和实例派生，复用 AutoMaterial、C 泥路、Forest Floor 和 Nordic Moss 的纹理、函数与实例参数。新增网格由 UV4 传递道路和路肩权重。边界高度取自原 Landscape 的浮点高程。主山体与村址来自 ReferenceHill-R12。

外围两种鹅耳枥、两种榛树、五种岩石、六种林下植物从原 PCG 的实际落点、树种与比例扩展。苔石、小石和两种枯枝取自 `LG_A` 的四项密度和缩放设置。树根沿用 R13 的根盘贴地。水坑随当前地势重新寻找闭合洼地，岸边湿度复用旧丘陵的 2.4 米湿岸规则，形成莎草与沿岸枯枝。丘陵天气由 UDS 接管全图高度雾，低洼局部雾沿用既有的距离与时段调节。

制作顺序为 `export_forest_reference.py`、`prepare_forest_reference.py`、`author_reference_surface.py`、`author_reference_terrain.py`、`generate_forest_reference.py` 与 `author_reference_woodland.py`，脚本位于 `Tools/WorldGeneration/ForestVillage`。制作源为 `F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/ForestReference-R14`。发布回执、原版本和此次输出位于 `F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestReference-R14`。


<a id="hills-grass-distance-r15"></a>
## HillsGrassDistance-R15 丘陵草可视距离

正式图 `/Game/GameMaps/L_ForestPathVillage` 新增远景草层。矮草、铺展草的原截止距离为 64 米，新增范围延伸至 128 米；高草由 76 米延至 152 米，岸边莎草由 100 米延至 200 米。近景的 16 米地块流送和原 PCG 中景设置继续生效。远景从地图已保存的 PCG 变换取点，矮草与铺展草各取约四分之一，高草约二分之一，稀少的岸边莎草保留全部点位。每种草的新增实例从其原截止距离开始显示。

远景用 128 米分区批量实例化，锁定原网格最低细节级别，共用 512 × 512 草色和透明度合图，省去法线、风动、压草及接触时间贴图。采用引擎缩放后的实例距离裁剪和远端淡出；免碰撞、投影、光追可见性及导航。PCG 重烘焙入口 `author_reference_woodland.py` 会按新草点同步刷新这层草。正式资产位于 `/Game/ForestPathStudy/VillageRegion/FarGrass`，地图烘焙由 `Tools/WorldGeneration/ForestVillage/author_grass_distance.py` 完成。

[合图制作源](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/HillsGrassDistance-R15) · [正式地图和原版本回执](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsGrassDistance-R15/published.json)。


<a id="hills-quarry-road-r16"></a>
## HillsQuarryRoad-R16 出城林道与白崖采石场

正式入口为 `/Game/GameMaps/L_ForestPathVillage`，采石场子关卡为 `/Game/ForestPathStudy/VillageRegion/Quarry/L_ForestQuarry`。沿村门旧路到山脚分岔，再沿平缓弯曲的林道向前。新段约 376 米，村门至工作场入口约 592 米。道路、碰撞高程、M 地图的道路权重、树木避让和水坑排除来自同一套场地数据。

采石场复用 `FixedLayout/Hills.layout`、`FixedLayout/Quarry.dressing`、原工作面测绘、吊机、棚屋、工作台和采石场地表贴花。沿原工作面边线给 PCG 留出作业区，外围继续使用 R14 的树木、灌木、石块和枯枝。近处与中景草共同使用带符号的路缘距离、两种尺度的斑块和固定种子，远草从实际中景 PCG 落点抽样。原工作区尺寸及方位由 `quarry.json` 记录。

R15 的远景范围继续生效。远草使用无光照裁切材质，从当前天空光及大气日月光估算颜色，一次采样取得草色与透明度。林冠和榛树分别在 80 米和 40 米处停止风动位移，绘制上限分别为 360 米和 160 米。采石场子关卡在玩家接近约 350 米时加载，离开 390 米后可卸载。程序化近草继续以 16 米格流送。正式图沿用 FPSWeatherManager、UDS 和 UDW 的时钟、自动天气及雾。

制作脚本位于 `Tools/WorldGeneration/ForestVillage`。从 R14 制作源复制一份，运行 `BakeTemperateHillsLayout -ExportQuarry=<制作源目录>` 导出原摆放及高程，再依次执行 `prepare_quarry_road.py`、`author_reference_terrain.py`、`generate_forest_reference.py`、`author_quarry.py` 和 `author_reference_woodland.py`。远草材质由 `author_grass_distance.py` 的 `make_materials` 制作。编辑器及开发版可用 `fps.Hills.VisitQuarry` 前往当前地图的采石场入口。

[制作源](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/HillsQuarryRoad-R16) · [正式地图与资产回执](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsQuarryRoad-R16/published.json) · [路肩落点统计](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsQuarryRoad-R16/shoulders.json)。

<a id="hills-forest-pcg-r17"></a>

### R17 丘陵草流送与森林 PCG 点位

近景草仍按 16 米方格靠近玩家时生成。每格先从遮罩统计三种草的数量，再按原有顺序把变换和种子写入各自的 PCG 点数组。摄像机水平位置静止、待生成地块清空时跳过候选格搜索。地块销毁、相机移动和更换遮罩时重新计算。路肩分布和各草种可视距离沿用 R16。

外围森林使用 UE 5.8 的 PCG 数组点数据。同一分组共享固定包围盒。正式点位资产为 `/Game/ForestPathStudy/VillageRegion/DA_ForestVillagePlanting`。使用 R16 植被制作源重建的 32 个分组共 1,064,589 个点。逐组按顺序比对位置、旋转、缩放及种子，并在独立无界面进程重新读盘，结果一致。该资产从 141,630,845 字节降至 89,473,797 字节。正式地图与森林 PCG 图继续使用 R16 版本。

近草逻辑位于 `Source/FPSGAME/WorldGeneration/ForestVillageGrassCover.cpp` 和 `ForestVillageRegion.h`，外围森林烘焙位于同目录的 `ForestVillageRegionPCG.cpp`。本版已构建 FPSGAMEEditor，未采集游戏帧耗或显存。R16 恢复文件位于本批次 Before，R17 文件位于 Release。

[发布回执](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsForestPCG-R17/published.json) · [逐组读盘记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsForestPCG-R17/disk-points.json) · [编辑器目标构建](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsForestPCG-R17/editor-build-console.txt)。

<a id="hills-trails-r18"></a>

### R18 东门林道、远坡草地与试玩光照

正式地图为 `/Game/GameMaps/L_ForestPathVillage`。从原山体开路前的高度重新铺设东门到原林道岔口的路床，再衔接白崖采石场。村门、林道交叉口和工作场入口沿用原位置。固定种子的长短弯沿坡脚起伏，路宽左右独立变化。烘焙后的地形、碰撞、地图道路权重、泥地边沿、草木避让及积水排除使用同一份中心线和道路权重。岔口到采石场段约 398.5 米，村门到工作场入口约 621.5 米。

外围泥路沿用原来的 C 层及整套近远 PBR 贴图。`MF_TrailDirt` 将厘米世界位置对应到一张 512 × 512 的线性分布图，两个通道给颜色、法线、粗糙度和高度提供相同的非周期坐标偏移。接回原 Landscape 和村门时渐弱。另一个通道由实际选中的远草落点烘焙，控制中远距离的林地草色，路面和湿岸让开。灯光、法线和近景细节沿用现有材质。远草按固定的连续密度斑块选点，增加水平方向的草丛宽度，沿用原来单采样的无光照远草材质、无阴影和无光追配置。109,317 个实例，81 个分区和 250 个组件。草种对应的远端裁剪上限仍为 128、152、200 米。

编译并保存的 UDS 9.7 编辑器转换工具为 `/Game/UltraDynamicSky/Blueprints/System/Editor_UI/UDS_LightingScenario_Convert`。工具找到天空 Actor 后，若存在游戏世界或天空所在持久关卡为 `L_ForestPathVillage`，结束转换检查。手动编辑其他地图时仍可沿用插件的转换流程。正式图继续使用 FPSWeatherManager、UDS、UDW 和既有体积雾接管逻辑。原林道测试关卡包沿用原版。

制作脚本在 `Tools/WorldGeneration/ForestVillage`。复制 R16 制作源至新目录后，先执行 `prepare_hills_trails.py <制作源> <工作目录>`、`author_reference_terrain.py`、`generate_forest_reference.py <制作源> <R14 参考批次>`、`author_reference_woodland.py`，再执行 `prepare_trail_distribution.py <制作源>` 和 `author_trail_distribution.py`。使用 R17 及以上的森林点位烘焙代码。若升级 UDS，批次 Reader 下的 HillsAuthor 工具保存了 9.7 转换图改动的制作源，须按新版本的实际图适配。正式包和配方可在本批次 Release 中恢复，替换前文件在 Before 中。未启动游戏进行画面或帧时间验收。

[发布回执](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsTrails-R18/published.json) · [制作源](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/HillsTrails-R18) · [远草烘焙](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsTrails-R18/cover-far.json) · [材质编译](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsTrails-R18/surface-built.json)。


<a id="hills-understory-r19"></a>

## R19 林下共生、城镇原泥路与林雾

`L_ForestPathVillage` 的石块、枯枝、灌木与地草可叠生。草在树干中心保留 62% 的候选点，沿根盘向外平滑回到正常密度。道路、积水和采石场继续使用原有遮罩。近草沿用 16 米格流送。外围部分中景草转由近草层承接，正式关卡包含 611,973 簇中景草、109,047 簇远草，远草分布在原有 250 个组件中。[林下生成](../../Tools/WorldGeneration/ForestVillage/generate_slope_grass.py) · [正式森林配方](../../Tools/WorldGeneration/ForestVillage/generate_forest_reference.py)

城内 `MI_ForestVillageMudRoad` 复用 `M_PebbleShoreGround` 中实际保存的 `VillageTerrainRoad` 节点与贴图输入，包括原村庄路网遮罩、Rocky Road 和 Chapel Earth。颜色、法线和粗糙度使用同一遮罩，村庄地基外沿三米渐变到林道。静态开关只在城内实例启用，正式林道沿用 Forest Reference 材质。[泥路制作](../../Tools/WorldGeneration/ForestVillage/author_village_mud_surface.py) · [城镇地基绑定](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/WorldGeneration/ForestVillage.cpp)

正式图加载原林地子关卡时，将其高度雾的晴天密度、高度衰减、起雾距离与体积散射、消光参数交给 UDS。原图实读密度 0.02，起雾 0 米，高度衰减 0.2，散射分布 0.2，消光 1.0。UDS 继续按天气和昼夜叠加，正式图沿用 600 米体积雾距离。[天气接管](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/FPSUDSHillsAtmosphere.cpp) · [测试图雾参数](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsUnderstory-R19/study-fog.json)

[R19 发布与恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsUnderstory-R19/published.json) · [制作源](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/HillsUnderstory-R19) · [发布前版本](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsUnderstory-R19/Before) · [本版资产和源码](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsUnderstory-R19/Release) · [FPSGAMEEditor 构建记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsUnderstory-R19/build-final.txt)


<a id="village-flora-r20"></a>

## R20 村镇草皮、花岗岩与可采伐林木

正式入口为 `/Game/GameMaps/L_ForestPathVillage`。城内草面使用 Quixel Grass（pe1jvwp0）的 42 厘米实扫尺度和 2K 基色、法线及 AO／粗糙度／高度贴图。位移沿视线偏移纹理，11 米外淡出。米级地形使用同一扫描的低频起伏，限幅 ±4 厘米；沿用村庄建筑退距、泥路及地基接边权重。R19 的泥路、城外林道各自沿用原着色。[Fab 草地](https://www.fab.com/listings/2f4c8d27-9de0-43c4-ae85-1038b4eda16a) · [高度场制作](../../Tools/WorldGeneration/ForestVillage/prepare_village_turf.py) · [草皮材质](../../Tools/WorldGeneration/ForestVillage/author_village_turf.py)

35 个 Quixel Megascans 花岗岩三维条目以 UE Medium 档导入 `/Game/ForestPathStudy/VillageRegion/Granite`，使用 Nanite、2K 贴图和共用 PBR 母材质。按原石块足迹的尺寸替换 1,230 个位置，其中 21 个来自原林道子关卡。初始随机分配保存在正式 PCG 地图，独立样板保留原布置。[Fab 检索清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/VillageFlora-R20/rocks.json) · [逐模型包名和尺寸](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageFlora-R20/rock-pool.json)

2,350 个原树位（其中原林道 578 个）纳入可采伐池。复用已导入的 Quixel 欧洲山毛榉 A–D 与 Black Poplar A–D，按世界种子、12 米格与固定原始根位选择树型。树干碰撞按观察者距离开启，倒树、木材掉落、树桩、异位幼树、成熟和存档共用项目采伐系统。原树位与采伐候选同一身份。其他鹅耳枥、灌木沿用原生境。[欧洲山毛榉](https://www.fab.com/listings/cefe5722-9c31-4aa2-9ee2-e5426610d5e6) · [Black Poplar](https://www.fab.com/listings/6b22075c-53b6-4973-a6a5-9f4ccd6a72a8)

制作顺序为导入花岗岩、运行 `prepare_village_turf.py` 和 `prepare_forest_palette.py`、制作村镇草皮材质、运行 `author_forest_palette.py` 保存原有地图。树池输入从 R19 的最终植被文件和 R14 实测林地实例获得。[原始下载和制作源](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageFlora-R20) · [发布清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/VillageFlora-R20/published.json) · [发布前文件](F:/FPSGAMEData/ArtProduction/HillsForestPath/VillageFlora-R20/Before) · [构建记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/VillageFlora-R20/build-final.txt)


<a id="trail-cover-r21"></a>

## R21 远坡草面与林道高度场

正式地图由 `/Game/GameMaps/L_ForestPathVillage` 载入专用的 `/Game/ForestPathStudy/VillageRegion/Reference/TrailLandscape/L_ForestPathForest`。该子关卡继承样板的地貌、植被、光照与天气数据；独立样板仍在 `/Game/ForestPathStudy/Maps/L_ForestPathForest`。外围地网和正式林地 Landscape 共用世界坐标的林草覆盖图及 C 层泥路函数。道路、积水与采石场工作面按地表权重留空。

中远草按四米单元抖动落点，使用有坡向的交叉草带，每片八个三角形，38 米开始淡入，168–202 米逐渐裁剪；再远用不透明地表表现连续草甸。正式图烘焙 63,057 片，按 81 个分区组件绘制。草带无阴影、光追、碰撞和风动。泥路将原 Nordic Forest Ground Roots Coarse 扫描的苔斑从泥底分离，由世界坐标决定八种斑形的空缺、偏移、旋转和大小。泥底、法线与粗糙度共用随机投影。

从原林道涂层提取 90 米连续中心线及横向剖面，移除行进纵坡和整体横坡，保留实测局部凹凸。零点 32768 的 16 位 PNG 以毫米编码，横纵方向每个像素均为 0.5 米。米级高程数据、静态地块碰撞、林地 PCG 落点按同一新路床保存，村内既有地基及采石作业面沿用原标高。制作依次执行 `prepare_trail_cover.py`、`prepare_trail_art.py`、`author_trail_cover_materials.py` 与 `author_trail_cover_level.py`。本次未试玩或测量帧耗。

[提取的道路高度图](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/TrailCover-R21/H_StudyRoadResidual.png) · [原始剖面和输出配方](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/TrailCover-R21) · [地形制作脚本](../../Tools/WorldGeneration/ForestVillage/prepare_trail_cover.py) · [发布与恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/TrailCover-R21/published.json) · [R20 发布前文件](F:/FPSGAMEData/ArtProduction/HillsForestPath/TrailCover-R21/Before)


<a id="forest-mist-r22"></a>

## R22 林内晨雾、暮霭与雨后湿雾

正式林道村庄使用 UDS 统一写入基础高度雾。晴天样板密度 0.02，起雾距离 0，垂直衰减 0.2，体积散射 0.2，消光 1。近景体积距离沿用子关卡的 60 米；远山继续由高度雾和天空大气表现。流式子关卡到达前，桥使用同一组后备值。UDS 自有夜色、云量、天气与室内遮蔽逻辑继续工作。

区域载入时，按照实际 PCG 树位、四向地面高差及水坑岸界挑选最多 12 片林下雾带。中心落在林地缓坡、浅洼或水边，两片雾带之间留有间距；村庄地基、采石场作业区和泥路中心避开。雾带半径 28–40 米。清晨 03:30 起雾，05:30–06:30 最浓，09:30 散去；傍晚 16:30 起，18:30–20:00 有较薄暮霭，22:00 散去。雨势和风压低局部雾，雨停后按实际地表湿度逐渐消散。晴朗干燥的白天只呈现基础林雾。以上时间均为游戏时钟。局部雾本地每 0.5 秒更新一次，按五秒时间常数平滑过渡；对距所有本地视点超过 245 米的雾带关闭显示，专用服务器不创建。

控制台 `fps.Hills.ForestMist 0` 可只看 UDS 基础雾，`fps.Hills.ForestMist 1` 恢复默认，数值范围为 0–2；不改变天气预设。生产目标为 FPSGAMEEditor，未进行实机画面或 GPU 耗时验收。

[UDS 雾接管](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/FPSUDSHillsAtmosphere.cpp) · [林下雾选址与天气曲线](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/WorldGeneration/ForestVillageMistComponent.cpp) · [样板雾原始参数](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsUnderstory-R19/study-fog.json) · [发布、构建及恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestMist-R22/published.json)


<a id="forest-review-r23"></a>

## R23 正式丘陵图的材质修复与实景复核

2026-11-24 在独立存档中以离屏游戏方式进入正式关卡。初次载入时 35 款花岗岩缺少 Nanite 和实例化材质用途，远坡草带缺少 Nanite 用途，共出现 71 条默认材质回退警告。为花岗岩母材质补上用途，为八三角形草带关闭网格 Nanite。远草旧材质按天空和日月亮度自发光，清晨在树荫里呈现出整排亮片。同机位关闭草带后亮片消失。正式草带改用遮罩受光材质，草尖使用粗糙无高光的地表朝上法线，按摄像机距离在 38–58 米间淡入。实例、结束裁距、无投影、无光追和无碰撞设置沿用现有布局。最后一次载入时上述回退警告为零。

实际统计到 35 种、1,230 块花岗岩及 81 个分区的 63,057 片远草。林道碰撞采样 153 点，全部与 R21 路床吻合，本次点位相对前版低 10 至高 10 厘米。村中地基实读动态材质父级为 MI_ForestVillageMudRoad。八种山毛榉与黑杨立木均出现，近树干碰撞射线命中 12 个实例。本轮未执行从实际挥斧到幼树成熟的完整生命周期。开阔草坡成片，林道旁约 60 度的近景陡坎仍有裸地。林雾在 06:00 附近有 4 个局部雾带可见，局部消光峰值约 0.269，19:00 约 0.126。雨停后正午同点捕捉到湿雾回升。晴天 UDS 基础密度 0.02，起雾距离为零，体积距离 60 米。独立测试图未进行同光照逐像素复刻比对。

RTX 3080 Ti、1600×900、同机位三段采集按开、关、再开排列，整帧 GPU 中位数依次为 22.87、23.06、20.25 毫秒。这些短窗口记录了实景负载，不能据此证明全图性能达标。正式世界存档在复核前后 SHA-256 相同。

[固定机位远草对照](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/ForestR22Review-20261124132649/丘陵远草复查.jpg) · [城外道路与村镇草皮、花岗岩](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/ForestR22Review-20261124132649/路面与村镇.jpg) · [碰撞、天气、组件与 GPU 采集](F:/FPSGAMEData/ArtReviews/HillsForestPath/ForestR22Review-20261124132649/review.json) · [正式资源与修复前备份](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestReviewFix-R23/published.json) · [恢复文件](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestReviewFix-R23/Before)

<a id="meadow-reach-r24"></a>

## R24 远坡草的距离与覆盖、林雾和树木再生

正式入口为 `/Game/GameMaps/L_ForestPathVillage`。在原 81 个远草分区中，四米网格共保存 63,586 片草带，其中 15,899 片在 336–404 米淡出，另外 47,687 片在 168–202 米淡出。每个八米网格用固定散列选一个四米候选格延伸到远端。草带在 24.5–41.5 米渐入，分区复用同一网格和材质，保留关闭投影、光追、碰撞和风动的设置。高密度近草仍按原 PCG 格流送。

正式 Landscape 和外围网格均读取同一份米制草面遮罩和 256 像素的草皮细节。地表从 13.5–36.5 米逐步接替近草。新遮罩允许有土壤的陡坡继续显示贴地苔草，陡处另外降低直立草片的出现率，泥路、水坑、村镇地基和采石场沿用原遮罩。城外路床和村内草皮、地基均沿用上版数据。35 款花岗岩的 ORM 贴图允许流送并限制为 1024 像素，颜色和法线保留 2K；正式村镇贴地装饰批次取消光追可见性。

正式林区的局部雾在晴天正午保留少量底雾，晨暮和雨后叠加，全球基础雾仍使用 UDS 的样板参数。改动沿用原 12 个雾区上限和原体积采样距离。幼树出生与读档重建共用森林村庄的选点规则，先尝试已存位置，再按确定的角度与半径调整，使用实际地形、道路、水体和村镇边界。运行时按完整树根足迹落地；同一资源 ID 继续沿用原有生长时钟和采伐存档。已砍的首代树桩保留原树根的位置。

基于 R21 路床、R20 草皮可用 `prepare_trail_cover.py --meadow <R20目录> <R21目录> <R24制作源目录>` 复建远草数据。材质与地图的增量入口为 [author_meadow_reach.py](../../Tools/WorldGeneration/ForestVillage/author_meadow_reach.py)，调用时提供原有制作批次和数据源环境变量，批次中的 materials.json 指向正式草带网格。原全量地编流程也复用同一套选点和材质函数。

[制作源](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/MeadowReach-R24) · [改动清单及恢复哈希](F:/FPSGAMEData/ArtProduction/HillsForestPath/MeadowReach-R24/published.json) · [发布前文件](F:/FPSGAMEData/ArtProduction/HillsForestPath/MeadowReach-R24/Before) · [构建记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/MeadowReach-R24/build-final.txt)。本轮按后台制作交付，未运行试玩、截图或 GPU 性能采样。

<a id="gate-road-surface-r25"></a>

## R25 东门弯道材质对照

正式地图 `/Game/GameMaps/L_ForestPathVillage` 默认在东门外沿现有中心线 9–39 米的弯道显示 A 版，首尾各约两米渐变。A 版取 Quixel Trampled Mud Ground 作踏实路心、Gravel Dirt Path 作碎石；B 版取现有教堂 ChapelEarth 和村道 RockyRoad。草边、露根和苔斑由原 C 层在路肩露出，支路交会按中心线合并磨损权重。雨后泥色与粗糙度跟随现有 WeatherWetness。微观高度仅在近处驱动视差，路床与碰撞沿用丘陵地编高度场。

进入正式丘陵图输入 `fps.Hills.RoadSurface A` 或 `fps.Hills.RoadSurface B`，即可在同一机位比较约 30 米样段。追加 `full` 可把同一方案预览至采石场，入口前最后约 75 米逐渐增加碎石。`fps.Hills.RoadSurface original` 恢复上版本场显示。命令写当前世界的材质参数集合实例，每次重新进入地图采用样段 A。城内原泥路和独立林地样板沿用原材质。

[采集、颜色与高度源文件](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/GateRoadSurface-R25) · [路面遮罩及图集制作](../../Tools/WorldGeneration/ForestVillage/prepare_gate_road_surface.py) · [正式材质接入](../../Tools/WorldGeneration/ForestVillage/author_gate_road_surface.py) · [A/B 切换](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/WorldGeneration/ForestVillageRoadSurface.cpp) · [正式包及可恢复版本](F:/FPSGAMEData/ArtProduction/HillsForestPath/GateRoadSurface-R25/published.json) · [修改前材质](F:/FPSGAMEData/ArtProduction/HillsForestPath/GateRoadSurface-R25/Before) · [编辑器构建记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/GateRoadSurface-R25/build.txt)。


<a id="continuous-meadow-proposal"></a>

## 丘陵草地连续覆盖方案（实施版本见 R26）

以村庄东门向采石场的林坡为首段，沿用 B full 的路面配色。目标是从路上平视、横移或开瞄具时，所有允许长草的坡面都有连续的草被，能看到成片草叶的方向和草冠轮廓。地图中的干净路心、开阔水面、建筑地基、采石作业面和裸岩由现有生态遮罩排除。树下允许草变矮变稀，石块、枯枝和灌木可与草叠生。

### 截图与当前实现

截图中有较长的斜直边，草叶集中在边线上，之间的绿色地面较平。R24 每张草带约 4.7 米长，两张近乎垂直交叉；实例在四米格内抖动，按中心点和局部坡向放置。这样的草带跨过凸坡或浅洼时，边缘可能浮起或埋入地面。草面着色还用镜头距离渐入，只取草皮扫描的亮度给固定绿色着色，并按世界距离显式降低纹理 mip。该实现能解释截图中的现象，具体机位还需在正式图对照。参见 [草带网格](../../Tools/WorldGeneration/ForestVillage/prepare_trail_art.py)、[生成点及高度](../../Tools/WorldGeneration/ForestVillage/prepare_trail_cover.py) 和 [地面着色](../../Tools/WorldGeneration/ForestVillage/author_trail_cover_materials.py)。

### 实施顺序

1. **先统一哪些地方有草。** 从已有道路权重、林地与苔地权重、水面、采石区和村镇边界离线烘焙一份世界坐标覆盖图。有效草地内部保持连续，路肩用现有的不规则草舌过渡。树下疏密另存为叶簇密度，不在覆盖图上挖洞。正式 Landscape 与外围网格读取同一字段。
2. **把草皮直接画在现有地表上。** 取消基础草层的镜头距离渐入。保留扫描中的颜色和叶片尺度，加入低频草向、斑驳和共用的小法线，与现有地形法线、林下受光和天气湿润度衔接。纹理 mip 由实际视图中的像素足迹选择，使瞄具放大后的坡面仍能读取对应细节。将草皮混合到现有不透明地面材质中，避免另外铺一层共面的网格。
3. **替换露边的长草带。** 离线按覆盖图生成低矮、轮廓不规则的草簇和草冠，复用项目草种。用分层抖动或蓝噪布点避免条带排列；根点按实际地表三角形落地，坡折处拆短。保持现有近草的细叶表现；山脊和侧视坡面保留有立体剪影的草簇。简化草簇时按屏幕投影保留整体高度和占屏面积。普通视角与瞄具共享同一批落点。
4. **控制绘制成本。** 复用现有空间分区和 HISM 批次，使用共享图集和材质，遮罩几何贴紧草叶外轮廓。地表持续负责覆盖，几何仅补轮廓、视差和近处草叶；草簇的 LOD 只改变细节。保留视锥与遮挡裁剪，装饰草关闭碰撞、投影和光追。复用现有近草流送，远处草冠离线排布，镜头移动时无需重算整坡 PCG。

### 预期画面与性能比较口径

从截图所示侧坡看，草被应沿坡连续起伏，横移时无交叉直边，开瞄时仍可辨认草丛和山脊的草冠。道路 B full 的路心与清理区保持可辨。后续验收可在同一存档、机位、天气、分辨率和瞄具倍率下对照 R24，记录整帧 GPU 中位数、P95、遮罩过度绘制及峰值显存；先看草带过度绘制与掩膜边界，再决定是否需要调整局部几何预算。实施与恢复记录见 [R26](#continuous-meadow-r26)。


<a id="continuous-meadow-r26"></a>

## R26 全图连续草被与默认 B 版道路

`/Game/GameMaps/L_ForestPathVillage` 的 1,024 × 1,024 米草地与苔地使用每米一格的世界覆盖图。正式 Landscape 与外围网格都将扫描草皮颜色和细法线混入现有不透明地面。像素着色按当前视图导数选择 mip，覆盖权重由地面位置决定。泥路、水面、村庄地基与采石场采用各自已有的生态遮罩，独立岩石保持原材质。陡坡渐变为低矮苔地。默认道路设置为 B full，从东门一路至采石场；R25 控制台指令继续可用。

旧长草带已移出地图。离线沿最终路床与山坡高度场烘焙 257,812 组不透明草簇，归入 81 个 HISM 分区。各簇按地面三角形扎根，坡折处缩短根盘，树下适当降低叶簇密度及高度。近景和中景原细叶仍作附加细节。新草簇起止裁距为零，按网格屏幕占比使用 105、28、7 三角形的三级轮廓；采用实例批次与遮挡裁剪，关闭碰撞、投影、光追与风动。草皮与叶簇沿用原有天气湿润度。

[数据与三级 FBX](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/ContinuousMeadow-R26) · [数据生成](../../Tools/WorldGeneration/ForestVillage/continuous_meadow.py) · [R26 归档网格配方](F:/FPSGAMEData/ArtProduction/HillsForestPath/ContinuousMeadow-R26/Release/Tools/WorldGeneration/ForestVillage/build_meadow_crown.py) · [材质和地图制作](../../Tools/WorldGeneration/ForestVillage/author_continuous_meadow.py) · [地面着色](../../Tools/WorldGeneration/ForestVillage/continuous_meadow.ush)。用 VillageFlora-R20、TrailCover-R21 及 R26 输出目录运行数据生成，随后用 Blender 后台导出三级 FBX。在设置 FPS_FOREST_REFERENCE_BATCH 和 FPS_FOREST_REFERENCE_SOURCE 的宿主里制作并保存关卡。

[正式发布与恢复哈希](F:/FPSGAMEData/ArtProduction/HillsForestPath/ContinuousMeadow-R26/published.json) · [发布前版本](F:/FPSGAMEData/ArtProduction/HillsForestPath/ContinuousMeadow-R26/Before) · [正式资产和制作代码](F:/FPSGAMEData/ArtProduction/HillsForestPath/ContinuousMeadow-R26/Release)。本轮全图后台落盘，画面与显存、帧耗交由用户检查。


<a id="fine-meadow-r27"></a>

## R27 删除宽三角叶草，丘陵补充层复用细叶草

正式地图为 `/Game/GameMaps/L_ForestPathVillage`。R26 的 SM_ForestMeadowCrown 和专用 M_ForestMeadowLeaf 已从正式 Content 删除。关卡保存后资产注册表中该网格的引用为零，材质的唯一剩余引用来自该退役网格。对应的三级源 FBX、旧落点数据和生成宽叶的脚本已从活动制作位置移出。旧版所用文件与精确路径、字节数和 SHA-256 在本批恢复清单中。

补充草层在 81 个空间分区中使用 16,126 组原生细叶低草 SM_RainforestGrassLow，材质绑定 MI_HillsGrassLow。补充层从原来的 257,812 组减至 16,126 组，采用现有网格较轻的两个细节级别，关闭风动位移、投影、光追和碰撞。近处及中景原 PCG 草负责密度，全图连续草皮仍按地表覆盖，坡面的细叶疏密由原有树距、坡度、湿岸和路肩权重决定。村路沿用 B full。

[新制作源](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/FineMeadow-R27) · [细叶落点烘焙](../../Tools/WorldGeneration/ForestVillage/continuous_meadow.py) · [正式图生成入口](../../Tools/WorldGeneration/ForestVillage/author_trail_cover_level.py) · [删除、发布与恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/FineMeadow-R27/published.json) · [替换前文件](F:/FPSGAMEData/ArtProduction/HillsForestPath/FineMeadow-R27/Before)。本轮后台保存，未进行试玩或性能采样。

<a id="hill-relief-pools-r28"></a>

## R28 原参考坡面凹凸与林中水坑加倍

正式地图 `/Game/GameMaps/L_ForestPathVillage` 在实际可蓄水洼地上生成了 12 处水面，前版为 6 处。丘陵原本按蓄水条件筛选、按东门距离和空间分散程度排序，并限制全图数量。新选择预算为 12，保留每 64 米地块一处、中心相隔至少 26 米的约束。东门先选可达的近池，其余名额优先面积 40 平方米以内的洼地，再在候选不足时补选较大洼地。最终距东门地基采样点最近的水坑约 47.5 米，面积范围 19–62 平方米，最大水深的范围为 10–44 厘米。水面、湿岸、植被和交互水深共同读取此次闭合盆地烘焙结果。

原参考林坡世界范围为（−189,−63）至（−91,59）米，每米一个样本。去除高程量化台阶和长坡之后，小尺度起伏与坡肩的半相关距离分别约为 6 米和 17 米。两档有符号残差从相同的原图位置取样，按目标坡向旋转；样本中心用最小间距随机选取，圆形权重平滑交叠，平缓林地与较陡坡面选用不同的参考部位。外围 2 米网格对最窄细节做额外低通。原参考林地、两条泥路路床、村庄平台和采石作业区设有过渡保护；村内开放庭地在已有建筑退距和路网遮罩内另作厘米级调整。原有树木采伐身份、岩石池和 B full 材质沿用。更新了碰撞地块、林地 PCG、岸草、近草点位及 R27 细叶草补充层。

[最终厘米高度场 PNG](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/HillReliefPools-R28/H_Region_R28.png) · [参考提取与处理数据](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/HillReliefPools-R28/relief.json) · [实际水坑清单](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/HillReliefPools-R28/Grass/ponds.csv) · [制作与恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillReliefPools-R28/published.json) · [改动前文件](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillReliefPools-R28/Before) · [编辑器构建记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillReliefPools-R28/build-publish.txt)。

从原制作根与 R28 输出目录运行 [高度场提取和准备](../../Tools/WorldGeneration/ForestVillage/prepare_hill_relief_pools.py)。在隔离宿主设置现有的 FPS_FOREST_REFERENCE_SOURCE 与 FPS_FOREST_REFERENCE_BATCH 后运行 [地形、水坑和植被制作入口](../../Tools/WorldGeneration/ForestVillage/author_hill_relief_pools.py)。外部覆盖烘焙使用 NumPy、SciPy 和 Pillow，可用 FPS_TERRAIN_PYTHON 指定解释器。此批为后台制作，未进行试玩或视觉验收。

<a id="forest-litter-r29"></a>

## R29 路肩落叶和林下倒木

正式地图为 `/Game/GameMaps/L_ForestPathVillage`。东门林道与采石场道路两侧沿里程分别取种子，决定落叶的聚集位置、长宽和强弱，排除路心、村内地基、积水和采石作业面。三款不同的 Fallen Leaves 与一款 Fallen Leaves And Twigs 打入共用图集，保存扫描的基色、透明遮罩、细法线和粗糙度。落叶随 R28 路面和坡面着色、随项目天气湿润，按屏幕像素足迹淡去细节；不创建单叶 Actor 或投影贴花。B full 路面与 R27 的细草沿用原设置。

六组 Quixel 倒木和苔木各有两款 UE Medium 实扫，正式 PCG 烘焙 869 个实例。其中普通倒木 95、倒伏松木 119、大型倒木 6、落松枝 253、苔木段 267、苔树桩 129。近路布置时检查整段木料的足迹；林内使用树距和湿岸权重，排除重叠、水面、路心与采石场。在编辑期按真实网格的主轴和分段底部支点贴合地形，悬空或埋入差异过大的落点放弃。木料为静态装饰，使用共享 PBR 母材质和 HISM，按尺寸淡出，关闭碰撞、导航和光追。较大的树干保留栅格投影。纹理允许流送，按部件分别限制尺寸。

PCG 数据加载按每组至多 48 个输出分页，图内的实际变体分别连到对应的生成器。分布图、网格支撑与实例变换在后台制作和存图时生成。正式高度场重烘焙入口会按新的中心线、水坑和树位更新路肩分布与木料摆位。

[官方条目、来源哈希及发布清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestLitter-R29/published.json) · [原始下载及制作源](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/ForestLitter-R29) · [已布置点位与网格统计](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestLitter-R29/baked.json) · [替换前版本](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestLitter-R29/Before) · [构建结果](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestLitter-R29/build.txt)。制作入口分别为 [扫描导入](../../Tools/WorldGeneration/ForestVillage/import_woodland_scans.py)、[散布和图集制作](../../Tools/WorldGeneration/ForestVillage/prepare_forest_litter.py) 和 [关卡保存](../../Tools/WorldGeneration/ForestVillage/author_forest_litter.py)。本轮为后台制作及必需构建，未运行性能采样或游戏验收。

<a id="forest-ecology-r30"></a>

## R30 林地 PCG 生态层

正式主图保留原内容路径，组合乔木、灌木、草本、岩石、枯木、林床装饰与湿地七个子图。单个加载节点最多 24 个输出，岩石组分为 24 和 17 两页。六个无点的生成器不参加本次烘焙。两个已验证的独立组合随正式资产发布。R29 两张混合点表在引用迁移完成后归档。

[层清单、组合示例与重建方法](../WorldGeneration/forest-village-ecology.md) · [检查记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestEcologyLayers-R30/audit.json) · [源码与正式包恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestEcologyLayers-R30/published.json) · [修改前文件](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestEcologyLayers-R30/Before)

<a id="landscape-themes-r31"></a>

## R31 丘陵景观与道路景观主题

正式关卡现由两个独立的主题组件生成。普通道路带按原项目的 13.3 米路肩范围分配，沿路和林内的倒木按生成来源分配，湿地归丘陵。七个生态层组合仍可复用。[主题职责、独立构建与共享依赖](../WorldGeneration/hills-landscape-themes.md) · [发布清单与恢复版本](F:/FPSGAMEData/ArtProduction/HillsForestPath/LandscapeThemes-R31/published.json)。

<a id="village-loess-r32"></a>

## R32 村内黄土、墙脚与山脚

正式图 `/Game/GameMaps/L_ForestPathVillage` 的村内土面沿八边形城墙和斜切角分配黄土权重，在墙外 4.5 米内过渡到林地。村内原有脚踩泥路和城门外的 B full 道路保留原路面混合。黄土的颜色、法线与高度来自项目内的 ChapelEarth 扫描，1.58 米平铺，近景使用高度偏移，并读取天气湿度。磨坊的独立土肩复用同一套材质。真实高度由一米网格承载，墙脚、门槛和建筑承重处保留原支撑标高。

原参考林地的外缘过去按近似固定宽度收坡。新版按已有山脊、坡向和沿山脚的位置改变延伸距离，并与原高度图的局部凹凸合成。M 键地图沿用真实地面和 5 米等高距，按局部坡度抗锯齿绘线。墙边 2,300 个可整地采样点的坡度第 90 百分位从 21.51% 降至 7.50%。受保护的原参考地形、两条道路的路心、水坑和采石工作面抽取网格与 R28 高差为零。正式包、碰撞和两个主题点集的贴地结果已保存，尚未试玩。

[丘陵高度源（16 位，厘米，零标高编码为 32768）](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageLoessFoothills-R32/H_Hills_R32.png) · [村庄高度偏移](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageLoessFoothills-R32/H_VillageLoessOffsets.png) · [同范围等高线对照](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/VillageLoessFoothills-R32/丘陵等高线对照.png) · [墙边坡度对照](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/VillageLoessFoothills-R32/村庄墙边坡度对照.png) · [正式包与源码版本](F:/FPSGAMEData/ArtProduction/HillsForestPath/VillageLoessFoothills-R32/published.json) · [前版恢复文件](F:/FPSGAMEData/ArtProduction/HillsForestPath/VillageLoessFoothills-R32/Before)

<a id="village-loess-review-r33"></a>

## R33 村庄地面实景复查

晴天 10:45 以相同机位复拍正式关卡的墙脚、黄土地面、东门和村内全景。黄土复用 ChapelEarth 的颜色、法线和打包高度，收敛亮部橙色，加入同一扫描较大尺度的色差。墙外侧按实际城墙轮廓、道路和湿地边界补入 14,065 个近景细草点，共 45 个已有网格单元。近草使用流送后的村庄地表定位。先前 5,871,968 个近草点的字节一致，PCG 掩膜规格、剔除距离和投影开关沿用既有设置。马厩车道贴花从接近东门处减淡，向院内逐渐恢复原覆盖率，保留扫描纹理和车辙法线。本轮复用了 R32 物理高度场；M 键地图与山体均在正式关卡拍摄。

[地面同机位前后对照](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/VillageLoessReview-R33/村庄地面同机位对照.jpg) · [村庄、林缘与 M 键地图](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/VillageLoessReview-R33/丘陵与村庄实景.jpg) · [原始截图和机位数据](F:/FPSGAMEData/ArtReviews/HillsForestPath/VillageLoessReview-R33/Final) · [制作源](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/VillageLoessReview-R33) · [正式包、源码和恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/VillageLoessReview-R33/published.json)

<a id="road-leaf-edges-r34"></a>

## R34 路肩落叶随机边缘与坡面贴花

东门林道和采石场道路沿用 R29 登记的四个 Quixel 扫描。新图集按素材固定种子生成不规则外缘，边界处的小片独立叶按连通形状整体取舍，重叠叶堆渐隐。地表可从相邻网格取样，交界处的混合顺序稳定。在 36 万个均匀采样点上比较材质的叶片透明覆盖均值，R29 为 9.96%，R34 为 9.80%，该数值用于对照叶量。修正由现有地形材质绘制，沿用已有叶片渲染距离。

正式图的 46 个苔斑、43 个泥斑已按地形法线定向。生成时按斑块覆盖的实际高度校正投影深度，原点集、水平散布位置及贴花宽度保留；已保存的演员与两份 PCG 点表同步更新。按有可见透明度的区域、每张贴花 61 × 61 个 UV 采样验证，受投影盒截断的苔斑和泥斑由 46 处降到 0 处。原林地各 27 个 Dried Leaf Pile 和 Buffalo Grass 在相同检查下均未发现截断。

[实景固定机位对照](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/LeafEdges-R34/实景前后对照.jpg) · [四款图集透明轮廓](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/LeafEdges-R34/四款落叶边缘对照.jpg) · [制作输出](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/LeafEdges-R34) · [发布、原包哈希及检查记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/LeafEdges-R34/published.json) · [修改前文件](F:/FPSGAMEData/ArtProduction/HillsForestPath/LeafEdges-R34/Before)

<a id="cliff-exposure-r35"></a>

## R35 路堑和陡坡露岩

正式图 `/Game/GameMaps/L_ForestPathVillage` 在 R32 地形上计算局部坡度、路肩至路心高差、道路退距和林下土壤残留。切坡从约 28°、普通山坡从约 36° 开始露岩，约 11° 范围内渐变，局部阈值随风化场变化。坡面由真高程和岩石法线共同塑形。正式森林 Landscape 副本使用独立可重复写入的 `Forest cliff relief` 编辑层，外围地块同步更新渲染网格与碰撞。

Quixel 的 Layered Rock Cliff 和 Granite Rock Face 提供裂隙、矿物颜色与高度。随机取样以三维世界位置为种子，每个共享顶点确定同一组旋转、缩放和偏移，按扫描高度混合相邻样本。裸岩架和苔岩架分别来自 Coast English Rock Shelf Stone Medium 09 和 Nordic Forest Ledge Rock Large，开口边缘沿坡面嵌入。岩架归入坡面所在主题的岩石 PCG 层，路心、墙基、池岸和采石工作台地保留。

本次生成改变 12,551 个米级高程点，变化为 -26 到 +26 厘米。两个主题共生成 57 处岩架，其中林内 42 处、道旁 15 处。近景草与中远景草使用同一露岩范围退让，岩架使用 HISM、Nanite、100 米剔除。正式工程资产与截图所用资产逐包对照，试玩读取的 28 个外围碰撞采样与输出高度图的最大误差为 0.00 厘米。截图仅代表记录的晴天机位。

[路堑与林坡同机位对照](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/CliffExposure-R35/路堑与山坡同机位对照.jpg) · [主山对照](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/CliffExposure-R35/丘陵山体对照.jpg) · [原始截图](F:/FPSGAMEData/ArtReviews/HillsForestPath/CliffExposure-R35/PublishedViews) · [高度图与扫描来源](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/CliffExposure-R35) · [正式工程发布与恢复文件](F:/FPSGAMEData/ArtProduction/HillsForestPath/CliffExposure-R35/published.json)

<a id="cliff-talus-r36"></a>

## R36 坡脚碎岩

R35 岩壁下方按坡降、露岩权重和地面坡度寻找堆积位置。路心、村庄、采石工作面与水岸设有保护距离，已有岩块与树根作为占地约束。42 处堆积共 472 个小型实例，复用工程现有的两款 Quixel Small Granite Rock 扫描，各自约 12 和 22 厘米宽。细碎石偏向岩脚，较大的断片可沿下坡多滚一段。固定种子保证重建时位置可复现。

丘陵景观的 Rocks 子图保存 203 个细碎石和 85 个断片，道路景观的 Rocks 子图保存 123 个细碎石和 61 个断片。细碎石与断片的末端剔除距离分别为 28 和 42 米，复用 HISM 且关闭碰撞、投影与光追。原岩架、母岩高度和岩壁材质仍按 R35 配方制作。本轮使用后台编辑器命令保存岩石子图、分页点集和正式丘陵图；未运行试玩。

[两主题分层与组合说明](../WorldGeneration/hills-landscape-themes.md) · [生成配方](../../Tools/WorldGeneration/ForestVillage/prepare_cliff_talus.py) · [分主题点集与 Quixel 素材索引](F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/CliffTalus-R36) · [发布回执及原包恢复版本](F:/FPSGAMEData/ArtProduction/HillsForestPath/CliffTalus-R36/published.json)

<a id="forest-audit-r37"></a>

## R37 正式图联机与运行成本

检查覆盖监听服与客机的地面、天气、远端砍树及重连，三个固定机位的帧耗，以及正式关卡的水坑、局部雾、碎石、角色档案和 M 键地图。树干碰撞与本地树冠分开调度，树龄单独同步。按样本、条件和未完成项阅读[正式图审查记录](../WorldGeneration/forest-village-network-performance.md)。[源码与恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestAudit-R37/published.json)

<a id="landscape-authoring-r38"></a>

## R38 户外地编技能

后续说“构建丘陵景观”或“修改道路景观”时，从[户外地编工程入口](../../skills/ue5-landscape-authoring/SKILL.md)选择高度源、实际主题组件和配方。原作者教程按上文章节取方法，正式图以 R27 的细叶草、R31 的双主题、R32–R36 的村墙与岩壁等现行配方为依据。通用流程的个人维护源、项目发布快照及路由恢复位置见[技能发布清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/LandscapeAuthoringSkill-R38/published.json)。
