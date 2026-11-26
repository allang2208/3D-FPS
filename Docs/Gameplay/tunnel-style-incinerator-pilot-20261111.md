# 处理线（焚化区）按 UndergroundTunnel 设计语义改造：试点

2026-11-11。用户要求以 `/Game/UndergroundTunnel/Maps/Demonstration` 为参考，全面提升随机地牢废弃设施的材质、做旧、细节和氛围，做旧与地面材质要符合参考的设计语义；先以焚化区试点。本批覆盖处理线的三间固定主题房：破损支护室（ShoredBreach）→ 焚化处理厅（AbandonedIncineratorHall，含 B1 停尸区）→ 烟气净化站（AbandonedFlueGasStation）。其他主题未改动。

## 与前几轮的区别

11-08～11-10 的几轮做法是"稀疏扫描贴花 + 换材质 + 摆件"，11-10 用同一参考包替换栏杆/灯具/管线后被用户否定并回滚。本批先从参考地图读取实际数据（2286 个静态网格组件、36 组植被实例、34 个贴花、66 盏灯、40 个 Niagara、2 个后处理体积、母材质节点图与顶点色），按参考的分层做法复现，而不是换贴图或凭截图印象。读取结果在 `SourceAssets/TunnelStyleIncinerator20261111/Reference/`。

## 参考场景的设计语义（数据读取结论）

| 层 | 参考做法 | 证据 |
| --- | --- | --- |
| 地面主体 | `MI_Env_2ly_ConcreteFloor01a`：A 层 Floor01a ×0.6、B 层破损混凝土 Floor02d，HeightLerp 对比度 25；**顶点 R** 控制 B 层，**顶点 A** 控制湿润 | 节点图 `graphs2.json`：`OneMinus(VertexColor.R)`→Transition Phase，`OneMinus(VertexColor.A)`→湿润 |
| 地面涂绘 | 逐实例涂绘：隧道壳体约 35–40% 顶点为部分 B 层、约 5% 全 B；湿润只占少量 | T3D 导出中 175 个组件带 `ColorVertexData` |
| 墙与砖墙 | 混凝土墙 `M_Env_Basic` + 两层细节法线（尺度 4–8）；砖墙为砖 / 抹灰两层，抹灰残片按 R 涂 | `MI_Env_ConcreteWall01b`、`MI_Env_BrickWall01a` 参数 |
| 交接边 | 每条墙脚和墙顶交线都有 10 cm + 10 cm 的 L 形网格贴花条，`T_ConcreteEdge01a` 的 V 0.774–0.855 带；顶点 A 在交线处 1.0、1 cm 处 0.9、10 cm 处 0 | `SM_Tunnel02a/04a` 的第 4 材质槽几何与顶点色 |
| 地表碎屑 | 约 2800 件网格贴花碎屑（金属碎片 21 种、混凝土碎块 8 种、纸箱垃圾 7 种），POM 视差，沿墙脚和角落密 | InstancedFoliageActor 36 组 |
| 碎石堆 | 46 处 PDO 视差碎石堆，墙脚 / 墙角，Z 向拉伸 1–3 倍 | `SM_DebrisPile01a–03a` |
| 污渍 | 金属件下方锈迹流痕；地面用 `MI_Decal_Debris01a`（Floor02d 投影）破损斑块，0.4–1.0 倍 256 盒 | 贴花与网格贴花统计 |
| 道具 | 小组团靠墙：油桶、托盘（斜靠）、散落木板（约 80 块）、空心砖（有翻倒）、油漆桶、液化罐、工具箱 | 道具网格与旋转统计 |
| 灯光 | 2500K 钨丝笼灯，300–650 lm，半径 3–6 m，体积散射 4–6，部分挂 `M_LF_Flicker` | 灯光组件读取 |
| 大气 | 体积雾 6000 cm、偏蓝内散射；21 组雾片、18 组浮尘；后处理 LUT、饱和度 0.59、暗角 0.53 | 雾、Niagara、后处理读取 |

参考的雨水遮挡 RT（`MF_RainOcclusionMask`）在室内没有捕获时读到的 R 为 0，因此不会出现整片湿地；湿润完全由顶点 A 决定。

## 焚化区的对应做法

材质实例全部以参考包的母材质为父级，从参考 MI 复制参数，参考包本身没有修改或保存。

- **地面**：三间房的地面、净化站铺装与 B1 混凝土地面换成 `MI_TS_Floor_Concrete2L`（参考 MI 原参数）。地面复制网格按 35 cm 边长重新剖分（折边保留），烘焙顶点色：R 来自墙脚距离、角落封闭度、多尺度噪声，以及灰渣源附近（炉门、接灰斗、投料槽、料斗、集尘桶）的加重；主通道略干净；A 只在排水沟、湿式洗涤器、洗池附近和少量角落积水斑。B 层（d>0.5）覆盖约 17–30%，湿润 0–2%。
- **墙 / 柱 / 顶棚**：混凝土墙用 `ConcreteWall01b` 参数，柱用 `ConcreteWall01a`，设备基座用 `ConcreteWall06a`；按参考 250 cm/UV 的纹素密度重做投影 UV。顶棚同材质，底色压到 0.72（焚化区的烟熏）。炉体砌体改为砖 / 抹灰两层，顶点 R 涂抹灰残片。
- **交接边条**：按参考截面和顶点 A 曲线生成墙脚与墙顶边条，共约 540 m 墙脚 + 316 段顶部交线，避开 ShoredBreach 两个侧门插槽。
- **碎屑层**：2360 件参考网格贴花碎屑（静态实例、无碰撞、无投影、26 m 剔除）；三房配比不同（支护室混凝土碎块多，焚化厅纸箱垃圾多，净化站金属碎片多）。
- **碎石堆**：37 处，墙脚 / 墙角，避开通行区、门口、刷怪锚点、容器和保留区。
- **贴花**：32 处地面破损斑块；10 处锈迹流痕（金属件与墙面接触点下方）；3 处炉口烟熏（参考 `M_Decal_Basic`，`T_Blend_Leaks01a` 侵蚀，向上拉伸，墨黑色）。该母材质的 Mask 用 Masks 采样器，参考包的高斯球是 Grayscale 压缩，会导致采样器不匹配，所以另做了一张原创的烟柱遮罩 `T_TS_SootPlumeMask`（TC_Masks，512）。
- **道具**：62 件，17 个靠墙组团（修炉空心砖、燃料桶、液化罐、斜靠托盘、木板、油漆桶 / 油瓶、工具箱），桶 / 罐 / 托盘有碰撞，其余可跨过。
- **灯光**：31 盏既有灯改为钨丝色温（暖灯约 2600K，冷灯改为约 3400K），体积散射 key 2.5 / path 1.6，光源半径 2 cm；焚化厅和净化站各一盏 path 灯挂参考 `M_LF_Flicker`（支护室只有 key/fill 灯，未加闪烁）。灯的位置、亮度、半径和调度不变。
- **大气与调色**：每间房增加房间尺度的低浓度偏蓝体积雾（焚化厅上下层各一），沿用现有雾池（最多 4 个）；焚化厅两个房间后处理饱和度乘 0.8、暗角 0.5。

## 落盘与重建

- 资产：`/Game/Dungeons/TunnelStyleIncinerator20261111`（10 个材质实例、1 张烟柱遮罩贴图、18 个壳体复制网格、3 个边条网格）。原壳体网格保留，用于回滚。
- 生产地图 `/Game/GameMaps/L_Dungeon_Randomized` 与 `DungeonFacilityFlow20261007/Config/catalog.json` 已保存，回执 `Receipts/install.json` 为 `map_saved`；生成器新增 88 个硬引用。备份在 `Backups/20261111-231404/`。
- 重建：`extend_catalog.py` 在 FloorReview 之后调用本层 `recipe.py`；从最早作者源全链重建与保存目录完全一致。`recipe.revert()` 可只撤销本层，离线往返校验一致。
- 制作源：`Scripts/plan_*.py`（外部 numpy 规划：地面遮罩、边条、碎屑、碎石堆、污渍、道具）、`Scripts/build_assets.py`（UE 资产）、`Scripts/prepare_install.py`、`install.py`、`run_background.ps1`。遮罩预览图在 `Plan/*_preview.png`。

## 尚缺素材（Fab / Quixel）

参考包没有焚化专用的灰烬和烟熏素材，目前烟熏用参考的侵蚀贴花代替。建议在 Fab 库添加以下免费 Quixel 素材（加入库或下载到 `D:/FPS3D/VaultCache/FabLibrary` 后即可接入）：

| 用途 | Fab listing |
| --- | --- |
| 炉前 / 接灰区灰堆贴花 | [Ash Pile](https://www.fab.com/listings/1b831362-8f0a-4359-b655-b5c1f889d66c)、[Ash Pile](https://www.fab.com/listings/2d4d3427-6fbc-45d2-8ec5-67c4f393597f) |
| 地面散灰 | [Ash](https://www.fab.com/listings/c8978e52-72ff-43ff-8315-be9529979784)、[Ash and Charcoal Pile](https://www.fab.com/listings/74f01085-bca4-44de-a030-ebc0eba44fac)、[Charcoal Scatter](https://www.fab.com/listings/6f27bd7a-6ce5-46ad-a25d-6f960fb5443e) |
| 炉口砖面烧蚀 | [Charred Bricks](https://www.fab.com/listings/cd1c98ff-bf8a-469a-a474-58a8223178ce)、[Burnt Wall](https://www.fab.com/listings/6f34eae3-93a1-47ad-a5b0-c9d18ebc92e2) |
| 投料口残留 | [Burnt Paper](https://www.fab.com/listings/baa6e27c-307a-4919-a1d3-2a8ba35b647c) |
| 桶 / 推车下油渍 | [Oil Stain](https://www.fab.com/listings/b6fa708c-7912-4108-8123-75c64d08d640) |

## 未做与边界

- 没有启动编辑器窗口、PIE、游戏、截图或性能采样；观感、通行、刷怪和帧率由用户进入随机地牢检查。处理线每局都会出现（六个主题每局全部分配到三条路线）。
- 2026-11-12 按用户要求用 `Scripts/build_subject.py` 把焚化线测试图 `/Game/GameMaps/Design/L_Incinerator_Theme_Subject` 换成当前正式配置（含本层）：同一 `open` 命令进入。只移除旧建图脚本生成的 234 个 Actor，重新放入 286 个网格 Actor、115 组实例（2370 件）、35 盏灯、96 处贴花、3 组血迹、2 个房间后处理、15 个大气点（4 个雾体积按满浓度静态摆放）及生产地牢的体积雾通道。旧图备份在 `Backups/Subject-*`，回执 `Receipts/subject.json`。测试图不刷怪、不封门，大气不走距离池。
- 参考的 LUT、中间调色偏和胶片颗粒需要扩展 `WardRoomAssembly.cpp` 的 `post_process` 字段，本批未改 C++。
- 新地面网格为非 Nanite（参考母材质没有 Nanite 用途标志，不修改参考包），三房地面共约 18 万三角面。

## 2026-11-12 墙面与地面修订

用户实测反馈：参考隧道的喷浆混凝土墙和两层脏污地面放在设施里像破损洞穴和泥地，要求墙面、地面改成和连接通道一致的设施墙面与工业地坪，其余保持。

- 三间房的墙体（含支护室两个侧门插槽的墙体变体）、柱子、地面、净化站铺装和 B1 混凝土地面换回原网格，材质统一为通道（Transit / Threshold）使用的 `MI_Architecture_Service_Dry`：墙面为设施抹灰，地面为工业混凝土地坪。B1 停尸区的医用地面槽不变。
- 同日追加：顶棚（支护室顶棚、焚化厅屋面、净化站屋面与屋面肋）也换回原网格和原材质 `MI_Concrete_Ceiling`，与通道顶棚一致。`n- 炉体砖砌、设备基座、墙脚 / 墙顶边条、碎屑、碎石堆、贴花、道具、灯光、雾和调色保持本批内容。
- 本层按同一修订号替换旧内容（先 `revert()` 再 `apply()`），原 `install-plan` 另存为 `Config/install-plan-20261111-tunnel-surfaces.json`；重绘的地面复制网格不再被引用，资产保留。

## 2026-11-12 素材添加清单

用于下一轮写实提升，全部是 Quixel Megascans，2026-11-12 在 Fab 查询时标价为 0。下载到本地 Fab 库（`D:/FPS3D/VaultCache/FabLibrary`，High 质量）后由制作脚本接入。已有的 Leakage、Damaged Concrete、Concrete Rubble 与 UndergroundTunnel 包不需要重复下载。

| 优先级 | 用途 | 素材 |
| --- | --- | --- |
| 必需 | 炉前、接灰区灰堆 | Ash Pile 贴花 1b831362-8f0a-4359-b655-b5c1f889d66c、2d4d3427-6fbc-45d2-8ec5-67c4f393597f |
| 必需 | 地面散灰 | Ash 贴花 c8978e52-72ff-43ff-8315-be9529979784；Ash and Charcoal Pile 74f01085-bca4-44de-a030-ebc0eba44fac；Charcoal Scatter 6f27bd7a-6ce5-46ad-a25d-6f960fb5443e |
| 必需 | 炉口烧蚀砖面、熏黑墙 | Charred Bricks 材质 cd1c98ff-bf8a-469a-a474-58a8223178ce；Burnt Wall 材质 6f34eae3-93a1-47ad-a5b0-c9d18ebc92e2 |
| 必需 | 投料口纸灰 | Burnt Paper 贴花 baa6e27c-307a-4919-a1d3-2a8ba35b647c |
| 必需 | 桶、推车、风机下油渍 | Oil Stain 贴花 b6fa708c-7912-4108-8123-75c64d08d640、8db4e28d-197e-4c65-8d18-03ca346920e3 |
| 推荐 | 地坪裂缝 | Large Concrete Crack 贴花 cf013e62-aec5-47cd-a224-ce5fd7bd9dcc；Industrial Decal Concrete Crack 01 3c36623d-b765-4e40-bff9-b23e3909359f；Industrial Decal Concrete Crack 13 33b85665-d805-403f-bc77-2f517c4c0a89 |
| 推荐 | 地坪剥落坑 | Concrete Damage 贴花 28e3f016-5d6f-45e4-986c-ac3218157aa6、45c982ce-54e4-4748-8be0-da4991a183d6 |
| 推荐 | 墙面掉漆 | Flaked Paint Wall 材质 1524e0fe-6010-4645-a97c-9256dcda7d57；Cracked Painted Plaster 材质 d91bfe39-edeb-420e-98cf-3533be8e8452 |
| 可选 | 墙脚返潮、泥水溅痕 | Mud Stain 贴花 0c20290d-5a14-4003-aaec-eba1704a4f01 |
| 可选 | 积灰地面脚印 | Footprints on Concrete 材质 7885bf43-7183-445a-93b9-ab440d8bbb96 |
| 可选 | 档案区、B1 散落纸张 | Urban Trash Bag Paper Crumpled 01 d4552a83-9f78-4ccf-a1b4-29a51ba47cff；Urban Office Equipment File Paper Stacked 01 23db3419-0e66-4c7c-8681-6976fe827b6d |

页面地址为 `https://www.fab.com/listings/<编号>`。

## 2026-11-12 Fab 自动下载与导入

用户授权用专用 Edge 配置（`D:/FPS3D/FabBrowserProfile`，用户本人登录）自动处理上表免费 Quixel 素材：`Scripts/fab_fetch.py` 只在页面确认免费且卖家为 Quixel Megascans 时点"添加到我的库"并下载，拒绝点击含购买、结账、购物车字样的按钮；每一步记录在 `Receipts/fab-actions.jsonl`。21 个素材全部加入库并下载到 `D:/FPS3D/VaultCache/FabLibrary`（贴花取 glTF 高质量或原始档，表面取纹理集，模型取 FBX/原始档）；首次试跑误下的 Ash Pile EXR 附加包已删除。

`Scripts/import_quixel.py` 导入到 `/Game/Dungeons/TunnelStyleIncinerator20261111/Quixel`：14 个 Substrate 延迟贴花、5 个表面材质、2 个 Nanite 模型（纸张，35.5 cm 与 14.6 cm，与扫描尺寸一致），共 120 个资产，回执 `Receipts/quixel-import.json`。所有下载的法线贴图经高度图梯度相关性判定为 OpenGL，导入时统一翻转绿通道；运行时最大 2048。本步只导入资产，没有改场景。

撤销自动化授权：在该配置里退出 Fab 登录，或删除 `D:/FPS3D/FabBrowserProfile`。

## 2026-11-12 第二轮写实（Quixel 素材与有来源的损耗）

规划 `Scripts/plan_round2.py`，资产 `Scripts/build_round2.py` / `build_emergency.py`，结果 `Plan/round2.json`、`Receipts/round2-assets.json`；仍是同一层（先 revert 再 apply），正式地图与测试图均已保存，全链重建一致。

- 灰与炭：炉门前、接灰斗、投料槽、料斗、集尘桶、推车周围 17 处灰堆 / 炭渣、10 处散灰；医疗废物料斗与推车旁 2 处纸灰。
- 油渍：燃料桶、液化罐、工具箱组团、推车、风机机座下 13 处。
- 地坪：15 处裂缝、8 处剥落坑（只在空地坪上）。
- 墙面（设施抹灰）：13 处顶部渗水流痕（沿用项目 Quixel Leakage 实例）、12 段墙脚返潮带（参考 `M_Decal_Basic` + 原创潮痕遮罩）、10 处掉漆 / 裂纹涂料（新建 `M_TS_SurfaceDecal`，Quixel 表面贴图按扫描尺寸放进贴花）。
- 炉口烟熏改用 Quixel Burnt Wall 贴图的贴花；炉体砌体 A 层换成 Quixel Charred Bricks（仍是参考两层母材质与抹灰残片顶点色，UV 改为 100 cm 对应 1 m 扫描）。
- 灯：焚化厅 B1 一盏服务区灯熄灭（灯管换成不发光玻璃）、冷柜区一盏降到 35% 并频闪；三间房出口门楣各加一盏红色应急灯（参考 `SM_Light01a` 笼灯 + 红色发光实例，频闪，无投影）。楼梯灯与唯一照明灯不参与熄灭。

修正：`prepare_install.py` 以前从已应用本层的目录生成计划，重装时调色和灯色会叠加（焚化厅饱和度被叠成 0.43 / 0.47，冷灯也被归成暖灯）。现在先撤销本层再生成，饱和度恢复为设计值 0.66 / 0.74，冷暖灯区分恢复。

## 2026-11-12 第三轮：去掉炉口烧蚀贴图，补细节

用户反馈炉口新加的黑色烧蚀墙面效果不好，已去掉 3 处炉口烟熏贴花（`prepare_install.py` 的 `SOOT_ENABLED = False`），炉体其他部分不变。

细节补充（`Scripts/build_round3.py`、`plan_round3.py`、`Plan/round3.json`）：
- 设备顶面积灰：Quixel Ash 派生的浅色薄灰贴花 `MI_TS_Decal_TopDust`，每间房按顶面大小取最大的 20 个（焚化厅 20、净化站 18，支护室没有设备），只向下投影 6 cm，不涂到地面。
- 纸张：医疗废物料斗、推车、记录桌、档案柜、控制柜周围 15 团 Quixel 揉皱纸，B1 记录桌桌面 2 叠文件。
- 蛛网：层高 5 m 以内的天花阴角放 14 张（支护室 5、焚化厅 B1 5、净化站 4），避开门口。

2026-11-12 追加：用户截图指出炉体正面的 Quixel 烧黑砖看起来像烧糊的一片，已撤回（`prepare_install.py` 的 `CHARRED_MASONRY = False`）。炉体砌体恢复为参考砖墙 / 抹灰两层材质，复制网格按 250 cm 对应一个贴图周期重做 UV（`Scripts/build_round3b.py`），与第二轮之前一致。正式地图、测试图已保存，全链重建一致。烧黑砖相关资产保留未用。

## 2026-11-12 第四轮：灰调暗、炉门与标牌做旧

`Scripts/build_round4.py`（资产）、`plan_round4.py`（`Plan/round4.json`），全部用参考 `M_Decal_Basic`（遮罩被 `T_Blend_Leaks01a` 侵蚀）或参考锈迹材质，不改设备与标牌的共享材质。

- 灰：21 处灰堆 / 散灰 / 炭渣改用偏灰、80% 不透明的派生实例，避免暗光下像白漆。
- 炉门（3 座）：门叶外缘一圈青铜色受热回火痕（不是黑色）；铰链（x≈-110）与锁扣（x≈+90）下方各 5 道锈流；手轮一处磨亮的浅色低粗糙度金属。位置取自炉门模型：门叶平面 y=-5、x -111..111、z 32..297，手轮中心约 (0, 165)。
- 标牌：从标牌模型的连通部件识别 43 块牌面（焚化厅 27、净化站 16），每块加一层灰膜和自上而下的流痕，投影深度只覆盖牌面厚度。牌子歪斜、缺角需要改模型，本轮没做。

正式地图与测试图已保存，全链重建一致。

## 2026-11-12 第五轮：积水、松脱线缆、整体调色

- 积水：参考 `M_Decal_Basic` 派生 `MI_TS_Decal_Puddle1/2`（近黑、粗糙度 0.03，原创不规则水坑遮罩），按地面湿区遮罩放 8 处（净化站 5、焚化厅 2、支护室 1）。
- 线缆：每间房一个原创管状网格 `Cables/SM_TS_<房间>_LooseCables`（橡胶材质，无碰撞），墙上松脱下垂的跨线 2 段 + 垂到地面并拖地的 1 根 + 断头悬垂 1 根（焚化厅上下层各一组）。
- 调色：`WardRoomAssembly.cpp` 的 `post_process` 改为全部字段可选，并新增 `color_grading_lut`、`color_grading_intensity`、`saturation_midtones`、`offset_shadows`、`film_grain`、`local_exposure_shadow_contrast`；旧配置行为不变。焚化厅两个房间后处理加参考 `T_LUT_Grading`（强度 0.6）、中间调偏冷去饱和、暗部轻微抬升、胶片颗粒 0.18；支护室与净化站加只调色、不锁曝光的房间体积（`GRADE_ROOM_VOLUMES`，需新二进制）。
- 构建：Game 目标已成功（`Receipts/build-game-grade.log`）；Editor 目标编译通过但链接时 DLL 被打开的编辑器占用（LNK1104）。测试图建图脚本直接写后处理设置，不依赖该 DLL。
- 落盘：用户当时在 PIE 中，安装脚本按规则拒绝改地图。`finish_pending.ps1` 在后台等待编辑器关闭后依次：链接 Editor、启用房间调色体积、安装到正式地图、重建测试图、校验全链，进度写在 `Receipts/finish-pending.json`。