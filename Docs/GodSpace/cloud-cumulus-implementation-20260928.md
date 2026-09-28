# 主神空间：积云密度重制

**当前状态：用户认为云海仍不真实，已要求隐藏。** 本文为制作与黑屏修复历史，不是云形验收结论。当前重建配置保留隐藏，源码/资源保留用于定向恢复；已废弃的旧补色分支按 [归档清单](../AssetArchives/godspace-20260928.json) 移入 trash。

后续本日的云团密度修正与喷泉波浪复用见 [喷泉波浪复用记录](fountain-wave-reuse-20260928.md)。下文的首次云形参数及截图保留为过程记录；最新主体/细节尺度与散射参数以该记录和当前 HLSL 为准。

2026-09-28，用户授权继续 GitHub 调研建议。初次后台制作后，用户明确追加了“启动截图检查”和黑屏排查；以下保留制作方案，并记录后续发现的接入错误。初次编译成功不等于云渲染通路有效。

## 已保存的接入

- 新主材质：`/Game/Props/GodSpaceLayout20260927/Materials/M_GodSpaceCloudSea_Cumulus`。
- 原正式实例 `MI_GodSpaceCloudSea` 已切换到新主材质，主场景继续引用该实例。
- 新的现有素材派生资源：`VT_GodSpaceCloudNoise_LinearMips`，128³、B8G8R8A8；关闭 sRGB，以 SimpleAverage 生成 mip 并使用三线性过滤。没有下载新的云贴图，也未改写引擎原纹理。
- `/Game/GameMaps/DayNight_Lighting` 保存云层视图采样倍率 3.0、阴影视图倍率 0.5；天空蓝图的持久配置与其组件同步写入。

## 云形、近远距离与光照

参考 [Takram clouds.glsl](https://github.com/takram-design-engineering/three-geospatial/blob/ce69b0997845b125f3b0b59134b493d9813ae4a6/packages/clouds/src/shaders/clouds.glsl) 的高度整形和有界密度侵蚀，改写成 UE HLSL。版本、原源码和 MIT 授权保存在 `SourceAssets/GodSpaceLayout20260927/Integration/ThirdParty/TakramClouds/`。未导入其 WebGL 渲染器或示例纹理。

`CloudSeaCumulusCoverage.hlsl` 使用现有天气分布图改变云顶高度，并以幂函数和圆拱剖面收拢云顶。`CloudSeaCumulusDensity.hlsl` 使用现有 Perlin-Worley 的 R 通道，在两个空间尺度上做主体与细节侵蚀。主体可以被侵蚀为空，不再强制保留最低密度厚膜。风位移、连续时钟、天气状态和闪电沿用原系统。

宏观三维云形保留到远处；天气图和主体噪声连续提高采样 mip，近景细节在 2.5–6.5 km 内逐渐消失，100–150 km 做密度淡出。没有另加一张远景云平面。撤掉上一版 `cloud_sea_lighting.py` 的暖色抵消和漫射补光接线，新材质由 UE 原生散射、环境光和自阴影受光；发光仅保留共享雷电。黄昏仍可能自然呈暖色，本次不通过固定白色发光覆盖昼夜配光。

80% 保留为分布目标，天气图仍以第 20 百分位为平面支撑阈值；体积侵蚀、过滤和透视会改变最终可见覆盖。没有测量或宣称画面已达到精确 80%。

## 性能取舍

仍只有一层 VolumetricCloud，空区使用保守密度跳过；主射线近处最多 3 次纹理读取、中远处最多 2 次，阴影不读取近景细节。没有新增 Actor、Tick、粒子或全屏云渲染器。

本机引擎默认每 15 km 达到主射线最大采样数，基础为 96。700 m 云层按视图倍率 0.7 计算仅约 3 次采样；此次倍率 3.0 对应约 13 次。这是按引擎公式估算的垂直穿层情况，实际步数受射线长度、空区与提前终止影响。提高采样会增加成本，远处也比旧版多保留一次主体噪声读取；未声称 FPS 提升或零额外开销。全局重建模式、反射预算、光追和 Lumen 设置未更改。

## 制作记录与恢复

制作入口 `Integration/produce_cloud_sea.py`，完整重建入口 `build_cloud_sea.py` 与 `configure_cloud_sea.py` 已同步，后续布局重建沿用新方案。旧主材质保留，新版正式实例与地图的修改前副本和 SHA256 位于 `trash/godspace-cumulus-20260928/`。

制作回执位于 `Integration/Receipts/cloud-sea-authored.json`、`cloud-sea-map.json`、`cumulus-build-completed.json`。创建材质过程中先设置 Volume 域后设置 Additive 导致一次临时编译警告，制作顺序已修正；纹理创建期间也有尚无平台 mip 的临时警告。后续必要构建已取得有效 128³/B8G8R8A8 纹理资源，最终材质编译错误列表为空并保存，见 `cumulus-final-build-stdout.log`。这些是构建结果，不是游戏画面验收。

## 截图检查中发现的黑屏错误

用户截图中的红字为“在体积云组件上指定的材质没有 UsedWithVolumetricCloud 标记集”。读取正式主材质确认 `used_with_volumetric_cloud=False`。只设置 Volume 域和 Additive 混合不会自动满足云渲染用途；本机引擎 `VolumetricCloudRendering.cpp` 在缺少该标记时提示该错误并直接返回。此前记录的普通材质编译错误列表为空，不能证明体积云专用着色器已编译。

`build_cloud_sea.py` 已显式设置该使用标记，增量落盘入口为 `fix_cumulus_cloud_usage.py`。另外，高度剖面中负底数 `pow(x,2)` 已改为 `x*x`，避免无效值。修复不删除或替换太阳、天空光，也不关闭硬件光追或 Lumen。

截图与修复回执记录在 `Saved/GodSpaceCloudReview20260928/` 和 `Integration/Receipts/cumulus-cloud-usage-fixed.json`。光追几何内存预算警告是独立事项，本次没有通过提高预算或关闭光追掩盖它。云海覆盖率和帧率仍未量化验收。

修复已在现有编辑器中应用，游戏运行时资产保存被 UE 拒绝后，编辑器退出，随后通过 D3D12/SM6 后台 commandlet 完成重编译和保存，退出码 0。首次读取使用标记为 false（`blackout-material-usage.json`）；后台读取时已经为 true（退出编辑器期间资产另有保存），最终后台另存回执记录为 true，编译错误为空。

按用户此前明确的截图要求重新载入并运行主场景，运行中的 `MID_MI_GodSpaceCloudSea_0` 查询云用途为 true（`blackout-runtime-fixed-state.json`），太阳组件可见、强度 500，当前使用的 Cubemap SkyLight 可见、强度 150。`blackout-usage-fixed.png` 的实际游戏截图显示天空、建筑与阴影恢复，黑屏问题已消失。下方云海另拍 `blackout-cloud-sea-fixed.png`：能够显示云与海面空隙，但云顶仍偏平、边缘偏软；这张图只证明渲染恢复，不代表最终云形观感完成。临时截图位置没有写入地图，临时后台节流设置已恢复，截图过程中原测试 Pawn 已结束，未移动新的 Pawn。
