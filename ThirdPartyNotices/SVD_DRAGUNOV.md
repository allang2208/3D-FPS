# SVD（德拉贡诺夫狙击步枪）第三方素材声明

- **作品**：SVD (Dragunov sniper rifle)
- **作者**：LeroyCake（<https://sketchfab.com/leroycake>）
- **来源**：<https://sketchfab.com/3d-models/svd-dragunov-sniper-rifle-2ac78fb5a0eb40f5a02a5b0a9f566abf>
- **许可**：**CC BY 4.0** — <https://creativecommons.org/licenses/by/4.0/>（允许商用，必须署名）
- **获取日期**：2026-09-22

要求的署名文字：

> "SVD (Dragunov sniper rifle)" by LeroyCake, licensed under CC BY 4.0.
> Source: https://sketchfab.com/3d-models/svd-dragunov-sniper-rifle-2ac78fb5a0eb40f5a02a5b0a9f566abf

## 用途与状态

源静态件位于 `/Game/Weapons/SVDDragunov20260922/{Meshes,Materials,Textures}`：枪体、弹匣、扳机、拉机柄、保险杆、镜体、镜座、镜片共八件。

2026-09-23 的运行版本位于 `/Game/Weapons/SVDDragunov20260922/Complete20260923`，注册为 `ue_svd`，已接入共享 Manny 手臂、专用动作、原厂 4 倍镜、物品数据和图标。实机验收状态见 [开发记录](../Docs/Weapons/svd-completion-20260923.md)。

## 修改说明

等比缩放到实枪全长 1.225 m 并把枪口转向项目约定方向（Blender -Y → UE +X）、各部件共用整枪原点、按测量区域**重组既有壳体**分出弹匣／扳机／拉机柄／保险杆（不裁切表面，面数总和与源一致）、贴图保持 4096（法线转无损 PNG）、在 UE 内重建材质（BaseColor × AO × Tint / Normal 翻转绿通道 / Roughness × Scale / Metallic）、关闭 Nanite、碰撞用三角面。未修改网格拓扑、UV 或贴图内容，未重新烘焙。逐件散列与源结构见 `SourceAssets/SVDDragunov20260922/PROVENANCE.md`。


## 2026-09-23 后续改动

在保留原八件 UV 和贴图的前提下重新装配刚性绑定，适配项目共享 Manny 手臂与动作，重定枪口/抛壳/瞄准标记，另制小型枪机载体和透明镜片材质。新载体是新增几何，不属于“原八件未改拓扑”的范围。原作者的署名和 CC BY 4.0 许可继续保留。

本枪设计枪声由已登记的 CC0 Free Firearm AK-47 / AR-15 源音加工，原音、散列与改动记录见 `SourceAssets/SVDCompletion20260923/audio_provenance.json`；它不是 SVD 实枪录音。机械音和共享手臂/动作沿用项目已有资产及其各自来源记录，不将这些第三方动作另行标为 CC0。

2026-09-23 视频音效更新：用户指定从 127毫米的《三角洲音效对比 PSG-1&SR25&SVD》（<https://www.bilibili.com/video/BV15MqbBcEQh/>）1:50 开始提取。新增一段独立单发和五段换弹／拉栓机械音，保存于 `/Game/Weapons/SVDDragunov20260922/VideoAudio20260923`，供 SVD 普通开火和机械事件使用；此前 CC0 设计声保留为历史来源。该视频音效是用户指定的本机提取，第三方权利保留，**没有确立公开再分发许可，不属于 CC0 或模型的 CC BY 4.0**。源为 AAC 有损音轨；PCM WAV 导出不构成无损原始录音，未独立确认实枪录音来源。时间点、散列和处理记录见 `SourceAssets/SVDVideoAudio20260923/provenance.json`。


2026-09-23 UV 兼容修正：GLB 内嵌纹理相对作者原始 4K 图像进行了垂直翻转；本项目原八个派生件的 UV0 以 `V = 1 - V` 匹配原始贴图。源 GLB、原始图像、几何位置及原作者署名保持不变。详细证据见 `SourceAssets/SVDCompletion20260923/UVRepair/texture_compare.json`。

2026-09-23 表面重制：按枪钢、聚合物、橡胶、贴腮垫和镜筒分区，制作四张新的 4K BaseColor／ORM 派生图，并更新七个枪械材质实例。保留原结构法线、部分原色及刻字细节；AO 改为独立材质输入，不再直接乘进底色。几何与已修正 UV 不变。可编辑源及制作记录见 `SourceAssets/SVDSurface20260923/README.md`；本次材质派生继续保留 LeroyCake 署名与 CC BY 4.0 来源。

2026-09-23 PSO-1 跨枪改造件：由已修正 UV 的镜体、夹具和镜片派生 AKM、A762、PKM 三套适配，新增各枪型侧座几何、金属区域涂层 UV、六张 4K BaseColor／ORM、干湿材质和三个透明 UI 图标，保留原结构法线与非金属细节。正式内容位于 `/Game/Weapons/PSO1Russian20260923`，可编辑源和制作记录见 `SourceAssets/PSO1Russian20260923/README.md`。这些派生镜体和图标继续保留 LeroyCake 的 CC BY 4.0 署名；其它既有枪械涂层参考沿用各自来源记录，不改变其许可。

2026-09-23 SVD 通用改造接入：在保留原枪 UV、几何、绑定和表面材质的前提下，为原消焰器增加独立材质分区；原 PSO 分区可随通用瞄具安装而隐藏、卸下后恢复。新增本枪侧桥／底座／战术侧座、配件涂层及原厂部件 UI 图标，通用配件和共享动作沿用各自既有来源。派生内容位于 `/Game/Weapons/SVDDragunov20260922/Accessories20260923`，作者源见 `SourceAssets/SVDAttachments20260923/README.md`。SVD 派生模型和图标继续保留上述 LeroyCake / CC BY 4.0 署名。

2026-09-23 哑光与弹匣精修：在现用 SVD 弹匣外壳上增加局部微倒角与底板卷边，保留口部内腔，重排弹匣专用 UV0 并将完整原结构法线与分区颜色烘焙到三张新 4K 贴图。枪体和金属附件使用本枪私有哑光干湿材质；算法参考项目内 PKM 表面制作，不引入 PKM 的第三方模型或纹理。作者源为 `SourceAssets/SVDMatteDetail20260923`。这些 SVD 模型／贴图派生继续保留 LeroyCake 的 CC BY 4.0 署名。

2026-09-23 最终涂层／接口：`SourceAssets/SVDRefinedFinish20260923` 参考本机 A762 的缎面处理，复制参考细纹至 SVD 私有纹理，保留原 SVD 结构法线、标记和材质分区；新增前握把鞍座、瞄具支架及 PSO 固定螺钉细节。SVD 原模型派生继续保留 LeroyCake / CC BY 4.0 署名，参考材质及共享手臂沿用其各自来源，不由此重新授权。此次 Git 仅发布代码、配方及文字来源，所有模型、贴图、动作、音频与 UE 二进制留在本机。
