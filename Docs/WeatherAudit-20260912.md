# 天气、云层、光照与挂水效果审计

日期：2026-09-12。宿主：`D:/FPS3D/FPSGAME`，UE 5.8.2。

结论：保留天气调度与昼夜合同，优先补齐所有降雨状态的云光过渡、统一风场和遮雨过渡，再增加屏幕边缘水滴、武器表面水膜与水珠。Fab 整体表现方案首选评估 Ultra Dynamic Sky（已包含 Ultra Dynamic Weather）；低迁移成本方案是保留现有天空、重做云参数驱动并评估 Easy Rain。二者是候选路线，不需要同时采购。

本次为审计与方案：读取当前源码、配置、磁盘资源和官方资料；运行独立只读资产查询；实际查看 2026-09-10 留存的游戏截图。没有改动玩法、材质、地图、配置或用户存档，没有下载、购买、导入新资产，没有提交或推送。本文中的新效果和数值均为建议，尚未实现或完成本次运行画面验收。

## 1. 当前证据

当前已有 `AFPSWeatherManager`、`UStormCloudComponent`、`UWeatherSurfaceComponent`。默认地图 `/Game/GameMaps/DayNight_Lighting`，另外覆盖 Normandy 和 MilitaryTrench 测试地图。天气管理器采用 DeltaSeconds，默认一天 2160 秒；GameMode 已避免重复生成管理器。原有时钟连接关系需要保留。

现有四套 Niagara 为 `NS_FPS_RainFine`、`NS_FPS_SurfaceSplashes`、`NS_FPS_RainMist`、`NS_FPS_RoofDrips`。本次磁盘加载确认均只有一个 GPU 发射器；旧 Fountain 喷泉发射器不是本次需要重新解决的问题。

| 发现 | 当前源码/资源证据 | 对效果的影响 | 置信度 |
| --- | --- | --- | --- |
| 云层只为雷暴过渡 | `Source/FPSGAME/StormCloudComponent.cpp:85` 只有 `Storm` 的 Target 为 1；其他状态均为 0 | 小雨、中雨不会通过该组件获得相应积云与阴天过渡；MPC 云量变化并不等于云形变化 | 高 |
| 云的艺术控制有限 | 同文件 94–103 行主要插值云底、厚度、覆盖、密度和灰色；回退材质为引擎 SimpleVolumetricCloud | 缺少由同一天气风场驱动的多尺度平移、侵蚀和天气图变化，难形成自然演变的雨云；不据此声称原材质完全没有动画 | 高（结构）；视觉归因待动态复核 |
| 三图光照衰减不一致 | `FPSWeatherManager.cpp:441` 测试图直射雨天乘 0.35；云组件 125 行雷暴再乘 0.25 | 测试图雷暴直射乘积为 0.0875；主图与测试图不是同一曲线，容易出现突然压暗或色调脱节 | 高 |
| 雨丝变化不足 | 资产回读：Sprite Size=(3,65)、Gravity=(65,20,-2100)，寿命 1.4–1.8 秒；生成器移除了 WindForce 和 AerodynamicDrag | 统一雨丝轮廓与横向运动易显得机械。3×65 是 UE 厘米单位的软边精灵几何尺寸，不是实际水滴直径 | 高 |
| 飞溅为简化软圆片 | `Tools/Weather/build_rain_assets.py:47`；四套雨材质均没有外部贴图依赖 | 缺少水冠、二次细滴和随机形态；不是单纯增加粒子数量能解决 | 高 |
| 遮雨插值实际跳变 | `FPSWeatherManager.cpp:266–290` 每 0.25 秒探测，用 FInterpTo(...,0.25,8) | 插值系数被截为 1，每次检测直接到目标；门口粒子/声音会突然切换。单相机雨体还可能使室内观察窗外雨显得不足 | 高（插值）；窗外表现待复现 |
| 地面湿润不能代表枪械湿润 | `WeatherSurfaceComponent.cpp:87,119` 为局部贴花累计 Wetness；MPC 查询的内容资产引用为空 | 地面有水坑，枪身仍可保持干燥；不能将 MPC 写入视为全场景材质闭环 | 高；资产注册表不枚举 C++ 字符串引用 |
| 枪械挂水尚未接入 | 本次回读 M4、AKM、手臂及父材质；未见 Wet/Rain/Drop 参数或 Weather 依赖。`FPSGAMECharacter.cpp:93` 设置 `bReceivesDecals=false` | 应在武器材质里混合水膜/水珠。普通世界投射贴花不能直接完成现有第一人称枪身挂水 | 高 |
| 覆盖地图硬编码 | `StormCloudComponent.cpp:31` 只对三张指定地图启用 | 后续新地图需要显式接入，不能假定所有关卡自动有风雨云 | 高 |

渲染设置已经开启 DX12/SM6、Lumen、Virtual Shadow Maps、Mesh Distance Fields 和 Substrate。新资源应在这些现有设置下验证。

## 2. 本次执行与边界

只读脚本：`Saved/WeatherAudit20260912/inspect_assets_readonly.py`。

输出：`Saved/WeatherAudit20260912/assets-readonly.json`、`asset-audit.log`。查询得到 18 个材质/父材质条目、两个枪模的材质槽和四套 Niagara 的当前输入；脚本内部 errors=0。

UE 命令行进程退出码为 1：启动阶段报告项目没有为 GameFeatureData 配置 AssetManager 扫描规则。Python 查询成功并写出了 JSON；这次不能写成“命令行全通过”。该项与天气查询分开记录，本次不修改相邻项目配置。

已查看留存画面：`unreal/weather-migration/Preview/DayNight_Lighting-storm.png` 和 `L_Normandy_FPS_Test-rain.png`。前者可见云层大面积灰色连片、部分亮雨线；后者有雨但环境仍呈强暖色。它们拍摄于 9 月 10 日，只用于理解既有表现，不能代表 9 月 12 日重新实测，也不足以单独判定运动僵硬。

本次未运行新一轮 PIE、听音或性能 A/B；没有重用历史整场景 GPU 数据来承诺升级性能。运行中的用户编辑器保持原状。

## 3. 升级设计

### 第一阶段：修复天气表现链

为 Clear、Cloudy、LightRain、Rain、Storm 配置统一的表现预设，包括覆盖、云形侵蚀、风向/风速、雨量、光照与雾。依次表现云层聚拢、直射光变柔、风增强、开始降雨；雨停之后云层和表面水分分别退场。

天气调度继续归 `AFPSWeatherManager`，保留原有时钟接口。选择第三方天空时，通过适配层消费当前时间和天气；旧太阳/天空写入器与新表现层不能同时控制同一灯光。必要时替换表现控制，但不保留两套自动天气调度。

先让所有雨态正确驱动云形，再调整视觉细节：大尺度天气分布、中尺度云块、小尺度侵蚀使用不同速度；避免靠提高全局密度把天空填成均匀灰板。以云遮光、天空散射和环境反射共同建立阴天层次，统一三图衰减曲线。固定时刻/曝光做诊断，然后复验实际自动曝光；不全局增大体积云采样来掩盖云形问题。UE 官方说明了体积云材质、散射、云影和天空实时捕获的关系：[Volumetric Cloud Component](https://dev.epicgames.com/documentation/en-us/unreal-engine/volumetric-cloud-component-in-unreal-engine)。

雨效拆成近处稀疏细滴、中距离雨丝、远处雨幕/薄雾；尺寸、速度、透明度和落点随机变化，方向统一受风场控制。水花补充水冠/二次飞溅贴图或 flipbook，依据地面/积水区别表现。保留有限粒子池和粗频率表面采样。

遮雨检测只更新目标遮蔽值，逐帧按 DeltaSeconds 平滑；将玩家受雨程度和窗外世界降雨分开。第一人称枪体不依赖静态网格距离场来做逐滴碰撞。

### 第二阶段：屏幕四周挂水

建议先用小型水滴状态缓冲或贴图图集，驱动一个后处理材质。静止小水珠、偶发缓慢下滑的大水珠及短流痕共同组成效果；折射只发生在水滴覆盖区域。其作用位置和混合顺序需在当前 UE 5.8 后处理链中验证：[Post Process Materials](https://dev.epicgames.com/documentation/en-us/unreal-engine/post-process-materials-in-unreal-engine)。

以下为首版可调的艺术目标，不是已测结果：

- 水滴集中在最外侧约 10%–15% 边带，四角最明显；中心宽度约 70%、高度约 70% 的矩形不生成水滴、不折射。
- 实际水滴总覆盖面积先限制在画面的约 3%–5%，不是把整个边带铺满水。
- ADS 时扩大保护区，保护铁瞄、镜片和准星；HUD 在清晰层合成。提供单独强度与关闭开关。
- 由“雨强 × 玩家暴露程度 × 朝向”决定新增水滴。进入室内停止新增，已有水滴继续缓慢流走；雨停后自然残留，首版可从 15–40 秒渐退调起。
- 宽屏、分辨率变化和疾跑急转不改变中心保护区，不让大流痕穿越瞄准区。

屏幕水滴是镜头/护目镜的视觉表达，和世界空间降雨分别控制；不要用全局地面 Wetness 直接驱动整个屏幕。

### 第三阶段：枪械表面附着

增加可复用的武器湿润材质函数，输入每把武器自身的 Wetness、DropletAmount、FlowAmount 和暴露权重。保留现有干燥材质的 PBR 输入及材质槽分工；M4 和 AKM 当前父材质不同，不能把所有槽统一覆盖成一个水材质。

- 水膜：依据金属、涂层、塑料、木材、织物分别改变粗糙度与颜色。光滑表面呈现细碎水珠高光，吸水表面主要加深颜色；保留底层法线和原有 Metallic 语义。
- 水珠：使用法线/高度图集及分布遮罩，按模型 UV 或骨骼稳定坐标采样。水珠应随枪、弹匣和配件移动，换弹时不发生世界坐标纹理游动。
- 流痕：稀疏、缓慢并随重力方向处理；掌心接触和被手遮住的部位减少新水滴，瞄具玻璃采用单独遮罩与强度。
- 每把运行时武器保留独立湿度，切枪不把湿度错误转移，也不让背包中未暴露武器凭空淋湿。雨停/入室后渐干，首版可从 1–3 分钟调起；是否跨会话保存属于后续明确的存档需求。
- 第一版使用材质层；只有实机近景仍需要时，再评估少量附着几何水珠，避免为每一滴水增加透明网格与折射开销。

## 4. GitHub 可借鉴项目

| 项目 | 借鉴点 | 接入判断 |
| --- | --- | --- |
| [codrops/RainEffect](https://github.com/codrops/RainEffect) | 水珠合并、滑落、擦除沿途小水滴，以及通过水滴法线数据折射背景；[作者原文](https://tympanus.net/codrops/2015/11/04/rain-water-effect-experiments/)说明大小水滴分层 | WebGL 示例，需将方法移植到 UE 后处理；不是 UE 插件。README 有自己的使用/再分发条件，不能标成 MIT |
| [SmailikHappy/GraphicsConcepting](https://github.com/SmailikHappy/GraphicsConcepting) | Niagara 接触与材质湿润之间通过屏幕空间 mask 衔接；[作者解析](https://smailikhappy.github.io/posts/Dynamic_wetness_article/)区分吸水与不吸水材质 | 项目声明 UE 5.4，并包含 SceneViewExtension 渲染通道；适合研究接触逻辑，直接迁入 5.8 要做渲染接口适配。该 mask 用于场景表面湿润，不等同镜头挂水；首页未见独立 LICENSE，直接复制前需补齐明确授权记录 |
| [sebh/UnrealEngineSkyAtmosphere](https://github.com/sebh/UnrealEngineSkyAtmosphere) | 天空散射、透射和 LUT 组织，帮助理解阴天颜色与光照一致性 | EGSR 2020 论文配套独立 DX11 示例，仓库有 MIT 许可；是技术参考，不是完整云雨系统，也无需重新实现 UE 已有的大气渲染 |

## 5. Fab 候选与排除项

以下根据 2026-09-12 查看的商品页与作者文档筛选。未在本机导入验证，不能宣称已适配当前 UE 5.8.2/Substrate 工程。价格随地区、许可档和促销变化，本次没有取得可靠的当前结算价，因此不列采购总价。

| 候选 | 适用范围 | 本项目建议 |
| --- | --- | --- |
| [Ultra Dynamic Sky](https://www.fab.com/listings/84fda27a-c79f-49c9-8458-82401fb37cfb) | 商品已包含 Ultra Dynamic Weather；天空、云、天气可统一表现 | 整体路线首选评估。作者 [9.7 文档](https://www.ultradynamicsky.com/Documentation/V9/9-7)确认 Screen Droplets，以及 Surface Weather Effects 的水珠/流痕和 Local Space / For Skeletal Mesh 输入。仍需定制边缘保护、ADS 和武器独立湿度，并接入现有时钟 |
| [Easy Rain](https://www.fab.com/listings/274c81ae-3554-4801-8ec0-04f93212da06) | Niagara 雨与水坑、表面水滴/流痕材质函数 | 局部雨效升级首选评估。需要 Mesh Distance Fields，本工程配置已开启；云、屏幕保护区和枪械运行时湿度还需自己接。商品离线渲染演示的运动模糊效果不能当作本项目游戏效果；当前第一人称摄像机 MotionBlurAmount=0 |
| [Sky Creator](https://www.fab.com/listings/39b1579f-305c-47c5-809e-74fb7d5ec520) | 多层体积云、天气预设、Niagara 和表面材质效果；支持外部控制器 | 更偏云层美术控制的整体备选，与 UDS 选一条路线；不为同一项目叠加两套云和太阳控制 |
| [Rain Drops – Wet Surface VFX](https://www.fab.com/listings/5ed72ea5-9036-45da-84d2-dbb2eb64ba2b) | 可动/静止水滴、流痕、湿层、渐入渐出和可调渲染纹理尺寸 | 仅需补镜头挂水时的小范围候选；页面没有证实 FPS 中心保护区或当前 Substrate 兼容，需改材质并实测 |
| [Rain – Water Drop – Flow Material & FX System](https://www.fab.com/listings/d6acc01f-872b-4cf0-a599-a132a4f526f0) | 有材质函数、投射体积和相机后处理 | 暂不列采购首选：当前商品页明确记录启用 Substrate 时崩溃。工程已开启 Substrate，不为使用此包关闭全项目渲染特性 |
| [Cinematic Droplets Pack](https://www.fab.com/listings/6ec383db-9156-4efa-a397-dd700a356595) | Houdini 制作的高密度几何水滴，面向特写和 Path Tracing 材质 | 不作为实时 FPS 枪身大量挂水的首选；其定位和性能路径与本需求不同 |

资产购买、加入 Fab 库、导入 UE、材质消费参数、实机验收是不同阶段。获得资源后先保留来源与许可记录；公开源码仓库不直接提交未核准再分发的 Fab 二进制。

## 6. 下一轮可复现验收

固定三张地图各一组相机与时刻，以 Clear → Cloudy → LightRain → Rain → Storm → Clear 连续测试两轮。当前第一处明确失配是进入 LightRain/Rain 后云组件 Target 仍为 0；首先验证其修复，再评估云噪声/散射调节。

| 场景 | 期望结果 | 记录 |
| --- | --- | --- |
| 固定视角雨态切换 | 云量/云形先连续变化；光照、雨和雾跟随；晴天可完整恢复 | 同机位截图和 30–60 秒视频、天气状态与材质参数曲线、活跃云/光组件数 |
| 屋外 → 门口 → 室内 → 望向窗外 | 镜头和枪停止新增水滴并保留残水，声音平滑；窗外继续下雨 | 暴露度、粒子生成率、镜头/枪湿度轨迹 |
| M4/AKM：持枪、ADS、普通/空仓/弹鼓换弹、切枪 | 接触动作与瞄准可读，水珠固定于对应表面，弹匣/配件正确随动 | 第一人称运动录像及材质实例列表；手臂/瞄具保护区截图 |
| 晴天持续恢复、再遇雨 | 不累积灯光压暗；干燥完成；组件和材质实例数量不增长 | 两轮状态记录、计数及一天 2160 秒时钟合同 |
| 1080p/1440p、16:9/超宽屏、低中高档 | 中心区域清晰，水滴强度选项有效 | 配置与对应画面 |
| 性能比较 | 同硬件、分辨率、相机、预热、场景负载；分别开关云、雨、屏幕、枪材质 | GPU 中位数/P95、显存、Niagara 数量；并行编辑器竞争时不作有效 A/B 结论 |

首轮性能规划目标：屏幕挂水和枪械湿润合计额外 GPU 开销争取控制在约 0.5–1 ms（1440p、目标硬件下待测）；云和降雨分别测量，按项目帧预算取舍。这是开发预算，不是已经达到的性能。

落地顺序：先修表现链和遮雨过渡，再完成镜头与枪械的小样；用同机位实机视频比较后，确定是否用 Fab 系统替换现有表现层。验收结果再决定正式资产引用与发布范围。
