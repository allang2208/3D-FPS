# R37　林道村庄的联机与帧耗复查

复查对象为 `/Game/GameMaps/L_ForestPathVillage`。地图沿用 R31 的丘陵与道路双主题、R35 露岩和 R36 坡脚碎石。这次修改了运行时代码、联机兼容标识、导航几何和后台检查入口。编辑器目标 `FPSGAMEEditor Win64 Development` 已编译。[构建日志](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestAudit-R37/release.txt)

## 地形和生态

- 原片章节、独立样板、道路真实残差、B full 路面、村内黄土、草被替换、落叶边缘以及水坑选址均有独立制作记录和恢复版本。检查时在正式 Content 复查了 R27 退役的宽叶网格与专用材质，两包均已移除。R20 素材清单记录 35 个花岗岩扫描、山毛榉与黑杨各四个可采伐变体；装饰鹅耳枥和榛灌木有各自的 PCG 生成路径。[历次制作记录](../Production/HillsForestPathStudy.md) · [两主题与组件](hills-landscape-themes.md)
- 正式图运行读回 12 处水坑、12 个局部雾组件、326 个细碎石、146 个较大断片。M 键打开了带村庄和道路的地形图。[运行读回](F:/FPSGAMEData/ArtReviews/HillsForestPath/ForestAudit-R37/Profile/review.json) · [M 键实际画面](F:/FPSGAMEData/trash/ForestLandscapeCloseout-20261126/Reviews/ForestAudit-R37/Profile/world-map.png)
- 旧档 A、B 两槽的副本均为 18 级、302077 灵魂、174 条物品记录。用控制台从丘陵切到主场景，再带 `HillsContinue` 返回，三个阶段读回的档案数值一致。丘陵两次启动记录的种子和世界 ID 相同。这一项覆盖换图和恢复逻辑，未操作场景里的传送门交互。[档案原值](F:/FPSGAMEData/ArtReviews/HillsForestPath/ForestAudit-R37/Profile/profile-readback.json) · [往返读回](F:/FPSGAMEData/ArtReviews/HillsForestPath/ForestAudit-R37/Profile/Travel/travel.json) · [世界 ID 日志](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestAudit-R37/profile/travel.log)
- R34 有落叶边缘同机位对照，R35 有路堑、主山对照及高度采样。R37 没有逐角度复拍所有季候、远坡、独立样板的布光或所有村庄任务，数量读回不能代替这些项目的观感验收。[落叶边缘](../Production/HillsForestPathStudy.md#road-leaf-edges-r34) · [陡坡露岩](../Production/HillsForestPathStudy.md#cliff-exposure-r35)

## 联机修复

- 将正式森林地图、林道副本、采石场、生态和地形数据等加入联机内容签名，同名地图使用不同生成数据时可在入场前拒绝连接。[签名输入](../../Source/FPSGAME/FPSGAME.Build.cs)
- 监听服按本地观察者生成树冠，为远端玩家单独分配权威树干碰撞。客机离房主约 315.6 米时，服务端可以命中客机旁的树干，客机砍伐通过既有库存操作入口，移除、幼树和成熟状态同步。[树木表现与碰撞](../../Source/FPSGAME/Production/ProductionTreeGrowthPresentation.cpp) · [采伐权威](../../Source/FPSGAME/Multiplayer/ColdSteelHarvestAuthority.cpp)
- 正式林图独立复制树龄时钟，批量资源快照比较排除纯时钟变化和种植快照序号变化。实际传输仍保留种植序号以维持接收顺序。重连续接同一档案与世界，按服务器的模拟生长时间观察幼苗及成熟状态。[世界状态传输](../../Source/FPSGAME/Multiplayer/ColdSteelWorldNetwork.cpp) · [地形与时钟](../../Source/FPSGAME/WorldGeneration/TemperateHillsWorld.cpp)
- 发布构建 F 轮共 22 项通过，包含版本错配、三个区域地面与布置摘要、双端碰撞、采石场传送、移动、时间与雨、远端树干、客机砍树、重连及加速再生。主客机正常退出，源世界存档哈希保持一致。同机独立进程走 UDP，注入 60 ms 包延迟与 2% 丢包。范围为监听服和一名客机，真实外网、多客机同屏、打包版与专服承载尚未测量。[F 轮逐项结果](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestAudit-R37/net/F/Evidence/result.json) · [构建哈希和退出回执](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestAudit-R37/net/F/summary.json) · [隔离测试入口](../../Tools/WorldGeneration/Run-HillsSceneryNetwork.ps1)
- 主机日志里，调整快照比较前的 D 轮记录 60 次入队、5 次跳过，修正后的 F 轮记录 8 次入队、58 次跳过。该数字用于观察重复发送，未测量整场网络带宽。E 轮受 Windows 提交内存耗尽中断；F 轮限制后台无渲染测试进程的 CPU 与纹理派生并发后完成。[D 轮日志](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestAudit-R37/net/D/host.log) · [F 轮日志](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestAudit-R37/net/F/host.log)
- 22 项回执对应快照 DLL 的 SHA-256 前缀 `F456927F`。正式目录随后于 19:53 写入另一构建，散列前缀 `F281E9FA`；交付时复查了本批登记的源码，内容与归档一致。后一二进制未重跑联机套件。[版本与源码清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestAudit-R37/published.json)

## 导航

教堂地基用原结构尺寸导出 37 个简化导航盒，神像按石座占地加入导航障碍，保留玩家实际物理碰撞。两处高模导航导出警告在修复后的采样中消失。七种导航体均通过绕神像八条路线。五种通过入口台阶取样，M10Mawcrawler 和 SpiralPillarM14 未通过；这两种配置半径为 225 和 125 厘米。此次没有改变门洞和大型怪物通行设计。[导航代理](../Publication/HillsForestLandscape20261126/Implementation/Source/FPSGAME/WorldGeneration/ChapelNavigationGeometry.cpp) · [现场寻路数据](F:/FPSGAMEData/ArtReviews/HillsForestPath/ForestAudit-R37/Profile/review.json)

## 性能测量

RTX 3080 Ti 12 GB，DX12，1600 × 900 输出，视距、效果及阴影档位 3，启用光追，无垂直同步或帧率上限。独立有图形运行采用晴天 10:45，每个固定机位预热 12 秒并记录 240 帧。列出的帧耗为总帧时间中位数及 P95，单位为毫秒。

- 村内 **15.44 / 16.54**，GPU 中位 14.12，阴影深度中位 2.16。
- 路堑 **15.21 / 16.36**，GPU 中位 13.98，阴影深度中位 4.60。
- 林坡 **17.23 / 18.48**，GPU 中位 15.96，阴影深度中位 4.67。该机位中位帧耗仍超出 60 FPS 对应的 16.67 ms。

三处显存中位用量约 9120–9449 MiB，本地预算约 10983 MiB。截图中的编辑器显存报警仍需按对应 PIE 负载复现。缩短树灌风动距离的试验没有稳定收益，已撤回。以上数据仅对应这三个机位，不含联机渲染负载，也没有测量低显存硬件。后续若继续降低林坡耗时，先同机位比较阴影深度、草叶覆盖与树冠遮挡各自的耗时。[测量设置](F:/FPSGAMEData/ArtReviews/HillsForestPath/ForestAudit-R37/Release/settings.json) · [逐项统计](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestAudit-R37/Release-stats.json) · [原始 CSV](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestAudit-R37/perf/User/Saved/Profiling/CSV)

<a id="forest-delivery-r47"></a>

## R47 正式林图复核

- 两个主题的 13 张生态子图及其制作入口可用。R43 灌木 17 包、R45 路面 9 包和 R46 材质与回退网格 13 包与发布回执逐包一致。R41 退役的十个带土木料模型均已移除。R42 面包房阁楼灯在当前运行关卡中仍关闭投影。[主题与退役清单](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestDeliveryAudit-R47/theme-audit.json) · [正式包核对](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestDeliveryAudit-R47/assets.json)
- R47 把此前遗漏的村外路面函数及 GateRoad 目录加入构建期联机内容签名。正式林图的植被资源请求结束后，可用的村内植被继续分批布置；可选空槽不再阻断整片生成。碰撞复查要求实际射线命中，Landscape 高度查询结果单独不能通过。联机用例将原档哈希一致纳入总通过条件。[制作与恢复回执](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestDeliveryAudit-R47/published.json)
- 三轮均为本机独立监听服与一名客机，60 ms 模拟包延迟、2% 丢包。每轮 22 项通过，包含刻意错配版本被拒、三个区域的地面和布置摘要、采石场、时钟和雨、远端树干碰撞、砍伐、强制断线、同档重连及再生。三轮原世界存档哈希一致。控制台路面 A/B 属于本地外观预览。丘陵在专用服务器的 BeginPlay 中明确拒绝初始化；多人并发压力和公网仍未覆盖。[首轮实测](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestDeliveryAudit-R47/net/A/summary.json) · [后续模块逐项结果](F:/FPSGAMEData/ArtProduction/HillsForestPath/ForestDeliveryAudit-R47/net/Final/Evidence/result.json)
- DX12、1600 × 900 输出、晴天、视距和阴影档位 3，三个固定机位每个条件记录 240 帧。正式阴影设置的两轮中位帧耗均值为村内 17.62、路堑 18.68、林坡 20.08 ms。对 22,386 株榛灌木临时改变阴影缓存失效策略，路堑和林坡阴影阶段分别减少约 0.26、0.23 ms，村内无稳定收益；正式图保留原动态阴影。初次快速加载的进程累计记录到 100 次 PSO 创建卡顿。已校正预载纹理清单与预算估算，按当前材质质量和实际请求的非可选 mip 计量。完整预载仍未放行。在本机该次实测中，高清纹理需要 5,904 MiB，预算为 3,894 MiB。地图就绪、可通过脚本移动相机，并不等于加载界面已释放玩家输入。上述采样独立于玩家此前的编辑器 F6。[机位数据、帧耗与显存余量](F:/FPSGAMEData/ArtReviews/HillsForestPath/ForestDeliveryAudit-R47/performance.json) · [完整预载运行记录](F:/FPSGAMEData/ArtReviews/HillsForestPath/ForestDeliveryAudit-R47/CompleteReadyFinal/routing.json)
