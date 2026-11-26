# 丘陵城镇与城门的 F6 性能对照

11 月 25 日 20:18 的两份用户导出来自同一场 `L_ForestPathVillage` 编辑器试玩。城镇较慢，而且更容易出现超过 100 ms 的长帧。两处在各自窗口的 19 次有效采样里，本地显存用量始终高于当前预算。建议先处理植被贴图的流送，再做城镇局部灯阴影的单项对照。[城镇原始导出](F:/FPSGAMEData/ArtReviews/HillsForestPath/VillageGateF6-R40/performance-20261125-121809-D267A88C4DD1281162D9178234F4791A.json) · [城门原始导出](F:/FPSGAMEData/ArtReviews/HillsForestPath/VillageGateF6-R40/performance-20261125-121854-F05DE9A84B957A9D1A6E9D9191DD3E79.json)

## 两个机位

按用户描述将较早文件标为城镇、较晚文件标为城门。两次导出在上海时间 20:18:09 和 20:18:54 采集。视点世界坐标分别约为 (98.7, 350.1, −4.1) 米和 (4.3, 214.3, 12.2) 米，视线方向也有变化。两段均约 10 秒，使用 RTX 3080 Ti、D3D12、2552 × 1218 输出、107.5° FOV。F6 面板均打开，模糊强度 9、半径 21，无暂停帧或后台帧。屏幕百分比的控制台读数为 0，报告没有给出实际内部渲染比例。

- **城镇，242 帧。** 平均 24.17 FPS，总帧 P50／P95 为 39.70／52.05 ms，峰值 115.02 ms。21 帧达到 50 ms，其中 4 帧达到 100 ms。GPU／渲染线程／游戏线程中位数分别为 36.90／39.79／18.89 ms。本地显存超预算 1150–1589 MiB，中位数 1284 MiB。
- **城门，293 帧。** 平均 29.28 FPS，总帧 P50／P95 为 34.12／36.47 ms，峰值 73.57 ms。1 帧达到 50 ms，0 帧达到 100 ms。GPU／渲染线程／游戏线程中位数分别为 31.43／34.09／14.16 ms。本地显存超预算 846–1158 MiB，中位数 1004 MiB。

60 FPS 的总帧预算为 16.67 ms。渲染线程与 GPU 在两个窗口都远超这一预算；城镇的游戏线程本身也有压力。各线程计时独立发布，无法从峰值帧反推某个具体渲染阶段。两份报告的 GPU 资源清单其实都是两个窗口之前、第 3307 渲染帧采的一份基线。窗口内显存统计只用了落在各自窗口内的采样。两份导出均未请求 GPU 联合跟踪，暂无换页事件、VSM、Lumen 或雾的逐项耗时。[窗口统计与原件哈希](F:/FPSGAMEData/ArtReviews/HillsForestPath/VillageGateF6-R40/comparison.json)

## 建议的开发顺序

1. **先给春草颜色与透明遮罩做可流送的 mip 版本。** 两张原图都是 8192 × 8192，资产设置均为 `NoMipmaps`。F6 基线中分别分配约 64 和 32 MiB，均未标为可流送。低草和铺展草的父材质包都引用这三张春草扫描图，春草法线和榛树法线已有 mip、带流送标志。建议先在丘陵材质分支保留 8K 顶级，给颜色与独立遮罩生成一致的 mip，遮罩按实际采样通道保护覆盖率。重点看远坡能否连片、细叶是否变稀、近处是否闪烁。分别读回所需／驻留 mip 与显存；保留原 8K 顶级时，近景仍可能请求全分辨率，增加完整 mip 链也会增加满载大小。若远景稳定，再独立试法线顶级限制为 4K。两张原分配合计 96 MiB，单靠它们不足以填平持续约 1 GiB 的缺口；其他场景也引用这些原图，应用到共享资产前应检查其用途。[贴图设置与引用](F:/FPSGAMEData/ArtReviews/HillsForestPath/VillageGateF6-R40/texture-assets.json) · [Epic 纹理流送指标](https://dev.epicgames.com/documentation/en-us/unreal-engine/texture-streaming-metrics-in-unreal-engine)
2. **城镇优先试次要补光的阴影。** 城镇有 10 盏灯进入视锥和距离候选，其中 6 盏启用阴影，分别是太阳、面包房三盏点光与两盏店铺吊灯；城门只剩太阳。五盏局部灯位置不同。先选一盏次要补光，只切换动态阴影，保留发光外观、光强、室内主灯和太阳。对照门框接触阴影、墙体漏光以及相同视角的 ShadowDepths／VSM 时间。候选数支持把这项放在前列，仍需对照才能给出毫秒收益。[Epic 可移动灯光](https://dev.epicgames.com/documentation/unreal-engine/movable-light-mobility-in-unreal-engine?lang=en-US)
3. **毛发按屏幕尺寸降级，先确认当前角色在使用发丝。** 早期进程资源清单中有约 399 MiB 的临时 `Hair.VoxelPageTexture`，同时记录到 512 MiB 的 VSM 保留池与 528 MiB 的 Nanite 几何页缓冲。三个数属于不同用途和寿命，不能相加当成可释放的独占显存。本次没有逐角色 Groom 采样。若同机位分项确认毛发开销明显，优先让中远景 NPC 切已有卡片 LOD 或减发束，保留近景，侧光下对照发际线、轮廓和阴影。[Epic 毛发性能与 LOD](https://dev.epicgames.com/documentation/en-us/unreal-engine/groom-scalability-and-performance-with-unreal-engine)

城门记录的注册实例约 117.62 万，比城镇约 113.50 万更多，帧率反而较高。低草、铺展草和细枝在两处的高排名均为源几何估算。已有主要草组件关闭投影，本次没有对应像素着色、覆盖绘制或实际渲染 LOD 的计时。保留当前草密度、近景材质与林雾；面板本身每次构建快照约需 5–7 ms，复测时采用相同面板状态，避免混入观察开销或其他视点的差异。

## 木料与岩石复查

R39 在把两款旧细枝纳入贴地分支时，一并套用了新增松枝的 50 米剔除。R40 隔离版恢复其原 75–100 米淡出，新增松枝仍使用 37.5–50 米。正式参考点流烘焙不再逐件查询木料包围盒；道路单主题没有大岩石候选时保留槽号，跳过三款丘陵岩模的几何读取和排序。两项都发生在制作阶段。

隔离版编译、烘焙及包准备已完成。14 款木料共 269172 件，新增的 136 个浅色苔岩位置继续复用原石位。2699 个抽样木件的 12549 个底部区段中，超过地面 5 厘米的区段由正式基线 44 处降至 0 处；与 R39 比较，抽取的木料与岩石变换一致。此次用户 F6 导出早于 R39／R40 的正式地图写回，不能据此计算新版帧率收益。当时的 R40 为隔离候选；这些地编改动在 [R41 正式写回](hills-landscape-themes.md#soil-wood-r41)时合入。[逐素材复查](F:/FPSGAMEData/ArtReviews/HillsForestPath/VillageGateF6-R40/wood-and-rock-check.json) · [隔离包回执](F:/FPSGAMEData/ArtProduction/HillsForestPath/VillageGateF6-R40/prepared.json)

<a id="hills-f6-r42"></a>

## R42 正式接入

- **春草纹理流送。** 颜色与透明遮罩保持 8192 × 8192 顶级，构建后各含 14 级 mip，DX12 资源清单两行均标为可流送。制作前逐一沿五个直接使用者的材质图追到透明遮罩取样，五处均读红通道，裁剪值均为 0.3333。按这个值为遮罩保留覆盖率，在原共享包上修改，丘陵、河岸和使用同一套扫描的城市场景均可按需流送。空白编辑器场景里的驻留量不能当作正式丘陵的节省量。[生成配方](../../Tools/WorldGeneration/ForestVillage/author_spring_grass_mips.py) · [材质通道记录](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsF6Optimizations-R42/mask-readback.json) · [DX12 纹理清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsF6Optimizations-R42/mips.log)
- **面包房阁楼补光。** 在当前村庄关卡关闭带 `VillageBakery.Group.Light2` 标签的阁楼洗漱台点光源投影。它仍为 800 流明，炉膛和柜台吊灯继续投影。面包房制作脚本使用相同设置，重新布置时会保留这项选择。[面包房配方](../../Tools/WorldGeneration/VillageBakery/install_bakery.py) · [三盏灯前后读数](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsF6Optimizations-R42/light.json)
- **修女发髻。** 实际主 Groom 有 75,005 条曲线、4,950,330 个控制点，资源自带发丝 LOD，卡片列表为空。复用引擎的屏幕空间连续 LOD，在修女已有的本地视距更新中调整该实例的减束量。远离时在等效 9 米和 21 米进入中、远档，靠近时在 18 米和 7.5 米返回。中档和远档分别从原始连续 LOD 偏移再减 0.008 和 0.016，近处恢复原值。视距沿用最近本地视角、FOV 和瞄具规则。发型源、玩家角色、眉睫及修女原有散发模拟分别沿用各自设置。[修女运行时实现](../../Source/FPSGAME/NPC/ChapelNun.cpp) · [Groom 与灯光源数据](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsF6Optimizations-R42/inputs.json)

本批更新两个纹理包、一个村庄关卡和运行时代码，按 `FPSGAMEEditor Win64 Development` 构建。前述 24.17／29.28 FPS 属于 R42 之前的 F6。当前未采集 R42 同机位游戏帧耗或在试玩中复看阁楼漏光、远坡和发际线。[正式发布及恢复清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsF6Optimizations-R42/published.json) · [正式编辑器构建](F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsF6Optimizations-R42/build-release.txt)
