# 铸造台挂件随风与高炉风格统一

用户要求：参考 PKM 挂件增加工具摆动，与高炉烟雾统一风向；铁匠台整体做旧，接近高炉。

## 动态挂件

- 高炉和挂件共同调用 `UFluidPresentationSubsystem::WindWithGustAt`。保留原有天气主风、雨天阵风公式、屋檐遮蔽系数与 260 cm/s 上限，阵风每帧只计算一次。普通枪口烟的既有 `WindAt` 不变。
- `UCastingToolRackComponent` 在 `AVoxelBuildPrefabActor::Configure` 中按 `casting_station` 注册，覆盖放置和存档重建。异步加载台体及四个工具，无每帧 Actor 扫描和同步资源读取。
- 钳子、横刃锤、锉刀、拨火钩各为刚体网格。挂钩和横梁固定，转轴为吊眼内壁与挂钩下沿接触点 `(8/27/43/57,44,94.30)` cm。
- 沿用 PKM 的阻尼弹簧、软限位、低回弹硬限位及最大 1/240 秒子步思路。各工具响应分别为 `.72/.34/1/.80`，横向上限为 `3.8/2.4/4.5/3.2` 度，前后上限 2.4 度。重锤阻尼更大、风响应更低。
- 风每 0.2 秒采样；30 米内最多 60 Hz 更新，远处 2 Hz 距离判断、停止摆动。暂停恢复、移位重置，建筑坠落时挂件固定跟随台体。风压有沿共享风向的微小强弱变化，无风时不会自行左右摆动。
- `SM_CastingStation` 仍是完整的放置/图标/加载回退；加载完成后替换为 `SM_CastingStationBareRack` 并附加四件动态工具，避免静态工具重影。两种台体统一七个材质槽顺序；运行时仍按槽名转接材质覆盖，以兼容 FBX 导入压缩空槽，保留淬火水面 MID 和插槽。

## 表面处理

- 架子、箍圈和工具暗铁材质直接继承高炉 `M_BlastFurnace_WroughtIron`，使用相同扫描底色、AO、粗糙度、金属度与法线。
- 铁砧保留已选择的黑铁色和已认可几何。以高炉同组扫描贴图加入克制的氧化斑、积灰、凹处暗化；工作面比铸铁主体更光滑、更有金属反射。
- 木材继续使用项目 Normandy 木纹，降低偏黄饱和度、加入扫描 AO 与积灰，并保留桶内及水线以下湿润变化。石基座仍共享高炉石材。
- 本次不修改水面、淬火动画、锻造时序或高炉原材质资产。无新增外来贴图。

## 制作入口与状态

- Blender：`SourceAssets/CastingStationRealism20260927/author_geometry.py`，输出可编辑 `.blend`、整体台体、无挂件台体和四个挂件 FBX。
- 接入：`install_wind_weathering.py`；现有整体 `install.py` 同步支持新网格及材质，避免重导回退。
- 修改前源文件保存在 `BeforeWindWeatheringV7`；资产保存时备份到 `RealismV5/BeforeWindV7`。
- 常规构建已完成：`Saved/BuildEditor/casting-wind-weathering-r2-20260927.log`，结果 `Succeeded`。
- 五个表面材质及第一批七个网格已后台导入保存：`Saved/casting-wind-weathering-commandlet-r2-20260927.log`，结果为 0 errors。高炉实际材质参数记录在 `furnace-style-source.json`。
- 导入诊断提示部分 UV 切线退化，已修正作者导出：合并前统一零号 UV，保留木桶纵纹与水面圆盘映射；仅对坍缩 UV 的三角面重新投影。修正后的八个网格（增加独立木桶）已后台导入保存，回执为 `SourceAssets/CastingStationRealism20260927/tool-rack-20260927-203741.json`。
- 最终资产执行日志：`Saved/casting-wind-weathering-mesh-final-r2-20260927.log`，结果 `Success - 0 error(s), 5 warning(s)`，本次不再出现 FBX 切线退化警告。材质保存记录为同一作者目录的 `wind-weathering-*.json`。这是构建与保存结果，不是运行或视觉验收。
- 遵循用户规则：不启动编辑器、游戏、预览渲染或自动测试；视觉与运行效果由用户测试。
