# 公寓海湾射灯与霓虹探照灯 V9

目标地图 `/Game/GameMaps/L_CyberpunkApartment`。制作源：`SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV9`；资产：`/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV9`。

## 灯光布置

| 类别 | 布置 | 初始设置 |
| --- | --- | --- |
| 屋顶扫光 | NEXUS 双塔、ESTUARY 数据中心、PORT 通信塔各一对 | 6 道光束，青蓝与紫／洋红搭配，长度 340–480 米 |
| 固定建筑射灯 | NEXUS、ESTUARY、TIDELINE 基座各两盏，向上照立面 | 6 个真实 Spot Light，75,000–120,000 cd，衰减半径 110 米，内／外锥角 12°／22° |
| 昼夜 | 真实射灯读取既有 AP7_Atmosphere → AFPSWeatherManager；材质读取既有 SkyAtmosphere 主光方向 | 白天熄灭，黄昏／清晨平滑过渡，不新建天气时钟 |

扫光采用远景装饰性柔边光束网格；固定射灯负责真正照亮建筑。光束的长度方向逐渐衰减、边缘柔化并带极弱雾丝变化，末端没有实体封盖。背景天气雾浓度不改写，光束与当前全局雾浓度不绑定。它们不是逐体素物理散射模拟，也不代表对任意遮挡物做完整光线求交。

俯仰中心为 18–22°，摆幅 6–8°，因此最大偏离竖直方向为 30°；横扫摆幅 24–38°。俯仰周期 32–43 秒，横扫周期约 42–56 秒，六盏相位错开。光束向天空扫动；灯具云台、灯头和光束共用相位与旋转函数。固定底座带旋转轴承、支架、散热环、侧轴、镜片和接线箱。

## 调整入口

- `design.py` 的 `SEARCH`：位置 `p`（沿用楼群作者坐标，单位米）、`color`、`length`、`tilt`、`tilt_sweep`、`yaw`、`yaw_sweep`、`period`、`phase`。
- 材质实例 `MI_AP9_<名称>_Beam`：`Tint` 与 `Gain` 控制光束颜色／亮度。`Tilt`、`TiltSweep`、`Yaw`、`YawSweep`、`Period`、`Phase` 控制运动；修改运动时同步相应 `_Head`、`_Lens` 和 `_Yoke` 实例，Yoke 的两项 Tilt 保持 0。
- `design.py` 的 `FIXED`：固定射灯位置、照射目标 `target`、色彩、坎德拉强度。关卡中 `AP9_*_Spot` 对应真实射灯；运行时强度来自 AP7_Atmosphere 的绑定值。

## 开销与原有系统

- 3 个可复用网格，无新增贴图；金属颜色、法线、ORM 复用 V7 加工金属资源。
- 扫光通过 GPU 材质 WPO 驱动，没有增加逐帧 Actor 或定时器。WPO 光束的网格边界按扫动包络扩展，避免转视角时因静态包围盒裁剪光束。
- 6 盏新增射灯不投射动态阴影，体积散射和间接光强度设为 0，只负责局部立面。最大显示距离 6 km，末端 500 m 渐隐。已有太阳、Lumen、室内灯与反射设置保留。
- 天空扫光使用单层加法材质，远景可见光束不进入光追几何；不添加 SceneCapture、媒体播放器或全局后处理。
- 真实射灯加入现有公寓 0.25 秒表现调度。V7 → V8 → V9 安装链在成功保存后接续，避免重装广告牌时丢失灯光。

本轮不修改 C++。制作、材质编译、资产导入与地图保存属于交付；没有运行游戏、验收截图或帧率测试。最终状态以本轮 `assets_saved.json` 与 `installed.json` 为准。

## 当前接入状态

2026-10-22 22:25:58（Asia/Shanghai），`publish-03` 后台 commandlet 完成，退出码 0。已导入并保存 3 个网格、3 个主材质和 30 个材质实例；`assets_saved.json` 为 `assets_saved`，`installed.json` 为 `map_saved`。

地图已保存 36 个本轮 Actor，其中 6 个为真实射灯、6 个为扫光网格，其余为灯座和灯头。既有 AP7_Atmosphere 保留原有绑定并追加 6 盏射灯，总绑定数为 25。地图修改前备份位于 `RefinementV9/Backups/20261022-222552`。

本次通过 `-nullrhi -nosound` 完成资产制作与地图保存，没有打开交互式编辑器、运行游戏、截图或测量帧率。保存结果不代表游戏内观感与渲染性能已验收，交由用户体验。
