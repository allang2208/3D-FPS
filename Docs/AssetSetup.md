# 恢复完整 UE5 内容

源码来自 2026-09-10 的本机 `D:/FPS3D/FPSGAME`。此次换引擎整理保留完整模块与配置，未公开整套本地 Content 和二进制作者源。许可证及图片 provenance 只说明已有记录，不自动授予原始文件公开分发权。

## 本机继续开发

本机原工程未移动，仍打开 `D:/FPS3D/FPSGAME/FPSGAME.uproject`。如使用新的 Git checkout，在确认拥有使用许可后，从完整宿主复制 `Content`，保持相对路径和 World Partition 的 `__ExternalActors__`/`__ExternalObjects__` 成套；不要用旧快照覆盖当前源码。复制前处理目标同名文件的差异，不批量覆盖新工作。

作者编辑还需要本机 `SourceAssets` 中的 Blend、FBX、声音和引用源；仓库只包含当前 M4 三段依赖链的作者脚本及记录，恢复本地源目录可补齐其输入。`Tools` 中部分旧参考导出器仍指向本机 Godot 归档，不参与 UE 游戏运行。历史工具带绝对宿主路径，运行前检查其输入和输出路径。

## 主要资源依赖

| 内容 | 当前恢复位置/说明 |
| --- | --- |
| 启动地图 | `/Game/GameMaps/DayNight_Lighting`；按 Config 的真实路径恢复 |
| 枪械/手臂 | `Content/Weapons`，包括 M4HK416Replica、M4WrapGripFinal、M4SlapImpactFinal、M4TacticalTossFinal 及枪匠配件 |
| 声音 | 枪械 HK416 派生音效和天气资源；具体引用见当前源码及已有来源说明 |
| UI/物品图标 | `Content/ColdSteelUI`、`Content/UI`、`Content/ColdSteelData/Icons`；JSON provenance 不等于图标授权 |
| 天气/场景 | `Content/Weather`、PWL_Light_Manager、Lighting、SceneTests 及相关地图和场景包 |
| 怪物 | `Content/Monsters`、`Content/ZombieFemale`；用户提供包的许可尚需独立确认 |
| 作者源与 MAT | 本机 `SourceAssets` 与原 MAT 工具资产；MAT 不是本次公开发布的插件包 |

`ContentInventory.json` 列出宿主各内容目录的文件数和大小，供检查恢复范围；它不是每个资源的授权证明。

## 插件和构建

保留宿主原 `FPSGAME.uproject`。CommonUI、EnhancedInput、PCG、PythonScriptPlugin、EditorScriptingUtilities、ModelingToolsEditorMode 等按描述符启用。`ModelContextProtocol` 与 `AllToolsets` 是额外编辑器工具，需要安装兼容 UE 5.8 的版本；不需要这些工具时可以在自己的 checkout 中关闭这两个 Editor 插件，再生成工程，切勿因此移除游戏模块依赖。

C++ 编译不需要先公开地图素材；成功编译也不意味着缺失地图/动画可以运行。恢复资源后用对应 `Tools` 脚本和真实游戏镜头验证；重建原生模块后启动新编辑器进程，避免旧模块仍在内存。

Windows 系统字体及其派生字体仅按工具中的本地用途处理，不随本仓库公开发布。现有天气来源说明见 [ThirdPartyNotices](../ThirdPartyNotices/WEATHER_ASSETS.md)。
