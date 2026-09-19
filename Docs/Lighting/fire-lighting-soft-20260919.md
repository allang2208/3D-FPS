# 夜间火把与枪口光照调整（2026-09-19）

用户要求：减轻青铜火把夜间刺眼、杂乱光斑与枪口火光遮挡瞄准，采用前一轮提出的柔和方案。

## 本轮设置

- 玩家第一人称相机：Lens Flare=0、Bloom Dirt Mask=0；Gaussian Bloom，总强度 0.15、Gaussian 系数 1、阈值 2。构造与 BeginPlay 同时应用，主场景及生成世界使用同一规则。保留地图/天气原有曝光。
- 青铜火把：350 lm、影响半径 500 cm、SourceRadius 6 cm、SoftSourceRadius 8 cm、SpecularScale 0.6、体积雾贡献 0.08。亮度以 1.5 Hz / 0.945 Hz 两条平滑曲线混合，最大幅度 ±4%，按位置错开相位。保留点火窗口、淡入淡出与青铜材质。
- 既有火把：BeginPlay 将精确匹配旧默认的 600 lm / 900 cm / 0.12 / 7.5 Hz 迁移为新参数，不重写地图与玩家建造存档，其他自定义值保留。
- 火把两层火焰：项目独立材质 `MI_TorchSoft_Flame01/02`，Emissive_Intensity 从源材质 20/40 调为 12/24。原包材质、飘灰、热扰动、火苗尺寸与 Alpha 曲线保持原样；当前 `NS_TorchFlame` 使用这两份实例。
- 枪口 V10：亮芯 25–40 ms，前焰 40–60 ms，侧焰 35–55 ms。现有预乘透明度与柔边淡出保留；RGB 增益腰射 0.55、ADS 0.42、LPVO 0.35，随机范围 0.92–1.08；ADS 尺度 0.78。默认关闭高倍镜对世界火光的倍率放大。
- 枪口备用点光：350 lm、SourceRadius 3 cm、SoftSourceRadius 5 cm、SpecularScale 0.35；体积雾/间接光贡献 0。正常 Niagara 路径仍不额外叠加这盏备用灯。
- LPVO：FlashAlpha 0.15、Hold 45 ms、Radius 0.28、OffsetY 0.90、Burst 10 ms；Ember 0.025 / 85 ms、EdgeBloom 0.08、Smoke 0.045 / 140 ms；AmbientAlpha 与 LensDirtAlpha 为 0。热烟只在镜口下部漂移。
- 所有 LPVO 镜内叠加效果共用中心保护：镜口半径 20% 内不绘制，20–38% 之间平滑淡入。跨越保护圆的三角形也不绘制，避免只有顶点透明而面片仍覆盖目标。分划绘制和射击射线不变。

## 作者入口与资产

`Tools/AssetPipeline/soften_fire_lighting_20260919.py` 在原火把 / gunplay 生成器之后运行，只保存两份项目 Niagara 系统与两份火把材质实例，不保存关卡及无关脏资产。

两份 Niagara 改前备份：`Saved/LightingSoft20260919/Before/`。原包素材不改动、不新增网络下载。已有源资产许可继续适用。

本轮不启动游戏、PIE、截图、渲染或回归。资产编译和原生构建属于接入步骤，视觉效果由用户自行测试。

原生接入：FPSGAMEEditor Development 构建成功，生成 `UnrealEditor-FPSGAME-9191721.dll`（使用独立后缀以保留正在打开的用户编辑器）。日志：`Saved/LightingSoft20260919/build-editor.log`。当前编辑器未重启，须重启后测试代码调整；资产已保存。这不代表视觉或游戏测试通过。
