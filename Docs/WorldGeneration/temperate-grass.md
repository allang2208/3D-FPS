# 温带丘陵连续草地

2026-09-13，UE 5.8.2。接入现有温带丘陵与传送门，不重建地图或更换河流地表。

## 素材与分层

新增资产为 Project Nature 的 [temperate Vegetation: optimized Grass Library](https://www.fab.com/listings/8b68642e-35f4-438e-82b4-799fc2228303)，本机已导入 `/Game/PN_GrassLibrary`。从中选取 12 个网格，复制到 `/Game/WorldGeneration/TemperateHills/Grass`，保留原网格的四档 LOD、顶点颜色及 Pivot Painter UV。不同高度的草与草本点缀分为两层：

| 层 | 源网格名称 |
|---|---|
| 连续覆盖 | `lowGrass_01_02_SM`、`lowGrass_02_02_SM`、`lowGrass_04_03_SM`、`lowGrass_08_02_SM`、`lowGrass_09_02_SM`、`grass_01_08_mesh` |
| 成簇点缀 | `grass_03_08_mesh`、`grass_05_03_mesh`、`grass_07_01_mesh`、`grass_09_02_mesh`、`grass_11_02_mesh`、`grass_12_05_mesh` |

旧 Normandy 草列表由这两组替代；Normandy 灌木、原黑杨、坡石与已接入的河流资源继续使用。没有接入草包的演示地图、角色蓝图或 Landscape 材质。

## 生成规则

- 底层候选间距从 145 cm 调到 55 cm，基础概率设为 0.94，统一缩放范围 0.98–1.24。该概率还会乘草甸、树冠、坡度与边缘权重，并非最终地表覆盖率。
- 点缀使用独立的 180 cm 候选网格，基础概率 0.5，缩放 0.8–1.15，只在较密的草甸区域成簇出现。低草覆盖连续过渡，高草分布有疏密。
- 约 36 m 尺度的噪声控制疏密，40 m 的物种区域场通过平滑权重混合相邻区域。附近草共享少数主导草型，避免每株从全库等概率抽取的杂乱感。
- 林下适当变疏。保留道路中线两侧 240 cm 的空带，向外 180 cm 内逐渐恢复底草；点缀用更宽过渡。河滩遮罩超过 0.08 不生成草，其外缘逐渐变疏；陡坡及树干周围 100 cm 继续避让。
- 坐标、种子和层的盐值决定候选与物种；采用半开区间归属，区块及分批边界不改变候选，也不重复生成。已有世界无需清除种子存档，重新进入后更新草地布局。

## 加载和渲染预算

- 复用草层的 16 m PCG 网格，将每次点生成调用限制为 16 m × 2 m 条带；上下文保留中间结果，后续调度继续。此处理是主线程分批计算，资源加载仍走现有异步队列。
- 草的生成半径 60 m，清理半径 78 m；材质实例距离淡出从 35 m 到 50 m，给生成保留 10 m 提前量。不会一次实例化整个 1 km 世界。
- 两组共 12 个软引用均在 loading 草资源阶段加载，加入现有逐个网格的 PSO/显示预热及 GameInstance 资源保留流程。草使用 PCG 静态网格实例，无碰撞、不投影。
- 自有草材质复制原主材质并增加 PerInstanceFadeAmount 遮罩淡出。保留第一级逐叶风动，实例关闭第二、三级风动和演示角色的三个弯折等级；不新增角色追踪器。颜色亮度 0.92、饱和度 0.9，衔接丘陵地表。

这些是实现参数，没有进行实机耗时或帧率测试。

## 调整与恢复

配置位于 `/Game/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming` 的 Grass 分类，可调 `GrassSpacingCm`、`GrassCoverage`、`GrassAccentSpacingCm`、`GrassAccentCoverage` 及两组网格。间距越小，实例数按间距平方的反比增加。

作者脚本为 `Tools/WorldGeneration/build_temperate_grass.py`，在编译新 Editor 模块后以 Python commandlet 执行。只写自有草副本、草 PCG 图的描述符以及该配置的草字段，不覆盖地表、河流、树木或地图。运行前自动把原草图和配置备份到 `Saved/TemperateGrass/BeforeGrass-*`。若从头恢复工程，应按 hills → streaming → rivers → grass 顺序执行作者脚本，后两步保留前面的其他字段。

二进制资产保留本机，Git 仅发布源码、作者脚本与说明；复建需先恢复已取得的 Fab 草包和原丘陵依赖。

## 交付状态

完成代码及本地资源接入、Editor/Game 必要构建。没有运行 PIE、游戏回归、截图或视觉验收，由用户重启编辑器后进入温带丘陵测试。作者 commandlet 的资源保存完成；进程仍可能因项目已有的 GameFeatureData AssetManager 配置错误返回 1，该返回值不记作测试通过。
