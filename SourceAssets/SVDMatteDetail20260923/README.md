# SVD 哑光表面与弹匣细节修订

## 2026-09-23 整理后的当前入口

旧换弹导出已由 `SVDThumbUp20260923` 替代；当前模型与材质入口为 `SVDRefinedFinish20260923`。本目录的旧制作记录保留其历史日期与验收边界。已经移走的旧导出、自动备份及恢复快照位于 `trash/svd-superseded-20260923/SourceAssets/` 下的同名目录，原路径、散列及保留替代物见 [归档清单](../../Docs/AssetArchives/svd-superseded-20260923.json)。当前所需 Blend、脚本、参数与原素材仍保留；不要直接重跑旧导入覆盖用户已认可的抓握。新 checkout 的恢复方式见 [SVD 发布说明](../../Docs/Weapons/svd-publication-20260923.md)。

后续 PSO 接缝分区修复见 [PSOSeamRepair20260923](../PSOSeamRepair20260923/README.md)。本目录六份 Blend 已同步修正；最新主网格 FBX 和 PSO 图集位于该修复目录，不要重新导入本目录旧 FBX 覆盖它。

PSO 镜体和侧座的当前表面随后按用户要求在 [PSOMatteFinish20260923](../PSOMatteFinish20260923/README.md) 继续升级；本目录其余枪身及弹匣哑光层保持。

2026-09-23。按用户要求参考最新 `PKMLowpoly20260922/HandleFinish27` 的哑光表面和局部模型微调方法，承接 SVD 已完成的弹匣内腔与手部抓握修订。当前网格、材质与贴图已通过后台 commandlet 导入保存；未运行游戏、试听、验收渲染或额外测试。

## 弹匣

- 从 `SVDMagazineFit20260923/SVD_base_Editable.blend` 继续制作。只焊接弹匣外壳的位置重复点并恢复源角点法线，在局部硬边上制作 **0.18 mm、三段**微倒角；保留原冲压筋槽、轮廓、安装位置和机械骨骼。
- 沿原壳体的斜底面增加贴合的底板卷边，新增唇缘最低约低于原底面 **0.22 mm**，主体嵌入现有壳体，不在手部包握区域增加厚大凸件。
- 保留前一轮完成的口部厚度、内壁和下沉托弹板，将外壳、口部与底板组织到同一弹匣对象，全部刚性绑定原 `WPN_SOCKET_Magazine`。
- 仅弹匣改为独立打包 UV0，制作三张 **4096²** BaseColor、ORM、Normal。完整原结构法线从旧 UV 源材质与新倒角几何重烘焙到新图集，没有减弱整张结构法线、凭空升采样或给全枪加凹凸噪声。
- ORM 为 R=AO、G=Roughness、B=Metallic。颜色使用 sRGB BC7，ORM 线性 BC7，法线使用专用压缩与一次 OpenGL→UE 绿色通道翻转。
- 原弹匣外壳 4,936 面，新弹匣总计 13,721 个三角面，包含保留的内腔和新增底板。该增加服务于局部倒角及卷边，不修改全枪拓扑。
- 保持原材质槽身份。`SM_SVD_Magazine_001` 与 `SVD_InterfaceSteel` 在本枪骨骼网格上都接专用弹匣图集；独立安装座仍使用它自己的钢材和 UV。

## 哑光表面

复用 PKM 的表面反射方法，参数按 SVD 独立副本应用：

- 干燥涂层粗糙度限制在约 **0.56–0.80**，低幅度物理尺度细纹主要影响粗糙度。
- 保留原深色钢材和分区颜色，少量细划痕仅略微磨亮；微划痕强度为 0.30。亚像素涂层纹理按导数淡出，使用蒙皮前位置／法线并经 VertexInterpolator 传递，避免动作中纹理滑动。
- 金属度遮罩与原瞄具外壳遮罩共同限制处理区域；聚合物、橡胶、刻字、镜片、分划、内腔和钛色饰件保留原材料身份。没有修改 PKM 或跨枪共享母材质。
- 共 **30 对** SVD 私有干／湿表面，覆盖当前枪体与金属改造件；17 个附件网格完成材质重绑，几何和安装挂点不变。既有受保护的附件材料保持。
- 新湿材质保留哑光基础层，再叠加既有水膜和水珠，湿度为零时水珠归零。干湿映射合并进当前已被运行代码加载的 `Accessories20260923/DA_SVD_AttachmentWetMaterials`，保留表中其他条目。

## 当前资产与作者入口

- 活动骨骼网格路径保持 `/Game/Weapons/SVDDragunov20260922/Accessories20260923/SK_SVD_Modular`。
- 新贴图／材质：`/Game/Weapons/SVDDragunov20260922/MatteDetail20260923`。
- `SVD_MatteDetail_Editable.blend`：含源法线烘焙供体、精修弹匣和当前完整基础场景。
- `SVD_{base,vertical,canted,prism,angled}_Editable.blend`：五套已有动作场景同步新弹匣；没有重烘焙动画。后续几何制作优先从本目录继续，动作算法、参数仍参考 `SVDMagazineFit20260923`。
- `author_model.py`：局部倒角、底板、独立图集、完整结构法线重烘焙与模型 FBX。
- `MicroFinish.hlsl`、`MatteColor.hlsl`、`MatteRoughness.hlsl`：本枪运行哑光表面代码，来源为项目 PKM 作者算法。Blender 工作材质仅表达基础外观，运行微纹以这些 UE 节点为准。
- `import_finish.py`：新材质与贴图、干湿映射、附件绑定；`import_model.py`：精修主网格重导并按槽名恢复绑定。
- `run_job.ps1`：优先后台；已有可用编辑器时走现有批次互斥桥。无法连接或存在目标未保存冲突时保留现场。
- `Before/`：本次改动前的主网格、附件网格和 SVD 私有天气表，仅用于逐目标恢复。
- `finish_receipt.json`、`model_import_receipt.json`：逐项保存记录；`model_authoring.json`、`editable_sources.json`：作者输出记录。

本轮没有 C++ 修改，不需要原生构建。原骨架参考姿态、手臂权重、抓握动作、换弹时钟、音效、枪匠和武器数值保持；当前效果由用户实机测试，不将材质编译／保存等同于视觉验收。

## 来源

模型、原结构纹理与部分原色继续来自 LeroyCake 的 CC BY 4.0 SVD。本次是本地确定性几何和材质加工，没有引入 PKM 的几何、贴图或第三方录音；保留原作者署名。详见 `ThirdPartyNotices/SVD_DRAGUNOV.md`。
