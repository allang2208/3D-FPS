# 暴风雨闪电与延迟雷声（2026-09-19）

最新的声画排查、昼夜闪电亮度及雷声起音修正见 [雷电可见度与雷声混音修正](lightning-audibility-fix-20260919.md)。下文包含早期默认值，不代表当前最终设置。

后续根据“没有看到闪电／听到雷声、乌云僵硬”的反馈，已补齐旧昼夜关卡的云材质接入，并调整首发延迟、云层运动与雷声混音；当前规则见 [暴雨云层与雷电接入修正](storm-motion-fix-20260919.md)。下文保留初版实施记录。

## 实施计划

沿用唯一的 `AFPSWeatherManager` 和现有雷声音频，按下列时序实现整片天空的闪电氛围。只执行制作、接入和必要构建，视觉、听感与性能测试由用户完成。

| 阶段 | 时间与行为 |
| --- | --- |
| 触发 | 只在暴风雨、有效雨量达到 0.85 后触发；间隔随机 12–25 秒 |
| 提亮 | 0.05 秒平滑升至峰值；每次峰值随机为设定强度的 82%–100% |
| 保持 | 保持约 1 秒，不使用原来的高频三连闪 |
| 恢复 | 1.5 秒平滑淡出，回到正在运行的昼夜与天气背景 |
| 雷鸣 | 从闪电开始随机延迟 2–5 秒；三组现有无雨风背景雷声轮换 |
| 离开暴风雨 | 取消待播放雷声、归零闪电，已播放的雷声用 0.75 秒淡出 |

## 实现

天气管理器计算唯一的连续 `WeatherLightning` 亮度值。云、丘陵天空和天气适配天空材质通过原有 `MPC_FPS_Weather` 读取该值。MPC 在同一帧闪电更新后发布，仅数值变化时写入；晴天和保持阶段不重复更新闪电参数。

`M_FPSLayeredClouds` 的闪电发光复用已经算好的 RGB 消光密度，密度为零时不会发光。按密度保留云团明暗，限制发光与消光的比例，避免厚云累积过强亮度。默认云发光倍率为 `FPS_LightningCloudLuminance=1.2`。天空背景增加冷白略偏蓝的统一亮度，默认 `FPS_LightningSkyLuminance=0.35`；不改变太阳、月亮、曝光或 Bloom。

接入目标包括现有丘陵天空主材质，以及 `DA_WeatherPresentation.SkyMaterials` 引用的项目天气天空适配主材质。引擎与原始 PWL 素材保持不变。云和天空的制作脚本同步调用共用的接入函数，后续重建材质也保留闪电入口。

雷声使用原 `ThunderAudio` 与新增的 `ThunderTailAudio` 两个复用组件，最多两声同时播放。待播放事件最多一个，直接由天气 Tick 倒计时，不为每次闪电创建组件、Actor 或 Timer。音频未结束时不抢占它；两个组件均忙则推迟整次闪电，保持声画配对。室内复用现有遮蔽读数，将雷声降至户外的 38%，并增加低通滤波。

## 性能取舍

- 新的天空闪电仅增加少量标量／向量运算。云发光复用既有密度，不新增噪声、体积纹理采样、体积云组件或散射阶数。
- 复用原闪电点光作附近地面的柔和响应：半径从 2000 米缩至 90 米，移到视点上方约 35 米；默认 60000 流明，关闭阴影、体积雾散射和间接光，镜面贡献设为 0.1。闪电结束后隐藏点光，室内补光随遮蔽衰减。
- 沿用现有天空捕捉，不额外请求即时 Skylight Recapture，不创建第二个太阳或全屏后处理。
- 无新增逐帧场景扫描、碰撞射线或动态材质创建；音频音量／低通仅在遮蔽或增益明显变化时更新。
- 未测量帧率或 GPU 耗时；以上是代码和材质的开销控制措施，不是性能验收结论。

## 可调参数与文件

天气 Actor 的 `Weather|Lightning` 分类提供保持时间、淡出时间、闪电间隔、雷声延迟、闪电强度和补光流明；`Weather|Audio` 提供雷声音量。默认值见上表。

制作脚本：`Tools/Weather/build_storm_lightning_materials.py`。入口脚本 `build_layered_cloud_material.py`、`build_hills_daynight_sky.py`、`build_natural_weather.py` 已同步保留接入。

备份与材质制作记录：`Saved/StormLightning20260919/`。未启动 PIE、试听、截图或做运行验收；完成构建后由用户重启编辑器测试。

## 制作与构建记录

- 材质制作命令完成并保存三个主材质：`/Game/Weather/Materials/M_FPSLayeredClouds`、`/Game/WorldGeneration/TemperateHills/Sky/M_HillsDayNightSky`、`/Game/Weather/NaturalV2/M_Atmospheric_M_Cubemap_Sky_Material_c3b1beab`。材质编译完成；命令返回成功，未执行游戏渲染或验收。
- 修改前的材质备份：`Saved/StormLightning20260919/Before-20260919-181433-933295/`；制作清单：`Saved/StormLightning20260919/materials-authored.json`；日志：`Saved/StormLightning20260919/material-build.log`。
- 原生编辑器目标构建返回 `Succeeded`，UBT 提示 `Target is up to date`，本次未重复执行编译动作。构建日志：`Saved/BuildEditor/build-20260919-181619.log`。天气源码修改时间为 18:11:40，普通编辑器模块生成时间为 18:12:23。
- 未执行运行测试或帧率／GPU 性能测量。已打开的编辑器需重启以加载新的原生组件与参数，再由用户体验暴风雨效果。
