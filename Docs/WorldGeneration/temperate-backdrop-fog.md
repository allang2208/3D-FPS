# 温带丘陵远景与 Normandy 低雾（2026-09-13）

## 本次接入

远景采用独立的粗网格地形与地表颜色图。近景仍使用现有分块地面、河流和植被；在近景加载范围之外延续同一个种子的丘陵高度。远处的草地、林地和裸土用颜色表现，不额外铺设草木实例。

| 项目 | 当前实现 |
| --- | --- |
| 远景几何 | 固定 3 个 DynamicMesh，共 25,088 个三角形，包含外沿下垂裙边 |
| 覆盖范围 | 中心代理覆盖可玩区，外围两圈延伸到世界中心 X/Y 各 ±5,120 米 |
| 地表颜色 | 按种子生成 1,024 × 1,024 颜色图，BGRA8 约 4 MiB，无持续纹理流送 |
| 近远衔接 | 可玩区覆盖遮罩；地块可用后隐藏对应代理，卸载时恢复；近景裙边延伸到代理高度下方 |
| 初始化 | 纯数值后台任务；主线程每帧提交最多 1 个远景网格；完成后才结束场景 loading |
| 游玩成本 | 无远景碰撞、导航、投射阴影或植被实例；移动时只更新小型覆盖遮罩 |
| 大气 | 使用关卡已有的天空、大气和高度雾；雾色跟随现有天气时钟，每 0.25 秒更新 |

远景使用黄褐草地与低饱和林地颜色，配合浅色空气透视衔接天空。背景圈的外围添加低矮大尺度起伏；不修改可玩区地形。这里采用固定范围的分层粗网格，没有引入完整 clipmap 插件或运行时 HLOD 构建。

## 低雾排查和调整

原来 `BuildValleyFog` 只在整张地图的一条谷线附近枚举 9 个固定位置，玩家 140 米内才生成、最多同时 3 片。因此离开这条谷线后可能没有任何局部雾。丘陵材质密度为 `0.12`，Normandy 引用实例为 `0.5`；原来还使用包含辅助组件的 Actor bounds 缩放雾体。

排查中也追踪了 Normandy 的 `UseDistanceFields?` 分支：主材质默认开启，依赖 `DistanceToNearestSurface`，但实际引用的 `MI_VolumeFog_01A` 已覆盖为关闭。因此距离场不是本次缺雾的已确认原因。项目自有 `MI_ValleyLowFog` 现在也显式保持关闭，因为程序化 DynamicMesh 地面未生成供它使用的地形距离场。原包启用的 curl noise 保留；`Distance` 参数属于距离场分支，不是雾的相机可见距离。主要调整针对布置稀疏、密度偏低与雾体尺寸/地面衔接。

- 64 米网格中的确定性随机位置，优先河岸，其次谷线或局部低洼处，避开陡坡。
- 玩家 140 米内补充，180 米外回收，最多 4 片；每 0.5 秒更新一次、单次最多新增或回收 1 片。
- 每片约 28 × 20 × 3.6 米，中心高于地面 0.9 米，沿地面坡向旋转，使用实际网格 bounds 缩放。
- 默认密度 `0.32`，出现时约 1.5 秒淡入，远离时在 140–180 米区间淡出。
- 生成在 loading 阶段已经开始，并请求 PSO 预缓存；使用已有高度雾的体积雾通道。

未修改 Normandy 原始材质或蓝图。局部体积雾仍受 UE 的体积雾质量设置影响；本次未更改全局画质预设。

## 文件与资产恢复

- `Source/FPSGAME/WorldGeneration/TemperateHillsBackdrop.cpp/.h`：远景后台生成、遮罩、天气颜色。
- `TemperateHillsStreaming.cpp`：近远景衔接、loading 等待、低雾布置。
- `Tools/WorldGeneration/build_temperate_backdrop.py`：创建 `/Game/WorldGeneration/TemperateHills/Backdrop` 材质和默认纹理，更新既有 DataAsset 的远景引用和低雾密度。
- 保留当前草地、河流和岩石引用；脚本不打开或保存关卡。
- 修改前的自有资产备份与写入记录位于 `Saved/TemperateBackdrop`。Fab 二进制留在本地，不加入源码仓库。

用包含新字段的 Editor 模块运行作者脚本即可恢复本次资产接入。无需重新运行最早的丘陵全量作者脚本。

## 参考来源

本次为原创实现，借鉴成熟地形方案中“近处细、远处粗、固定几何预算”的结构：

- [CDLOD](https://github.com/fstrugar/CDLOD)：距离驱动的连续地形细节层级思路。
- [Terrain3D 架构](https://github.com/TokisanGames/Terrain3D/blob/main/doc/docs/system_architecture.md)：重复利用固定地形网格的思路；此处未移植 Godot 插件。
- [ProceduralLandscapeUE](https://github.com/MaximeDup/ProceduralLandscapeUE)：UE 地形 clipmap 参考，未安装其旧版插件。

本次没有复制以上项目源码，也没有引入付费素材。

## 交付边界

完成源码、材质作者脚本和本地资产接入。Editor 构建完成；Game 构建的丘陵源文件编译完成，但整体链接被并行开发文件 `Source/FPSGAME/Weapons/PhantomRearGripVisual.cpp:27` 的 C4458 编译错误阻塞，未修改该文件。作者命令行完成所有资产保存，但进程仍因工程原有 GameFeatureData 配置和 HTTP 8000 端口占用错误返回非零，不将其描述为命令行整体通过。

遵照用户规则，没有运行 PIE、游戏测试、性能采样、截图或视觉验收。外观与实际帧时间交由用户测试。重新启动 UE 编辑器后进入丘陵，才能使用更新后的原生模块与资源。
