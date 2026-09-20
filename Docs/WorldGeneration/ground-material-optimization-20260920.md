# 丘陵地表材质优化（2026-09-20）

> 后续地面模糊与约 180 秒材质等待的处理见 [旷野地面加载诊断](ground-loading-diagnosis-20260920.md)。材质资产已接入；加载逻辑现修正为等待实际可渲染材质、共享高清贴图和附近约 96 m 地形，远处地形进入后继续流送。构建与实测状态以诊断文档为准。

本版在四层地表的基础上，修正凹凸采样与显示纹理错位、零权重法线仍改变表面的问题，并加入近景交点细化、干壳层随机铺贴和遮罩外跳过采样。作者脚本仍为 `Tools/WorldGeneration/build_hills_ground_v2.py`。

## 接入范围

- `/Game/WorldGeneration/TemperateHills/M_TemperateGround`：四层丘陵地面。
- `/Game/WorldGeneration/TemperateHills/PebbleShore/M_PebbleShoreGround`：丘陵地面加河岸，仍为 `DA_TemperateHillsStreaming.GroundMaterial` 实际引用。
- 顶点色 R=河岸、G=湿润、B=卵石覆盖以及天气 `Wetness` 参数沿用。未修改地形网格、碰撞、采集、PCG 或地貌破坏代码。
- 在当前 UE 编辑器进程内执行作者脚本，重建并保存上述材质，不启动地图、PIE 或独立 commandlet。制作时原资产副本写入 `Saved/GroundMaterialOptimization20260920/BeforeAuthoring-<时间>/`；本次两份旧快照现已移到 `trash/hills-ground-superseded-20260920`，见 [归档清单](../AssetArchives/hills-ground-20260920.json)。

## 本次实现

### 高度图与表面使用同一套投影

旧版在 3.4 m 的共享坐标直接采样土和砾石高度，显示端却分别使用 3.0 m、2.1 m 和不同偏移，因此凹凸位置可能与可见石子或土块不一致。

现在沿世界 XY 投影步进，各层使用与最终颜色、法线相同的尺度和偏移；草、土、砾石高度共同参与。每个步进位置重新计算同一套高度混合权重。干壳仍没有源高度图，使用固定中间高度，并按其覆盖权重降低整体视差深度，避免纯干壳被其它层高度推着移动。

所有纹理采样的梯度从未位移的世界投影取得，在分支与循环外计算，避免把视差交点跳动直接用于 mip 选择。

### 粗步进后细化最后一个区间

丘陵和河岸都先执行有上限的粗步进，找到交点后只细分最后一个区间，再在最后两个采样点间插值。远处减少粗步数和细分次数，已有距离、贴地视角渐隐仍保留。

这能提高最终交点定位精度，但不能保证较少粗步数捕捉到每一个很窄的凸起。`GroundReliefSteps`、`PebbleReliefSteps` 可分别调节；新增细分参数不是整段射线都重复采样。

### 层覆盖法线与细颗粒法线分开处理

四层代表不同表面覆盖，先按高度混合权重对完整 XYZ 法线加权归一化。覆盖权重为零时该层不再影响结果。细颗粒法线先向平面法线渐隐，再用 RNM 重定向叠加；细节强度或距离渐隐为零时，细节层不再改变基底法线。

### 干壳层随机铺贴

在共享三角格点上取三个确定性随机平移样本，并用相邻格点共享的权重混合。颜色、法线、粗糙度使用相同平移和权重，保留图案对齐；不随机旋转，避免遗漏切线法线方向转换。对权重做四次方锐化以减轻交界混合发灰。

只启用在重复感较强且没有高度图的干壳层，避免给每一个 POM 高度采样增加三倍读取。`GroundDryStochasticStrength=0` 可恢复规则铺贴。该实现借鉴三角格点随机平铺思路，没有移植直方图保持、完整 hex tiling 管线或虚拟纹理缓存。

### 在读取贴图之前跳过无贡献区域

纹理对象传入 Custom 节点，分支位于实际 `Texture2DSampleGrad` 之前：

- 河岸遮罩为 0 时跳过河岸贴图读取。
- 河岸完全覆盖处跳过丘陵各层贴图；覆盖层权重为 0 时跳过对应层。
- 细颗粒已完全淡出或强度为 0 时跳过细节贴图。
- 视差深度为 0 或距离已完全淡出时，直接返回普通投影坐标。

法线采样使用 UE 的 `UnpackNormalMap`，纹理对象保留按压缩设置选择的采样器类型；采用 UE shared-wrap sampler，避免新增采样节点各占独立采样器。边界仍保留双侧混合。GPU 是否实际降低耗时取决于像素分布、分支一致性和编译器；本次没有测量帧率。

## 主要参数

| 参数 | 当前默认 | 含义 |
| --- | --- | --- |
| `GroundReliefDepthCm` | 9 | 丘陵视差深度；0 关闭 |
| `GroundReliefSteps` | 8 | 丘陵粗步数设置，上限 24；按视角和距离降低 |
| `GroundReliefRefineSteps` | 3 | 丘陵最后区间细分，1 关闭细分，上限 8 |
| `GroundReliefFadeM` | 7 | 7 m 内满强度，16.1 m 完全淡出 |
| `PebbleReliefDepthCm` | 5 | 河岸视差深度；0 关闭 |
| `PebbleReliefSteps` | 12 | 河岸粗步数设置，上限 24；按视角和距离降低 |
| `PebbleReliefRefineSteps` | 3 | 河岸最后区间细分，1 关闭细分，上限 8 |
| `GroundDryStochasticStrength` | 1 | 干壳随机平移强度，0 恢复普通采样 |
| `GroundDetailStrength` | 0.5 | 细颗粒强度；0 跳过细节纹理读取 |

河岸视差仍在 9–18 m 渐隐；其它层尺度、颜色宏观变化、湿润粗糙度与 AO 参数沿用基线。随机干壳的三套贴图各从一次采样增加到三次；丘陵步进也增加了草层高度读取。因此本次优先修正画面一致性，并减少无贡献区域开销，不宣称总耗时或帧率已改善。

## 参考来源与借鉴边界

- [a-riccardi/shader-toy：ParallaxOcclusionMapping.cginc](https://github.com/a-riccardi/shader-toy/blob/master/ShaderToy/Assets/Shaders/ParallaxOcclusionMapping.cginc)，[MIT 许可证](https://github.com/a-riccardi/shader-toy/blob/master/LICENSE)：借鉴 Contact Refinement 的最后区间细化。此处为适配 UE Custom 节点、多层世界投影和现有河岸遮罩重写的实现。
- [mmikk/hextile-demo](https://github.com/mmikk/hextile-demo)，[MIT 许可证](https://github.com/mmikk/hextile-demo/blob/main/LICENSE)：借鉴三角格点共享样本、随机变换及一致权重的思路。本次只实现随机平移与权重锐化，未复制整套示例或其贴图资产。
- [WickedEngine terrainVirtualTextureUpdateCS.hlsl](https://github.com/turanszkij/WickedEngine/blob/master/WickedEngine/shaders/terrainVirtualTextureUpdateCS.hlsl)：借鉴在纹理读取前跳过零贡献层的组织方式。没有移植其虚拟纹理系统。
- [Self Shadow：Blending in Detail](https://blog.selfshadow.com/publications/blending-in-detail/)：RNM 法线重定向的算法依据，用于将细节叠加到已混合的基底表面。

## 交付边界

2026-09-20 00:09 在当前编辑器执行完成，远程作者命令返回 `success=True`，两份材质均已保存；丘陵基础图为 91 个表达式，含河岸版本为 130 个表达式，数据资产继续引用含河岸版本。作者调用的 `recompile_material` 未返回错误。这里只记录资产制作与接入结果，不代表画面或性能验收。

必要的材质图生成、着色器编译和资产保存由作者脚本执行，结果写入 `Saved/GroundMaterialOptimization20260920/authoring.json`。本次没有运行额外检查脚本、离线校验、PIE、截图、实机验收或性能测试，由用户测试实际观感。

该效果仍是材质视差，不能改变轮廓、碰撞或脚底实际高度；真实石头的轮廓继续由现有 `GroundDebris` 和河岸卵石网格承担。干壳缺少真实高度图的限制仍然存在。
