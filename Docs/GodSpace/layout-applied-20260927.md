# 主神空间浮空布局接入 · 2026-09-27

当前交付状态与重建入口统一见 [2026-09-28 整理与发布](publication-20260928.md)。下方大地和旧云补色段落属于已替代历史；当前下方为海洋、云海隐藏、地毯 V2 与连续金属条已保存。本文旧路径若已归档，按 [文件清单](../AssetArchives/godspace-20260928.json) 查询。

用户已确认应用布局，并删除水池、草地测试场景及其传送门，保留丘陵。本次完成源码修改、Editor 目标构建、资产导入和正式关卡保存。没有启动游戏、截图、运行测试或性能采样，效果由用户测试。

## 已保存的主场景

正式关卡仍为 `/Game/GameMaps/DayNight_Lighting`，显示名称继续使用“主神空间”，保留原关卡路径与存档标识。

- 使用原有大理石组件落实 80×96 m 切角平台、分层浮空基座、中轴喷泉、北侧祭坛、西侧星座凉亭与东侧生产仓储区。
- 新增结构网格包含底裙、檐线、切角补片、祭坛台阶、侧面缓坡、铺地线条、石凳和唯一保留的丘陵门底座。光球与环作为环境装置接入，没有新增主神玩法。
- 原有喷泉 Actor、祭坛标签、火把及其昼夜逻辑保留。重复柱栏形成 50 个局部实例组；地砖保留原来的 LOD1 使用策略。新结构约 5,400 三角面，核心装置约 5,280 三角面。
- 预览局部坐标整体平移 `(-2400,-1300,0) cm`。东侧院扩大到 28×21 m，以容纳玩家已有高炉、铸造台、工作台和建造箱子；未重写建造存档、炉内状态或库存。
- 出生点改到南侧到达区，世界位置 `(-1100,-5100,125) cm`，朝向中央与祭坛。丘陵门世界锚点为 `(-200,-4200,50) cm`，不再按玩家临时站位生成。仓库锚点为 `(500,-500,20) cm`，保留现有仓库与箱子的存储标识。
- 原 5 km 测试地板已从主关卡移除，新台面和结构承担静态碰撞。

## 云与大地

只使用游戏已有 `/Game/Weather/Materials/MI_FPSLayeredClouds` 及其纹理。丘陵继续使用继承该实例的 `MI_HillsClouds`；天气、连续风运动和昼夜控制保持共用。

主场景的 `SkyAtmosphere` 改为以组件位置定义地面，高度基准位于平台下方 1.5 km。现有单个体积云组件云底海拔 0.9 km、厚度 0.32 km，因此相对平台为下方 600～280 m。没有新增云图集、云片或第二套天气时钟。天空 Actor 的 `GodSpace.CloudSea` 标签让天气控制保留该关卡的云层高度，雨天不会被重新推回旧的 1.55 km 云底。

云视图采样倍率设为 0.7、阴影 0.4、反射 0.25、反射阴影 0.2，追踪距离 30 km。这些是制作设置，不是实测性能结论；全局 Lumen／硬件光追配置未改。

大地已按用户反馈改为库内地表混合烘焙：24 km 主体、不规则山脊与主河／支流、按地球曲率下沉的圆形远端延伸，共 90,624 三角面；4K 宏观颜色图与 2K 细节法线图。颜色使用丘陵已有的草地、开挖土壤、苔藓碎石和干土贴图混合到草坡、林地、河岸和裸岩分区，原始资源不改。材质运行时采样两张图，远距离仅轻微降低饱和度，雾色由现有大气系统处理。背景地表无碰撞、不投影，并关闭该组件的距离场光照和光追可见性；保持纹理流送和正常 mip。没有下载外部地理数据，也没有引入额外地形插件。

## 退役场景

已从 Content 删除以下关卡，并保留 SHA-256 归档回执：

- `/Game/Clearwater/L_ClearwaterWater`
- `/Game/GameMaps/L_GrassDeformDenseTest`

归档位于 `trash/godspace-layout-20260927/Retired/Content/`。只退役这两个关卡包，共享水材质、植被、草交互和丘陵资源仍保留。主场景与丘陵中的水池／草地传送门生成逻辑已删除；草地地图的打包列表和两个地图的预加载引用已移除。丘陵往返门及地牢流程保留。

原主场景备份位于 `trash/godspace-layout-20260927/Before/Content/GameMaps/DayNight_Lighting.umap`。旧测试场景制作脚本保留为历史工具，当前接入不执行它们。

## 交付文件与状态

- 新资产：`Content/Props/GodSpaceLayout20260927/`，共 3 个网格、3 个材质和 2 张贴图，已导入并保存。
- 制作源：`SourceAssets/GodSpaceLayout20260927/Integration/`。`export_accepted_layout.py` 从原 Blender 方案导出构件和坐标；随后执行 `import_assets.py`、`apply_map.py` 与 `retire_test_maps.py`。
- `Receipts/import.json`、`map.json`、`retired-maps.json`：保存／删除回执；`hub-backup.json`：旧地图备份信息。
- `Receipts/editor-build.log`：本次常规 FPSGAMEEditor 构建成功。没有运行打包构建或游戏测试。
- 工作开始时编辑器关闭，先在后台读取与构建。后续发现编辑器已打开，资产与地图操作改经现有 MCP 批次互斥；为保存地图结束了当时的 PIE，没有关闭编辑器或自动重新开始游戏。

此前 `Preview/` 图片是布局 V1 历史预览，仍显示三个门及 Blender 占位云；不代表本次接入后的 UE 实机画面。本次没有追加预览渲染。

## 出生姿态修复 · 2026-09-27

用户报告人物陷入地下，并自行进入游戏供定位。读取该次运行发现：胶囊中心 Z=118.15 cm、半高 96 cm，角色处于 Walking，脚底在 20 cm 地面上方约 2.15 cm；相机局部高度为 74 cm，但世界高度只有 101.70 cm。原因是制作脚本使用 `unreal.Rotator(0, heading, 0)`，实际把 heading 写入 Pitch，角色继承出生点约 102.85° 的倾斜，相机随父组件旋转降到低处。

已将出生点、模块化建筑与锚点的旋转全部改为显式 `pitch=0, yaw=heading, roll=0`。先扶正用户当前角色，再结束该次 PIE，通过既有 MCP 互斥连接重新保存本批布局，保留原出生位置、地面高度、玩法 Actor 和 50 个实例组。未改角色相机高度或通用出生碰撞逻辑；无需 C++ 编译。

修复前正式地图备份：`trash/godspace-spawn-rotation-20260927/Before/Content/GameMaps/DayNight_Lighting.umap`；散列记录与保存回执分别为 `Integration/Receipts/rotation-backup.json`、`rotation-map.json`。诊断数据位于 `Integration/SpawnRepair/`。修复后没有自动重新开始游戏或运行验收，交由用户重新进入查看。

## 库内地表复用与远景修订 · 2026-09-27

用户截图显示旧背景的规则波纹和单一绿色，随后要求优先使用库内地表贴图。本次复用以下已存在、也供丘陵地表使用的资源：

| 地表 | 库内颜色贴图 |
| --- | --- |
| 草地 | `/Game/PN_GrassLibrary/Textures/LandscapeTextures/ground_I_albedo` |
| 土壤／河岸 | `/Game/UnrealNormandy/Textures/T_LC_GroundSoilExcavated_00A_Albedo` |
| 苔藓碎石／裸岩 | `/Game/UnrealNormandy/Textures/T_LC_MossyGravel_00A_Albedo` |
| 干土 | `/Game/UnrealNormandy/Textures/T_LC_GroundDry_00A_Albedo` |

近景继续使用已有各套材质的法线、高度与粗糙度契约；主神空间的背景地表使用离线烘焙结果，避免把丘陵的近景视差／多层采样整套带到远景。烘焙改变采样方向与尺度，并以不规则植被、坡度和河谷遮罩分区。纹理采用 mirror 寻址、mip 和流送，外圈 UV 保持世界尺度。现有云层、天气材质与布局出生修复不变。

`export_library_ground.py` 导出本项目拥有的源图供同项目派生使用，来源记录在 `EarthLibrary/sources.json`，不表示允许将原图或派生素材单独再分发。`author_distant_earth.py` 制作网格及两张图，`import_distant_earth.py` 导入、建立材质并保存。原完整布局导出／导入脚本已接入同一路径，重建不会恢复旧的正弦波背景。

备份位于 `trash/godspace-earth-library-20260927/Before/Content/`；制作和保存回执为 `Integration/Receipts/earth-authored.json`、`earth-import.json`。本次完成后台制作与既有编辑器中的资源保存，未启动游戏、追加截图、渲染或性能测试。

### 颜色未显示与围墙状边界修复

用户再次提供截图后，读取正式资源发现网格同时保留了地表材质槽和 `WorldGridMaterial` 槽。新 FBX 没有命名材质，重导入追加了默认槽，而原脚本仅绑定第 0 槽。这解释了截图中的灰色网格噪点，颜色源 PNG 本身含草地、林区、土壤与河流。已在 FBX 中明确 `Earth` 材质槽，并在导入后给所有结果槽绑定同一个远景地表材质。

旧外圈把最边沿 UV 原样复制到延伸环，产生退化 UV 和长条拉伸；三个方形延伸环也留下规则边缘。已改为 11 圈圆形地形，延伸至半径 220 km，按 6,360 km 地球半径施加曲率，使外缘低于从主神空间观看的地平线；UV 随世界坐标延续，镜像采样避免边缘像素无限拉长。地表材质取消额外蓝灰色覆盖，仅保留 15 km 以外轻微去饱和。

诊断依据保存于 `Integration/EarthRepair/colour-boundary.json`，本轮修复前资产备份在 `trash/godspace-earth-colour-boundary-20260927/Before/Content/`。本轮只进行问题定位、资源重建与保存；没有启动游戏或进行修复后的视觉验收。

## 矮围栏上横杆碰撞修复 · 2026-09-27

用户报告矮围栏上横杆可穿过。读取用户当前 PIE 中的围栏发现：横杆与栏柱组件均为 `QueryAndPhysics`、`BlockAll`，Pawn 和 Visibility 通道均阻挡；但共享 `SM_RomanRail_200` 的 BodySetup 内盒、凸包、球和胶囊数量全部为 0。栏柱已有凸包，本次不改。

已在共享横杆资产上生成单个 200×40×40 cm 盒碰撞，局部中心 `(0,0,20) cm`，覆盖横杆本体；采用 SimpleAndComplex，角色走简单碰撞，复杂查询保留模型几何。整圈已有实例继续复用该资产，没有新增隐藏墙面或改变围栏摆放。保存网格前结束了用户当前 PIE，未关闭编辑器或启动新的游戏测试。

`Integration/ensure_rail_collision.py` 已接入 `apply_map.py` 的围栏放置前阶段；原建材生成脚本 `SourceAssets/RomanColumn20260915/integrate_railing_kit_20260917.py` 同步改用原生盒碰撞生成，并处理已有资源缺少碰撞的情况。本轮仅保存 2 米横杆资产，没有执行旧脚本的建造存档或面板重建流程。

定位数据：`Integration/RailRepair/collision-before.json`；保存回执：`Integration/Receipts/rail-collision-saved.json`；原资产散列备份：`trash/godspace-rail-collision-20260927/Before/Content/Props/RomanColumn20260915/SM_RomanRail_200.uasset`。已完成资源保存，修复后的行走／跳跃由用户测试。

## 海洋与云海替换 · 2026-09-27

按用户最新方案，正式主场景的 `GodSpaceDistantEarth` 已替换为 `GodSpaceDistantOcean`。海平面位于平台下方 1,500 m；单层球面海壳延伸到半径 220 km，外圈沿实际球面曲率落至地平线之后，没有竖直裙边。当前为 6,721 顶点、13,248 三角面，旧地表为 90,624 三角面。原地表资源保留为历史制作源，正式地图和完整重建脚本均已切换海洋。

海洋沿用当前 `MI_ClearwaterWater → M_ClearwaterWater_Native` 的 SingleLayerWater 原生光照、吸收／散射参数与水面高光模型，使用库内 `T_Ocean_Waves01_Normals`、`T_Ocean_Waves02_Normals`、`T_Ocean_Foam` 三张已有贴图。派生远景材质只做三次纹理采样、法线流动和稀疏白沫；随距离衰减波纹并增加粗糙度，减少地平线闪烁。不执行 48 波谱、WPO、冲击／尾迹场、焦散图集、水底或水下后处理，没有新增水体 Actor 或 Tick。原有水体注册表按具体网格登记，新海面不注册交互；组件无碰撞、overlap、投影、贴花、距离场光照和光追可见性。海面网格自身关闭距离场生成、光追几何和 CPU 数据保留；全局 Lumen、光追和昼夜系统保持原配置。

云层仍是原有的一层 VolumetricCloud，范围在平台下方 600–280 m。`M_GodSpaceCloudSea` 派生自当前 `M_FPSLayeredClouds`，`MI_GodSpaceCloudSea` 复制已有云实例的纹理绑定，继续使用现有风动、雷光和太阳／月亮光照。覆盖控制改为该场景独立的 `GodSpace_CoverageBias=0.12`，云图周期 32 km，按约 80% 覆盖的美术目标配置，避免运行时被丘陵晴天的稀疏云量覆盖。**0.12 是噪声偏置，不是覆盖百分比；80% 为设计目标，未采集画面测量实际覆盖率。**

云海不叠加第二层云或粒子，关闭第三层细节噪声。主视图采样倍率 0.7，阴影 0.35，反射 0.2，反射阴影 0.15；保留一阶多次散射。最大追踪距离 160 km 用于衔接下视地平线，实际体积云成本仍取决于视角和遮盖面积，不能用三角面数量推断帧率。本轮未采样帧率或 GPU 耗时。

制作入口：`Integration/author_distant_ocean.py`（后台 Blender 导出）、`produce_distant_ocean.py`（导入、编译与定点地图保存）、`ocean_mesh_budget.py`（网格预算）。完整布局的导出、导入、放置脚本已同步；本次没有重建建筑或改动出生点、栏杆、喷泉及交互存档。

新资产为 `SM_GodSpaceDistantOcean`、`M/MI_GodSpaceDistantOcean`、`M/MI_GodSpaceCloudSea`，均已写入 `Content/Props/GodSpaceLayout20260927/`。保存回执为 `Receipts/ocean-import.json`、`ocean-map.json`、`ocean-mesh-budget.json`。旧地图与散列备份位于 `trash/godspace-ocean-20260927/Before/Content/GameMaps/DayNight_Lighting.umap`。本次通过既有批次互斥，在编辑器关闭后以 NullRHI commandlet 完成后台落盘，没有启动编辑器、游戏、截图或验收，实际效果由用户测试。

### 连续海面、近远衔接与棋盘材质修复

用户进一步明确：整个下方视野都应是连续海洋，近处有动态水面效果，远处用低成本贴图衔接，不能只出现局部水块。该轮反馈同时定位到两个具体故障：SM6 编译日志报 `Sampler type is Normal, should be Linear Color`，因为库内 `T_Ocean_Waves01_Normals`、`02` 实际是 `TC_VECTOR_DISPLACEMENTMAP`、UI 纹理组，上一版错误地直接接 Normal 采样器；因此游戏回退棋盘材质。另一个故障是昼夜蓝图的 `volumetric Cloud Settings` 仍持有旧值，在构造/刷新时把组件改回不可见、追踪距离 3 km。上一版只写组件值，没改蓝图真正的设置来源。NullRHI 保存成功不能证明 SM6 材质可用。

本轮制作将现有海浪图派生为两张 1K、BC5、WorldNormalMap、带 mip 与流送的场景专用资源，原库不改。材质采用一张连续球面网格的两个 section：0–12 km 为现有原生水体的近景视觉，5–12 km 渐变至远景；12–220 km 只使用一张海浪贴图和普通受光材质，取消 SingleLayerWater 的水体专用 pass。近景 4 次纹理采样、远景 1 次；近景白沫、法线、颜色、粗糙度和水体散射权重一起过渡，section 边界共享顶点并使用相同的最终颜色/法线/粗糙度表达式。总面数仍为 13,248，没有叠加重合水面或透明边缘。近水外观源与无交互约定不变。

`configure_cloud_sea.py` 将云海设置写入主场景昼夜 Actor 的配置结构，保留现有蓝图和天气逻辑；同时使 SkyAtmosphere 的海平面位置采用绝对坐标，避免随父级太阳组件旋转。完整重建脚本也使用这一入口。针对本次资产的材质编译属于制作步骤，会处理编译返回的错误；不额外启动游戏或验收渲染。备份使用 `trash/godspace-ocean-continuous-20260927/Before/Content/`，避免覆盖上一轮恢复点。

本轮已使用后台 D3D12/SM6 commandlet 完成近水、远水和云材质编译，并保存 9 个资产及正式地图。制作时还处理了 UE 5.8 批量删除表达式遗漏旧水体输出节点的问题，改为快照逐节点删除后重建本任务拥有的海洋材质。最终生产日志为 `Receipts/ocean-v2-production-save-stdout.log`，保存回执为本轮更新的 `ocean-import.json`、`ocean-map.json`。云配置结构中的启用状态和 160 km 追踪距离已随地图落盘；约 80% 仍是云量设计目标，未作画面测量。没有启动游戏、截图或性能采样。

### 水面拉丝与缺少起伏修复

用户截图出现贯穿海面的放射状长线，且缺少波动。本次读取原库材质及源图确认：`T_Ocean_Waves01_Normals`、`02` 尺寸实际为 **961×63**，用于 `MS_VertexAnimationTools_MorphTargets` 等顶点动画路径；上一轮将这类查找数据当二维法线平铺，是资源类型使用错误，改成 BC5 仍不能修复其空间含义。诊断源图和原材质引用记录在 `Integration/OceanWaveSources/`。

已换成原库 `M_Ocean` 实际使用的二维纹理家族：`T_Water_Normal_Large` 与 `T_Water_Normal_Subtle`，派生为本场景的 `T_GodSpaceOceanSurface_N`、`T_GodSpaceOceanDetail_N`，均为 1K BC5、mip 与流送开启。原错误派生 A/B 图不再被当前海洋材质引用，原库资源不改。波纹使用世界空间法线，避免贴图方向与放射网格切线耦合；提高近水粗糙度，压低针状亮斑。

新增 `OceanSwell.hlsl` 的两层几何涌浪（波长 640/370 m、振幅 6/3 m，使用与现有 Clearwater 相同的深水色散关系），高度和法线来自同一波场；`OceanChop.hlsl` 的 140/65 m 两层细波仅作用于法线。浪尖白沫由涌浪波峰与现有白沫纹理共同控制。几何位移从 2.5 km 开始减弱，5 km 归零；海面中心改为 80 m 格距的规则网格，外围保持低密度曲面，共 **17,401 顶点、34,400 三角面**。包围盒上下各扩展 15 m 容纳起伏，依然无碰撞、无交互、无 Actor Tick，不跑 48 波谱或实时 FFT。近材质 4 次采样、远材质 1 次采样；远景过渡及地平线覆盖保持。

本轮使用 `produce_ocean_waves.py` 仅更新主场景已引用的海面网格、近远材质和两张正确二维法线，共保存 7 个资产；没有重写地图、云层、出生点或栏杆。后台 D3D12/SM6 编译与保存完成，回执为 `Receipts/ocean-waves-import.json`，生产日志为 `ocean-v3-wave-production-stdout.log`，修改前资产备份在 `trash/godspace-ocean-waves-20260927/Before/Content/`。未启动游戏、截图或性能采样；波动观感与实际帧率由用户确认。

### 下方云量加倍

用户要求在现有基础上再增加一倍下方云彩。仅调整 `MI_GodSpaceCloudSea`：`GodSpace_CoverageBias` 从 0.12 提至 0.24，`Cloud_GlobalDensity` 从 0.006 提至 0.012；完整导入脚本同步新值。覆盖偏置与消光密度同时增加，形成更密实的云海；这些参数不是线性覆盖率，不能据此声称可见面积精确翻倍。

保持现有单层体积云、素材、320 m 层厚、风动及天气驱动，采样倍率和细节噪声数量不变；不改海面、地图或新增云 Actor。增量保存脚本为 `Integration/increase_cloud_sea.py`，保存回执为 `Receipts/cloud-sea-double.json`，修改前材质备份于 `trash/godspace-cloud-double-20260927/Before/Content/`。原编辑器在接入期间退出后，改用同一互斥锁下的后台 commandlet 完成资产保存，不重新启动编辑器。未启动游戏或进行截图、性能测试；新参数在下次进入场景时读取。

### 海浪规则感与远景硬衔接调整

用户反馈水纹过于整齐、近水与远景贴图的分界明显。本次只更新四个近远海材质资源，保留现有 34,400 三角面的球面海壳、贴图库、云量加倍设置和正式地图。

原近景使用 SingleLayerWater，远景使用 DefaultLit；即使表面颜色、法线和粗糙度在边界相同，两套反射及合成路径仍不相同。本次纯视觉海面统一为 DefaultLit 受光表面，沿用水的低反射率参数、现有水面法线及白沫素材，取消该背景海面的 SingleLayerWater 专用渲染通道。没有改动可交互水体的 Clearwater 资产或注册表。

`OceanSwell.hlsl` 改为四个不等波长的涌浪带（883/593/421/347 m），方向、相位不同；`OceanNoise.hlsl` 提供连续的空间噪声与解析梯度，调制波组振幅并弯曲浪峰。波形高度及法线使用同一解析场；几何淡出梯度也纳入法线计算，位移在 2.2–3.8 km 内收掉，避免进入外围稀疏网格。叠加三组较弱的风浪法线，并按屏幕像素足迹衰减细波。

三层既有法线贴图采用不同旋转角度、非等宽周期、流速和连续 UV 扭曲，解码后的法线旋回世界坐标；两层细节的强度在波组之间变化。白沫贴图使用独立扭曲坐标，白沫按局部浪峰和强弱成短片分布，减轻连续白线与整齐瓦片感。

近远景共用宏观法线、深蓝色、反光与雾效路径；近景细节在约 1.8–12 km 的宽范围逐渐减少，并加入连续的空间变化，避免固定圆环式变化。至 12 km section 边界，两侧输出相同的法线、颜色和粗糙度。远景依然一次纹理采样，近景四次；新增的是有限的波形与噪声运算，没有新增纹理、网格、粒子、交互或 Actor Tick。实际帧率未采样，不能据此宣称性能提升。

完整生成入口 `import_distant_ocean.py` 已同步，新增 `refine_ocean_materials.py` 支持只重建材质、不重导网格或改写云资产。后台启动前发现编辑器已运行，因此改用现有 MCP 批次完成材质编译与四个资产保存。制作回执为 `Receipts/ocean-natural-materials.json` 和 `ocean-natural-mcp-20260927-a.json`；修改前材质及 SHA256 备份于 `trash/godspace-ocean-natural-20260927/Before/Content/`。没有启动游戏、截图或验收渲染，最终观感由用户测试。

### 积云云海与 80% 分布制作

用户确认采用现有素材重做单层云海，覆盖目标约 80%。本轮重建场景专用 `M_GodSpaceCloudSea` 与 `MI_GodSpaceCloudSea`，并保存正式地图的云层设置；共享天气材质、海洋材质、建筑和玩法未改。原先的覆盖偏置加倍方案由明确的分布阈值替代。

使用当前云库的 `T_CloudPattern` 与 `VT_PerlinWorley_Balanced`，没有生成或引入另一套云贴图。`author_cloud_distribution.py` 读取原有浮点分布图的 EXR 源，以 RGB 权重 0.55/0.30/0.15 在周期双线性重建上取第 20 百分位，得到阈值 **0.05561124**、边缘羽化宽度 **0.02940483**。这定义约 80% 的周期平面云区支撑，其余区域保持无云；80% 不是某个游戏视角中已实测的不透明像素占比，云边缘、视角和远处大气都会改变画面观感。原图尺寸为 1024×1024；编辑器读到的 32×32 是当时驻留尺寸，不用作源图制作分辨率。

云层位于平台下方 180–880 m 的空间范围内，厚度 700 m；实际云体在该范围内按分布图改变顶部与底部高度，加入大尺度三维隆起和有界边缘侵蚀，形成厚薄不同的云团。分布周期为 18 km。云滴本色保持接近白色，使用现有太阳、天空光和体积自阴影体现受光面与背光面；关闭本材质额外的地面反弹项，保留一阶多次散射及柔化的次级阴影。

`CloudSeaCoverage.hlsl` 先计算保守密度，将平面空洞和垂直范围之外的采样跳过，并把云顶/云底数据传给完整密度阶段。`CloudSeaDensity.hlsl` 内的条件采样使主视图每个有效采样点在近、中、远处分别最多进行 3/2/1 次纹理读取：细节噪声在 3–8 km 收掉，主体三维噪声在 14–28 km 收掉；次级阴影始终省略细节噪声。100–150 km 渐隐接入大气，避免 160 km 追踪范围末端形成硬切。仍只有一个 VolumetricCloud，保留原视图、反射和阴影采样倍率，没有新增粒子或运行时 Actor。

风位移和连续噪声时钟沿用 `StormCloudComponent`，天气状态沿用 `FPS_WeatherBlend`，雷电沿用现有天气 MPC 和发光连接。`configure_cloud_sea.py` 同时写入昼夜蓝图的真实配置结构与编辑器组件；完整布局导入、导出和放置入口也已同步，后续重建不会恢复旧偏置方案。

执行入口为 `produce_cloud_sea.py`，已通过当时运行编辑器的互斥桥完成材质编译、两个材质资产和正式地图保存。回执为 `Receipts/cloud-sea-authored.json`、`cloud-sea-map.json`、`cloud-sea-produce-mcp-20260927-a.json`。修改前地图与材质及 SHA256 备份于 `trash/godspace-cloud-sea-20260927/Before/Content/`。未自行启动游戏、截图、验收渲染或性能采样，最终观感由用户确认。

制作中曾强制使用 PNG 导出器读取浮点云图，触发 UE `SupportsTexture` 断言并导致当时编辑器退出；该读取步骤未写入场景资产。已修正为 EXR 扩展名并由 UE 自动选择兼容导出器，随后成功取得数据并完成制作；本任务未主动重启编辑器。

### 用户反馈棕色平面：修正体积云采样坐标

用户实际游戏截图显示下方为连续棕色平面，没有预期的云团或海面间隙，上一轮云海视觉目标未达成。针对反馈读取已保存的场景、材质与运行日志，确认新版云材质已经被游戏加载；随后从本机引擎实现定位到材质制作错误：`build_cloud_sea.py` 将 WorldPosition 设置为 `WPT_EXCLUDE_ALL_SHADER_OFFSETS`。`VolumetricCloudMaterialPixelCommon.ush` 的 `UpdateMaterialCloudParam` 会逐采样点更新 `AbsoluteWorldPosition`，但 `WorldPosition_NoOffsets` 的更新仍为 TODO；使用后者不能取得体积云射线采样位置，导致分布图与三维噪声的空间采样失效。

现已改为 `WPT_DEFAULT`，并通过 `fix_cloud_sea_position.py` 对已保存的 `M_GodSpaceCloudSea` 进行同一项增量修正。后台 D3D12/SM6 commandlet 完成重新编译及资产保存，回执为 `Integration/Receipts/cloud-position-fixed.json`。修改前资产及 SHA256 备份于 `trash/godspace-cloud-position-fix-20260927/Before/Content/`。本轮没有改写地图、海洋、80% 分布阈值或采样预算，也没有启动编辑器、游戏、截图或验收渲染；此次完成状态为坐标错误修复并落盘，实际云形与颜色尚待用户游戏内确认。

### 云海橙红染色：场景专用昼夜颜色补偿

用户继续反馈云层橙红，并授权按建议调整。对当时已运行世界的定向读取记录于 `Integration/Receipts/cloud-lighting-inputs.json`：云本色为 (0.98, 0.985, 0.99)，太阳白色、6500K，云散射亮度缩放为白色；首次读取太阳高度约 2°，随后随时钟上升。云层开启逐采样大气透射。引擎 `VolumetricCloud.usf` 在 SkyAtmosphere 存在时从大气远景光照表取得云的环境光，因此不能假定提高指定 HDR SkyLight 强度就能直接补亮体积云。低角度大气染色是有设置依据的来源，但未通过画面对照分离全部贡献。

本次将调整限定在 `M_GodSpaceCloudSea`，不修改太阳组件、全场景曝光或 SkyLight。`CloudSeaLightBalance.hlsl` 读取引擎已有的太阳方向、地面透射后照度与远景天空辐亮度，计算低太阳角度的暖色衰减。仅在光色偏暖、低角度且有足够日光时压低暖色通道；补偿强度为零、高太阳角度及夜间保留原散射本色。地面照度是该云层配色的近似依据，不是逐云点的精确光照反演。`GodSpace_CloudWarmNeutralization=0.82`、`GodSpace_CloudDiffuseFill=0.65` 是制作参数，不代表已实测去色百分比或最终画面亮度。

`CloudSeaAmbientFill.hlsl` 通过材质发光输入加入受限的冷白漫射补偿，复用当前消光和云层高度，空云无补光，深厚云体及底部补光更弱；亮度取自现有入射光，夜间无固定发光下限，阴雨进一步减弱。它是云材质的美术补偿，不是新增场景灯或真实额外散射计算。原有天气闪电输出继续相加保留。完整制作入口 `build_cloud_sea.py` 同步调用 `cloud_sea_lighting.py`，增量制作入口为 `produce_cloud_lighting.py`。

保持约 80% 的分布阈值、云体密度、形状噪声、风动、单层云及原有采样倍率。没有新增云纹理采样、灯光、Actor 或 Tick；新增成本为颜色运算及读取已有远景光照缓冲，未测 GPU 耗时。本轮不改海面或地图。修改前云主材质及 SHA256 备份于 `trash/godspace-cloud-lighting-20260927/Before/Content/`。本轮不启动编辑器、游戏、截图或验收渲染，观感由用户测试。

最终版本已通过后台 D3D12/SM6 commandlet 完成编译并保存主材质；执行时编辑器未运行。保存回执为 `Integration/Receipts/cloud-lighting-saved.json`，最终生产日志为 `cloud-lighting-final-stdout.log`，完成标记为 `GODSPACE_CLOUD_LIGHTING_SAVED`。该状态只表示制作资产已落盘，不表示运行画面或性能已经验收。

### 2026-09-28：按 GitHub 调研建议重做积云密度

用户授权继续后，已新建 `M_GodSpaceCloudSea_Cumulus`，将正式实例接到新材质，后台编译并保存主场景云层参数。此次采用 Takram 的高度整形与有界侵蚀思路，复用现有天气图和体积噪声；噪声派生为线性、带 mip 的独立资源。远处保留三维主体、逐渐收掉细节；撤掉上节的补色与漫射发光分支，仅保留共享雷电发光。主神空间视图采样倍率由 0.7 提至 3.0，阴影由 0.35 提至 0.5；更高采样有额外成本，未测帧率。

约 80% 仍是布局目标，未宣称实际画面覆盖率达标。最终材质编译错误为空，已保存 3 个材质/纹理资产和主场景；无游戏、预览或验收测试。实现、来源、备份与制作回执详见 [积云重制记录](cloud-cumulus-implementation-20260928.md)。本节取代旧版云形及补色方案，旧记录作为历史保留。
