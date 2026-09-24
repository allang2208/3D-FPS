# 主场景反向亮斑排查记录

用户在祭坛主场景报告太阳相反方向出现亮斑／光晕。2026-09-24 已读取磁盘关卡与用户既有 PIE 状态，本记录不包含修复或视觉验收。

- 实际地图为 `DayNight_Lighting`，一盏 DirectionalLight；没有证据表明新增了第二盏太阳。
- PWL 配光 Profile 中的 LensFlareIntensity≈3.65 被第一人称相机覆盖：override=true、Intensity=0、PostProcessBlendWeight=1。因此此前基于 Profile 的镜头耀斑判断不成立。
- 运行天空不是只读关卡所见的原始 PWL 实例，而是 `StormCloudComponent` 管理的 NaturalV2 MID，母材质为 `/Game/Weather/NaturalV2/M_Atmospheric_M_Cubemap_Sky_Material_c3b1beab`。
- 视觉天空与指定立方图的 SkyLight 使用 `T_HDR_Sunshine_02`。MPC Sky Rotation=0、Sky Speed≈0.0005；视觉 HDR 按时间绕 Z 旋转，SkyLight 的 SourceCubemapAngle=0。该 HDR 自带明显日光高亮，而真实太阳另由 DirectionalLight 驱动。

现有证据支持继续排查 HDR 高亮、反射与太阳方向的关系，但没有完成比较实验，不能确认截图的唯一成因。没有调整材质、光源、曝光、Bloom、LensFlare 或 SkyLight。七张 HDR 的 BC6H 改动属于编码压缩，不能据此认定它制造了第二个太阳。

原始证据保留在本机 `Saved/Diagnostics/DoubleSun20260924/`：`main-sky.json`、`live-sky.json`、`alignment.json` 和成功调用记录。第三方材质与蓝图 `.copy` 导出保留本机，不公开分发。失败的 `KismetMaterialLibrary` 调用输出已归档；有效读取使用 `unreal.MaterialLibrary`。

本轮仓库整理没有运行游戏、截图、A/B 测试或重新采样；问题仍为待确认状态。
