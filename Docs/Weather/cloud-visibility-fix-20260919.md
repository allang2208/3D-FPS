# 雨天云层消失：纹理绑定修复

## 本次继续排查确认的原因

用户反馈下述噪声修正后仍然没有云，并授权本次临时材质对照、截图和恢复。

真正缺失的是共享材质实例的纹理覆盖值。`build_layered_cloud_material.py` 复制了引擎 **母材质** `m_SimpleVolumetricCloud` 的图，但没有带入其可用 **实例** `m_SimpleVolumetricCloud_Inst` 的纹理。项目 `MI_FPSLayeredClouds` 和继承它的 `MI_HillsClouds` 实际读取到纯黑布局图、纯黑高度图和默认体积纹理。此前只看标量、图连接和编译结果，漏掉了这项关键输入；下方的噪声修正不能解决这个问题。

| 参数 | 修复后的纹理（引擎自带） |
| --- | --- |
| `Layout_CloudGlobalPattern` | `T_CloudPattern` |
| `Noise_Texture3D` | `VT_PerlinWorley_Balanced` |
| `Layout_CloudHeightProfile` | `T_Profile_08` |
| `Layout_GlobalCloudMask` | `T_CloudMask` |

四个资产均来自 `/Engine/EngineSky/VolumetricClouds/`。仅在项目共享实例设置覆盖，不改引擎资产、关卡或其他会话资产。丘陵实例继承相同绑定。增加 `repair_layered_cloud_textures.py`，并由完整重建脚本调用，防止重建时再次丢失。

### 本次针对性对照与边界

- 当前关卡 `DayNight_Lighting`，同一视角、云底 1.55 km、厚度 1 km；暂时停止云控制器和天空 Actor 的 Tick，结束后恢复材质、云层属性、天空网格可见性和视角。
- 隐藏天空背景网格后，现用图和引擎母材质图都没有可见云团；固定消光材质能改变遮光，说明体积层能进入渲染。
- 覆盖率升至 1.2、绕过新增边缘整形、直接读取密度打包数据或取消保守密度剔除，都未恢复可见云团；没有将这些临时设置应用到正式材质。
- 读取实际纹理绑定后定位到上述占位图。截图与临时诊断脚本在 `Saved/CloudDensityDiagnosis/`，正式修改与资产备份在 `Saved/CloudTextureFix20260919/`。
- 编辑器随后退出，使用资产制作命令补齐四个引用并定向保存共享实例。没有在修复后重新启动游戏截图，也没有进行性能回归或雷声试听；最终雨天观感由用户测试。没有增加云层或纹理采样次数，不据此宣称帧率已验证。
- 诊断用的三个临时材质在编辑器退出时被保存到磁盘；已按精确文件清单移出 `Content`，归档至 `trash/cloud-density-diagnostics-20260919/`，不留在正式资产目录。

资产保存结果：宿主当时正在更新原生模块，命令行启动受 `AutoFootstep`／`FPSGAME` 模块加载问题影响。改用 `Saved/CloudTextureFix20260919/AssetAuthor/CloudAssetAuthor.uproject` 的纯资产命令行宿主完成相同定向保存，退出码 0；四个绑定见 `authoring.json`。没有修改宿主插件配置，制作完成后已移除临时 Content 目录连接。

## 上一次的噪声修正记录（未解决无云）

用户反馈：上一轮调整后，下雨时看不到云。

## 定位

现有游戏日志确认 `DayNight_Lighting` 已绑定 `MI_FPSLayeredClouds`，并记录了暴风雨、闪电触发与雷声播放调用。因此本次针对已接入的新云材质，未再次更换天气控制器或增加云层。

第三层噪声的原始节点语义与此前调参理解不一致：`UseNoise3` 开启后，`Combine Noise3 MultChannel` 将主噪声项乘以 `Noise3_MultChannel.a × Noise`。之前把 alpha 设为 0.18，当作“18% 的细节混合量”；实际主噪声项乘数最多为 0.18。它压低了主噪声对云布局的正向扩张，再叠加降低的云种权重和边缘淡化，使本来稀疏的布局难以形成可见云密度。这不是把 `Cloud_GlobalDensity` 写成零，也不是缺少云组件的绑定。

## 修正

- 用 `lerp(1, saturate(Noise), FPS_DetailErosion)` 替换直接乘法增益；默认细节侵蚀量 0.18，主噪声项乘数为 0.82–1.0。保留既有第三次噪声采样及其不同尺度、运动速度。
- 恢复引擎基线的四种云布局权重 `Layout_CloudType=(1,1,1,2)` 与比例 `Layout_CloudPerTypeScale=(1,1,1,1)`。云量、消光密度与光照仍由现有天气参数控制。
- 保留柔和边缘与高度淡化、连续风偏移、积分噪声时钟、云层闪电发光和延迟雷声。
- 同步 `build_layered_cloud_material.py`，重建时也使用修正后的公式；仅修改并保存项目自己的 `M_FPSLayeredClouds`，不修改引擎素材或其他未保存资产。

## 制作交付

执行 `Tools/Weather/repair_layered_cloud_density.py` 完成材质制作、编译和定向保存，返回 `FPS_CLOUD_DENSITY_REPAIRED`。资产备份与制作清单在 `Saved/CloudVisibilityFix20260919/`。没有修改 C++，无需原生模块重建；编辑器已经载入并保存本次材质。

未切换天气、启动 PIE、截图、试听或进行运行／性能测试。日志用于定位已有行为，编译不代表已确认最终画面。由用户重新开始游戏观察雨天云层。
