# M-07 碎片反馈后的 V02 修订

日期：2026-10-01。宿主：`D:/FPS3D/FPSGAME`。

**后续状态（2026-10-02）：用户已否定本版的整体模型，指出重复手部、肩肘扭曲和步行僵硬。[V03 连续人体与动作修订](BlindSupplicantM07AnatomyV03.md) 已重做并保存，当前 AI/F6 蓝图使用 V03。下方为 V02 制作历史，不能作为已认可成品。**

## 当前状态

用户已否定 V01：游戏中鳃膜被拉成长三角片，铺满场景。此前的资产保存、构建及 F6 注册不代表模型质量合格。原始 Meshy GLB、旧制作源和失败版 UE 包保留，用于追溯。

V02 源模型、连续膜片、曲面代理、贴图图集和 FBX 已保存，必要的 Editor／Game 后台构建及实际后台导入、资产保存已完成。最终显示资产为 `SK_M07_ContinuousV02`，现有 `BP_BlindSupplicantM07`、`PA_M07` 和 12 个身体动作的预览模型引用均已保存。最终回执位于 `SourceAssets/BlindSupplicantM07Meshy20261001/Authoring/FragmentRepairV02/ue_fragment_repair_delivery.json`；不再处于等待退出 PIE 或等待导入的状态。

旧 `SK_M07` 的 V02 重导入保留了错误的米制网格／根骨尺度 1，而物理来源是厘米网格／根骨尺度 100；该次显示膜全部回退到蒙皮，保留为失败记录。最终从 FBX 导入新包 `SK_M07_ContinuousV02`，保存正确厘米坐标和根骨参考尺度 100，并按同一参考帧重建、复用现有身体碰撞资产。本轮没有运行游戏、布料模拟、截图或渲染验收，构建与保存完成不代表视觉合格。

## 修改范围

- 保留 Meshy 原头部、装具、暴露身体表面和身体 UV。主体权重按身体、左右侧和各自手指链限定，补体使用骨段轴向伸长。
- 移除旧自动分区中没有对应模拟表面支撑的膜片碎岛。旧 joined surface 没有可靠的六片切缝，因此六片膜为依据原轮廓、深度带和肩背连接重建的连续叶形几何。
- 每片显示膜 2,275 顶点，对应单独曲面代理 611 顶点；六片显示膜共 13,650 顶点，物理来源共 3,666 顶点、6,624 三角形。代理分别沿各自深度带构建，保留六个物理岛；不再把多个叠层的深度平均成一个面。
- 六片膜在 Blender 中分别可编辑，UE 中共用 `M07_Gills` 材质及一个显示 section，绑定到一个包含六岛的衣物资产。已写入片间自碰撞与身体碰撞引用；实际避让效果尚未运行确认。
- 肩背固定带与主体使用一致的身体骨权重，自由区域逐渐转入原有鳃骨链。保留 Blender 源的 81 骨参考姿态及 12 个动作；修正 UE 旧重导入造成的根骨参考尺度丢失。
- 新膜片使用连续 3×2 UV 图集和单独 PBR 图，身体继续使用原身体贴图。

## 绑定修正

旧逐片绑定入口临时替换整个资产的 PhysicalMeshData，父类重新计算 ReferenceBoneIndex 后只还原物理网格，留下最后一片的参考骨骼。此副作用已修正，legacy 路线同时恢复 LOD map。

V02 使用完整六岛物理网格进行原生绑定，始终保留完整参考骨骼空间，最终回执记录参考骨为 `spine_05`。显示顶点按鳃骨权重确定所属膜片，物理三角形按制作岛标签过滤；肩背固定点保留身体蒙皮。位置、法线端点和切线端点在同一片代理中拟合，不能稳定拟合的局部点使用原蒙皮。单资产内保留六岛的同片捕获映射，此路线不手工累加粒子索引偏移。

ReferenceBoneIndex 覆盖是源码中确定的错误，旧分区、代理覆盖和权重也存在问题；尚未通过运行画面确定哪项因素分别贡献了截图中的长三角片。

必要的制作绑定记录还暴露了 UE 重导入的 100 倍单位错配：显示顶点 `Z=2.555`，物理来源使用厘米；显示根骨 scale 为 1，来源根骨 scale 为 100。由此产生上百倍重心系数，全部自由顶点被回退成蒙皮。新包从 FBX 直接导入正确厘米坐标，绑定入口要求两套根骨尺度一致，并把实际布料驱动／蒙皮顶点数写入制作回执；零布料驱动点会使作者化失败。

布料身体碰撞复用按新参考帧重建并保存的现有 `PA_M07`，回执记录 16 个身体物理体和 15 个约束。身体作者化入口按骨骼参考缩放换算局部胶囊尺寸，避免把厘米半径直接写入缩放为 100 的骨骼。

## 实际保存回执

以下为后台制作保存结果，属于作者化数据，不是运行测试结果。

| 项目 | 实际记录 |
| --- | --- |
| 显示资产与根骨参考尺度 | `SK_M07_ContinuousV02`；`X=100 Y=100 Z=100` |
| 衣物资产 | `SK_M07_ContinuousV02:M07_ContinuousGills_V02_0`，一个资产、六个物理岛、一个显示 section |
| 布料捕获的显示顶点 | 12,524 |
| 保留原蒙皮的显示顶点 | 1,126 |
| 模拟顶点／三角形 | 3,666／6,624 |
| 固定顶点／最大位移 | 286／8 cm |
| 身体碰撞 | 复用并保存 `PA_M07`，16 个物理体、15 个约束 |
| Editor 构建 | `Succeeded`；`Saved/BuildEditor/m07-FPSGAMEEditor-20261001-234118.log` |
| Game 构建 | `Succeeded`；`Saved/BuildEditor/m07-FPSGAME-20261001-234145.log` |
| 实际后台导入 | `Saved/Logs/M07Import-20261001-234940.log`，末尾记录 `Python script executed successfully` |

现有角色蓝图已指向新显示资产；12 个身体动作的预览模型引用已更新，动作轨道和共用 `SK_M07_Skeleton` 保留。回执中的 `saved=true`、`runtime_tested=false` 和 `visual_tested=false` 分别记录保存完成与未测试状态。

## 文件与接入

制作目录：`SourceAssets/BlindSupplicantM07Meshy20261001/Authoring/FragmentRepairV02/`。

| 文件 | 内容 |
| --- | --- |
| `M07_Separated_Master_V02.blend` | 主体、六片可编辑连续膜、曲面代理与原参考骨架 |
| `SK_M07_Display_V02.fbx` | 身体与显示膜 |
| `SK_M07_ClothBuildSource_V02.fbx` | 显示网格及完整六岛物理来源 |
| `cloth_ue_manifest_v02.json` | 代理顶点、固定带、位移预算、岛身份及身体胶囊 |
| `source_repair.json` | 几何重建、权重、图集与未验收状态 |
| `Textures/M07_Gills_V02_*.png` | 新膜片 BaseColor、Roughness、Metallic、Normal 图集 |
| `ue_fragment_repair_delivery.json` | 最终厘米参考帧导入、布料捕获、身体碰撞和资产保存结果 |

制作脚本：`Tools/BlindSupplicantM07/repair_source_v02.py`。
导入脚本：`Tools/BlindSupplicantM07/import_fragment_repair_v02.py`。
最终正确参考帧导入脚本：`Tools/BlindSupplicantM07/import_unified_frame_v02.py`。
原生作者化：`BlindSupplicantAuthoring.cpp`、`M07InteractingClothingAsset.cpp`。

最终显示引用已保存为 `/Game/Monsters/BlindSupplicantM07/SK_M07_ContinuousV02`，角色仍使用 `/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07`；共享 AI、受击／布娃娃、导航和 F6「盲祷者 M-07」入口保留。旧 `SK_M07` 留作失败版记录。

## 待用户观察

由用户自行打开 UE，在 F6「怪物生成」中选择「盲祷者 M-07」并重新生成角色观察新资产。六片重建膜的轮廓、肩背连接、图集采样、长肢体变形和布料摆动均未获用户认可。膜片是原造型参考下的几何重建，不能称为对原高模的精确自动切分；本轮没有运行证明旧截图中的长三角片已经消失，保存结果不等于运行或视觉验收通过。
