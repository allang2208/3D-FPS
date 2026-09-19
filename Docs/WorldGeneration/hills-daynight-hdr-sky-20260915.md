# 丘陵复用 DayNight HDR 天空

丘陵继续由 `AFPSWeatherManager.NormalizedDayTime` 驱动昼夜，新增天空球与动态混合材质，不增加第二个时钟、太阳或曝光控制器。

## 本机资产

`/Game/WorldGeneration/TemperateHills/Sky/M_HillsDayNightSky` 从 PWL 的 `M_Cubemap_Sky_Material` 复制，保留不受光、天空材质的绘制方式。新的图表使用独立材质实例参数，避免主世界 MPC 的强度、旋转值干扰丘陵。

`MI_HillsDayNightSky` 已由作者脚本接入 `DA_TemperateHillsStreaming`。引用现有本机素材，不改源包：

| 时段 | 源材质 | 天空贴图 |
| --- | --- | --- |
| 朝霞 | `MI_Sky_Sunrise` | `T_HDR_Sunrise` |
| 晴天 | `MI_Sky_Sunshine` | `T_HDR_Sunshine` |
| 晚霞 | `MI_Sky_Sunset` | `T_HDR_Sunset` |
| 夜间 | `MI_HDR_Night_Sky` | `T_HDR_Night_00` |

源材质在 `/Game/PWL_Light_Manager/Shader`，贴图在 `/Game/PWL_Light_Manager/Textures/HDR`。商用源资产沿用现有本机授权范围，未公开发布二进制。

## 丘陵时序与天气

这些时间窗是本次适配丘陵现有 06:00 日出、18:00 日落的设置，并非复制 PWL 场景的整套灯光预设：

- 04:30–06:00：夜空渐变为朝霞。
- 06:00–08:30：朝霞渐变为晴天天空。
- 08:30–16:30：晴天天空。
- 16:30–18:00：晴天渐变为晚霞。
- 18:00–19:30：晚霞渐变为夜空；之后保持夜空到次日 04:30。

所有混合权重由当前时间直接计算。跨午夜连续，调时间和切换世界后无需追赶独立天空计时器。贴图旋转使用已有天气天数与时刻；默认每游戏日 1.08 圈，对应源 Sunshine 每秒 0.0005 圈、丘陵每游戏日 2160 秒。

天气读取 `UStormCloudComponent.GetStormBlend()`。原有体积云在晴天也保持可见，使用非零密度 0.008 和稀疏覆盖率；混合值达到 0.65 时，HDR 景象完全让位于已有大气背景。体积云仍由原天气系统负责风、覆盖率和暴雨，不复制云层。

白天的背景为 80% 现有大气、20% HDR 色调，比例由材质参数 `DayAtmosphereWeight` 控制。太阳圆盘使用 `SkyAtmosphereLightDiskLuminance`，读取现有索引 0 大气定向光的方向、大小、颜色及天气衰减；`SkyAtmosphereViewLuminance` 只提供散射背景，不能代替太阳圆盘。没有添加第二个太阳灯。

天空球半径 50 km，跟随视点，位于河谷地形、10 km 高度雾截止距离及体积云之后；关闭碰撞、投影与导航影响，参与现有天光实时捕获。资源在丘陵加载阶段异步准备，离开丘陵时释放。

## 可调参数

`DA_TemperateHillsStreaming` 的 `Sky / Day Night` 分类提供天空材质、天空网格、曝光补偿、起始旋转角度、每游戏日旋转圈数。清空天空材质引用可使用原体积云天空。

默认天空曝光补偿为 -4.5 档：源 Sunshine 预设 EV100 为 5.5，丘陵保留 EV100 1；源天空全局强度 1.5 作为材质参数 `HDRSourceIntensity` 保留。此补偿只调整贴图辐射亮度，不修改丘陵太阳、树荫曝光和天气灯光。四个贴图参数也可在 `MI_HillsDayNightSky` 中替换。

## 制作与交付边界

作者脚本：`Tools/WorldGeneration/build_hills_daynight_sky.py`。脚本只保存项目自有天空材质和丘陵 DataAsset；修改前备份已有目标资产到 `Saved/HillsHDRSky20260915/BeforeAuthoring-*`，制作结果记录为 `authoring.json`。

完成必要原生构建和材质制作接入。遵守用户规则，未启动游戏、渲染预览或进行视觉/运行测试；天空亮度、过渡观感和河面反射效果交由用户测试。已打开的旧编辑器需重启以加载新的原生模块。

## 用户截图反馈后的修正

用户反馈太阳和云不可见、天空出现蓝红小点。本次读取用户已有 PIE 日志及导出的源 HDR 像素，未启动新的游戏运行：

- 现有日志显示丘陵天空材质、体积云材质和原有定向光均加载成功；不是资源引用丢失。
- 第一版不透明天空材质遗漏太阳圆盘节点，盖住了引擎原本绘制的太阳；已补接现有大气光的圆盘输出。
- 第一版在晴天将体积云可见性和密度设为零；已移除此条件，恢复原晴天云层。
- `T_HDR_Sunshine` 的真实像素是粉紫色、云集中在地平线附近的天空，不能仅凭名称把它当完整白天云景。因此保留其色调，以原有大气作为白天主背景。
- 蓝红小点的局部截图与镜头眩光相似，但尚未通过现场对照确认。丘陵曝光组件现将镜头眩光强度设为 0，保留 Bloom；这是针对彩色光斑的处理，不宣称已实机确认其来源和消失。

源贴图读取记录在 `Saved/HillsSkyFix20260915`，材质作者脚本已更新。源 HDR 的显示转换仅用于查看现有像素，不属于关卡渲染验收。
