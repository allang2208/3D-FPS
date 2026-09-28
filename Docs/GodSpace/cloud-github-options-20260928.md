# 主神空间云海：GitHub 方案调研

2026-09-28。用户反馈现有云海粗糙，要求查找 GitHub 实现。本轮只读取项目云形代码和外部资料；没有修改云材质、地图、光照或启动应用。

## 当前实现的问题与判断边界

用户截图中的云体呈大面积平缓覆盖，边缘有明显颗粒，缺少厚薄错落的积云轮廓。上一轮颜色补偿没有达到目标，应停止把调色当作主要解决办法。

当前 `CloudSeaDensity.hlsl` 将主体噪声映射到 0.57–0.95 的正值区间，再乘高度剖面；主体噪声不能直接切开云体。云顶噪声位移限制为层厚的 ±0.07，在 700 m 层厚下即 ±49 m，远处还逐步消失。这些公式支持“云形过平”的判断。截图里的颗粒可能包含体积采样、时间重建或纹理频率问题，仅凭静态图不能分离其各自贡献，不能声称换贴图就一定解决。

## 候选比较

| 项目 | 已核对内容 | 对当前 UE 工程的取舍 |
| --- | --- | --- |
| [Takram three-geospatial / clouds](https://github.com/takram-design-engineering/three-geospatial/tree/main/packages/clouds) | Three.js/GLSL；云包为 MIT，并列出第三方声明；具备云形、细节侵蚀、光照及时间上采样实现 | 推荐作为云形算法来源，需移植到 HLSL/UE 材质，不能直接安装进 UE |
| [Prograda / Skybolt](https://github.com/Prograda/Skybolt) | C++/OpenSceneGraph；MPL-2.0；行星云层与跨距离渲染，当前源码含时间上采样 | 适合借鉴俯视云海和远景层次；整套引擎接入成本高，不作为 UE 插件导入 |
| [CorvaeOboro / clouds_unreal](https://github.com/CorvaeOboro/clouds_unreal) | 项目声明 CC0；VDB 体积纹理与可放置云蓝图；UE5 工程实际声明 5.0，启用 SparseVolumetrics 与 Volumetrics | 可参考局部云团制作；尚无本工程 UE 5.8 兼容证据。重复大量局部射线步进云体覆盖全视野有额外重叠成本，不作为云海主体首选 |
| [mxcop / vapor](https://github.com/mxcop/vapor) | README 标注 UE 5.6 开发中；页面显示已于 2026-08-10 归档；仓库未找到自身完整许可，只有对上游模板 MIT 的致谢 | 暂不作为正式接入来源。源码公开不等于整仓已有可复用许可 |

许可证依据：[Takram 云包 LICENSE](https://github.com/takram-design-engineering/three-geospatial/blob/main/packages/clouds/LICENSE)、[Skybolt License.txt](https://github.com/Prograda/Skybolt/blob/master/License.txt)、[clouds_unreal LICENSE](https://github.com/CorvaeOboro/clouds_unreal/blob/master/LICENSE)。Corvae 版本依据：[CLOUDS_UNREAL5.uproject](https://github.com/CorvaeOboro/clouds_unreal/blob/master/CLOUDS_UNREAL5/CLOUDS_UNREAL5.uproject)。研究时未下载或集成这些库。

## 推荐实施路线

以 Takram 的密度建模为参考，替换现有简化云形；保留 UE 原生 VolumetricCloud 的采样、光照、深度合成与时间重建，不叠加另一个全屏云渲染器。核心依据是 [clouds.glsl](https://github.com/takram-design-engineering/three-geospatial/blob/main/packages/clouds/src/shaders/clouds.glsl) 中的高度整形、天气覆盖及三维侵蚀，以及 [clouds.frag](https://github.com/takram-design-engineering/three-geospatial/blob/main/packages/clouds/src/shaders/clouds.frag) 的光照/步进分工。Takram 自身仍列有时间上采样拖影等限制，因此参考其密度模型不等于全套照搬或保证达到其示例效果。

1. **云形**：高度剖面形成圆拱云顶，低频三维噪声真正切出云团与空隙，再用细节噪声软化边缘。去掉强制保留厚膜的主体下限。沿用现有天气图、体积噪声和天气驱动；先按现有纹理真实通道语义适配，不能直接照搬参考纹理的通道假设。
2. **覆盖**：80% 是整体布局目标，不能让每个局部都接近均匀密实。保留成组云团、不同宽度的露海通道。三维侵蚀会改变最终可见覆盖，不能继续把二维天气图阈值当作最终画面 80% 已达成。
3. **近远层次**：近处保留云团轮廓、侧壁和少量细节；远处减少细节频率而保留宏观起伏，通过连续密度与大气透视融合。避免将三维形状在固定距离完全压成平面，也避免再出现独立贴图硬接缝。
4. **光照**：撤回本轮试用的云本色衰减与发光补色分支，以原生散射、自阴影和天空环境光建立白灰/灰蓝层次，再限定黄昏暖色。自然度应来自形状与光照关系。
5. **性能**：先保留单层云、现有纹理及近中远细节分级；空区跳过、远距降频，沿 UE 的时间重建处理颗粒。必要的重建质量调整有成本，不预先承诺零开销或固定 FPS。对于从云层上方俯看的场景，不直接用地面仰视的低成本云阴影预设替代。

UE 渲染方式依据：[Epic Volumetric Cloud 文档](https://dev.epicgames.com/documentation/unreal-engine/volumetric-cloud-component-in-unreal-engine)。跨尺度密度与远景参考：[Skybolt 作者说明](https://prograda.com/2021/07/28/rendering-planetwide-volumetric-clouds-in-skybolt/)。该作者说明发表于 2021 年；当前仓库已存在 [CloudsTemporalUpscaling.cpp](https://github.com/Prograda/Skybolt/blob/master/src/Skybolt/SkyboltVis/Renderable/Clouds/CloudsTemporalUpscaling.cpp)，不可再把旧文章的“未来支持跨帧”当作当前缺失功能。

作者效果示例：[Takram Fuji](https://media.githubusercontent.com/media/takram-design-engineering/three-geospatial/main/packages/clouds/docs/fuji.jpg)，仅为外部项目参考，不是 FPSGAME 预览或效果承诺。后续实施应先制作独立候选；用户若明确要求画面预览，再做指定范围的实际引擎预览。本轮没有启动测试、渲染或性能采样。
