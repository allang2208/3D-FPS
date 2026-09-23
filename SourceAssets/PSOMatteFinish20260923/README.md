# PSO 哑光材质升级（2026-09-23）

## 2026-09-23 整理后的当前入口

旧换弹导出已由 `SVDThumbUp20260923` 替代；当前模型与材质入口为 `SVDRefinedFinish20260923`。本目录的旧制作记录保留其历史日期与验收边界。已经移走的旧导出、自动备份及恢复快照位于 `trash/svd-superseded-20260923/SourceAssets/` 下的同名目录，原路径、散列及保留替代物见 [归档清单](../../Docs/AssetArchives/svd-superseded-20260923.json)。当前所需 Blend、脚本、参数与原素材仍保留；不要直接重跑旧导入覆盖用户已认可的抓握。新 checkout 的恢复方式见 [SVD 发布说明](../../Docs/Weapons/svd-publication-20260923.md)。

已完成后台导入保存：8 对干湿材质、1 张外壳分区遮罩、4 套运行网格材质绑定及2份现有天气映射表。实际保存回执 `import_receipt.json` 的 `completed=true`。未启动游戏或额外测试。

按用户要求，将刚完成的 SVD／PKM 表面处理方法应用到 PSO 镜体、接缝金属环、原侧座和各枪专用安装座。读取当前接缝修复后的资源，从现有材质复制专用版本；保留枪械 SKILL 的分区、宿主颜色、结构法线与干湿材质合同。

## 外观制作

- SVD 原有哑光层在私有副本内精修，不再次叠加同样的粗糙度处理。镜体底色向深灰枪钢低幅度收敛，混合权重 0.45；挂座保留略深的层次。
- AKM、A762、PKM 使用各自已经烘焙的主体涂层颜色，再增加与 SVD 相同的哑光反射处理，不套用另一把枪的贴图或替换跨枪母材质。
- 金属涂层粗糙度约 0.56–0.80，细划痕强度 0.24；细纹主要改变粗糙度，底色磨损幅度较低，并沿用原微纹的亚像素淡出。
- 完整保留原结构法线、AO、金属度和 UV。镜片的透明材料独立保留，橡胶和标记由原材质金属分区保护。
- 新增 4096² `T_PSO_ExteriorMask`，使用实际镜筒面朝向及原 UV0 制作，包含已经修复为不透明的接缝环。遮罩用于外壳涂层和外露雨水区域，避免镜筒内壁受到新划痕／雨滴处理。
- 8 对专用干湿材料：SVD 镜体／原侧座，以及 AKM、A762、PKM 各自镜体／安装座。湿润在新干材质之上叠加水膜和水珠，`WeaponWetness=0` 时返回干态。

## 接入

新材料与遮罩在 `/Game/Weapons/PSO1Russian20260923/MatteFinish20260923`。现有 SVD 骨骼网格和三套 PSO 静态网格仅重绑对应材质槽，不重新导入几何，也不修改槽名、槽序、骨骼、光心、安装位置或镜片材料。

两份既有运行天气表分别追加新干湿映射：

- SVD：`/Game/Weapons/SVDDragunov20260922/Accessories20260923/DA_SVD_AttachmentWetMaterials`
- 三款改造件：`/Game/Weapons/PSO1Russian20260923/DA_PSO1_WetMaterials`

`bake_exterior.py` 为遮罩作者入口，`MicroFinish.hlsl`／`MatteRoughness.hlsl` 复用前轮 SVD 方法，`PSOColor.hlsl` 控制 PSO 表面色调。UE 材质图与源 HLSL 均可继续编辑；Blender 工作材质不替代最终 UE 表面图。

`run_job.ps1 -Script import_finish.py` 通过后台 commandlet 或已有编辑器互斥批次接入；`Before/` 保存改动前的网格和天气表。实际完成状态以 `import_receipt.json` 中逐资产的保存记录及 `completed` 为准。

本轮仅制作、导入、必要材质编译和保存；不进行额外检查、渲染或游戏测试，效果由用户实机确认。
