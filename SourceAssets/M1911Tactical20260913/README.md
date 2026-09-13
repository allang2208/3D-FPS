# M1911 红色激光与手电接入

2026-09-13，复用现有战术设备，接入 M1911 的 `tactical` 改造槽，保留原有手臂、枪体和动作。

## 来源与装配

- 激光：`SourceAssets/TacticalDevices20260913/M4/laser/Editable.blend`，现用 TRELLIS 原型的游戏网格。
- 手电：`SourceAssets/TacticalDevices20260913/HunyuanV3/M4/flashlight/Editable.blend`，用户指定的混元 V3 游戏网格。
- 来源生成记录与素材约束沿用这两个现有目录，不将它们称作新生成模型或公共领域资产。
- 保留设备本体尺寸、UV0、几何细节和结构法线；只移除步枪专用接触座，改为 M1911 前部机匣下方的贴合座。两个变体互斥安装在 `WPN_root`，不随套筒或枪管单独后移。
- 以当前 M1911 Frame 三角面取得接触面，配件尾部在枪根作者坐标 Y=-0.064 m，位于扳机护圈前方；安装座位于 Y=-0.086 m，宽 16 mm、长 32 mm。激光沿用约 85 mm、手电约 120 mm 的原设备尺寸。手电向枪口前方伸出，未缩小整件模型。
- FBX 转为厘米、+Y 前向；运行时根据实际骨架的前后照门方向与枪根坐标转换，不沿用步枪组件的 0.01 缩放。Emitter/AimGuide 跟随各自设备导出。

## 材质

外壳、原设备金属安装鞋和新增贴合座使用 M1911 已有套筒及后部统一的烤蓝涂层：`Attachments20260913/Textures/T_M1911_Attachment_BaseColor` 与 `T_M1911_Attachment_ORM`，独立 UV1 按 10 cm 物理纹理尺度投射。对应涂层作者参数 Base=(0.022,0.028,0.036)、Roughness=0.26、Metallic=0.88；不把枪身 UV 图集直接套在附件上。

复制当前激光 OpticalV2、混元手电 MetalTail 材质后，仅替换金属涂层输入；保留原 UV0 光学纹理、结构法线/AO 连接及激光橡胶尾部，沿用现用手电的金属尾盖。激光红色发光由原纹理红色区与新位置的镜口顶点遮罩共同限制，避免沿用步枪坐标导致外壳发红。

三份干材质各有独立雨滴版本，接入现有 `WeaponWetness` 与 WeatherViewEffectsComponent；仅金属区域使用水珠，保留光学与激光橡胶区。天气库合并记录见 `installed.json`。

## 游戏与数据

- `Content/ColdSteelData/gunsmith.json`：M1911 开放 `tactical`，选择 `false` / `laser` / `flashlight`。
- 激光沿用通用 80 m、遮挡截断、ADS 汇聚准星，腰射散布 ×0.5，ADS 时间 -0.2 s；ADS 最低时间仍由现有枪匠计算的 0.001 s 下限处理。
- 手电沿用 850 lm、40 m 衰减、动态阴影、近墙亮度过渡，以及收起、卸下或打开枪匠时关闭照明的规则。
- `TacticalDeviceComponent.cpp` 通过 M1911 分支加载 `/Game/Weapons/M1911/Tactical20260913/{laser,flashlight}/SM_TacticalDevice`。已装备角色、枪匠草稿、未装备实例展示、背包动态武器图标和掉落继续共用 `SetGunsmithTactical`。
- 配件卡沿用现有战术大类图标；本轮没有新增二维配件图标。
- 打包目录增加 `/Game/Weapons/M1911/Tactical20260913`，依赖原有 M1911 涂层纹理及共享激光效果。

## 作者入口与交付范围

`read_fit_source.py` 读取装配源，`author_devices.py` 制作两个变体和当前枪上的可编辑组合；两处 `M1911_Device_Editable.blend`、FBX 及 `M1911_Tactical_Assembly_Editable.blend` 保存在本目录。`import_devices.py` 导入专用材质、模型与雨滴版本；首次天气库保存遇到文件占用后，`register_rain.py` 仅续写剩余天气映射。

两个设备、三份干材质及三份雨滴材质已保存。首次导入在天气库写入时遇到临时文件占用，续写脚本随后成功保存 RainVisibility 与 NaturalV2 两个天气库并生成 `installed.json`，未关闭用户编辑器。续写 commandlet 退出码为 1，汇总仅为工程既有 GameFeatureData 配置错误；Python 脚本执行成功，详见 `register-rain.log`。

原生构建成功：`UnrealEditor-FPSGAME-913202522.dll`，日志 `build-editor.log`。按用户规则未启动游戏、未执行测试、截图或渲染验收；导出、导入及编译属于制作接入，不代表运行或视觉验收。重启编辑器后由用户测试。
