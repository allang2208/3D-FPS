# 云材质升级（2026-09-19）

本次补完前一轮尚未制作的云形、边缘和散射材质。前一轮的暴风雨透光／灯光调整继续保留，详见 [暴风雨调整](storm-cloud-soft-lighting-20260919.md)。

## 已制作并接入的资产

- `/Game/Weather/Materials/M_FPSLayeredClouds`：项目自己的 Volume 主材质，由 UE 基础云材质复制后修改图结构。
- `/Game/Weather/Materials/MI_FPSLayeredClouds`：公共参数实例，也作为天气创建云层时的默认材质。
- `/Game/WorldGeneration/TemperateHills/Sky/MI_HillsClouds`：现有丘陵实例改用公共实例为父材质；关卡、地貌数据和异步加载路径继续使用原资产引用。

材质制作脚本：`Tools/Weather/build_layered_cloud_material.py`。原丘陵制作脚本 `Tools/WorldGeneration/build_temperate_sky.py` 同步改为引用新材质，后续重新制作不会退回引擎示例材质。

## 材质结构变化

1. 保留引擎布局纹理、云类型高度剖面与 3D 体积噪声，重新分配尺度：大尺度云团、中尺度扰动、小尺度细节；启用原来默认关闭的第三层噪声，降低扰动速度和强度。调整层积云、薄层云、雨层云权重，让主体与薄云有不同高度和形状。
2. 在 RGB 消光输出前增加独立的边缘塑形节点。低密度边缘平滑衰减，并对云层顶部、底部增加渐变；仍由已有噪声决定轮廓。只从原密度场减去物质，保留原空区域跳过计算的有效范围。
3. 调整双相散射参数，减弱过于集中的前向亮边；多次散射近似设为一阶，并启用地面反射贡献。保留体积自阴影。采用一阶近似的依据见 [Epic 体积云文档](https://dev.epicgames.com/documentation/en-us/unreal-engine/volumetric-cloud-component-in-unreal-engine)。
4. 云自发光输出接零，闪电继续由天气管理器提供。云底补光来自真实天空／日月／地面光照，夜间仍随昼夜控制器变暗。
5. 天气组件每帧传入 `FPS_WeatherBlend`，晴天到风暴的边缘密度过渡使用现有天气插值，不新增时钟或体积云组件。

## 参数入口

在公共实例中可调整以下参数；云密度、覆盖率和风暴权重仍由天气组件控制。

| 参数 | 本次值 | 用途 |
| --- | --- | --- |
| `Noise1_Coordinates` | 3.2 / 3.8 / 7.2 / 5.0 | 主云团尺度与扰动速度 |
| `Noise2_Coordinates` | 24 / 28 / 32 / -2.0 | 中尺度扭曲 |
| `Noise3_Coordinates` | 80 / 88 / 68 / 2.6 | 细节尺度 |
| `Noise_Strength` | 0.70 / 0.055 / 0.022 / 2.2 | 三层噪声强度及整体控制 |
| `FPS_EdgeFeather` | 0.18 | 边缘消光渐变宽度，风暴时降至其 80% |
| `FPS_EdgeSoftness` | 0.80 | 渐变权重 |
| `FPS_BaseFade` / `FPS_TopFade` | 0.08 / 0.14 | 云层底部／顶部渐变范围 |
| `Multiscatter_Controls` | 0.72 / 0.20 / 0.25 / 1 | 多次散射贡献、遮蔽、各向同性 |
| `Phase_Controls` | 0.55 / -0.12 / 0.28 / 1 | 双相散射分布 |

颜色向量 alpha 保留原语义。噪声向量 alpha 是速度／强度控制，按本次分层设计显式调整。

## 制作与交付范围

素材沿用 UE 引擎云纹理和函数；本次未导入 Fab 云包或改写引擎素材。已有其他地图单独指定的云材质保持其资产引用；本次正式接入现有丘陵云与天气备用云。

只执行资产制作、保存和必要编译。未运行游戏、截图、视觉验收或性能测试，画面效果和帧率由用户实机测试。第三层噪声及地面反射增加计算，一阶散射替代原材质的二阶近似；没有测量性能变化。

修改前资产备份、制作记录与编译日志位于 `Saved/CloudMaterialUpgrade20260919/`。重启编辑器加载磁盘新材质与原生模块后再进入游戏，避免当前会话继续使用已加载的旧资源。

最终材质构建使用 `compile_final.py` 完成着色器编译并保存上述三个资产；`material-build.log` 记录制作进程退出码 0，未启动游戏。编辑器正在 PIE 时使用独立制作 commandlet；该进程通过命令行配置关闭自己的 MCP 服务，避免占用用户编辑器的 8000 端口。

原生 `FPSGAMEEditor Win64 Development` 构建成功，耗时 135.86 秒，模块后缀 `919180006`。日志：`Saved/BuildEditor/layered-cloud-20260919-180006.log`。最初丘陵材质的修改前备份保存在 `Saved/CloudMaterialUpgrade20260919/Before-20260919-175508-662330/`。
