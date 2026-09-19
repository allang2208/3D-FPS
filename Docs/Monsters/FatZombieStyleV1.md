# 胖子僵尸材质风格样板 V1

日期：2026-09-19。阶段：第一只怪物的材质样板，交由用户在 F6 生成后判断；不是已获认可的全怪物美术标准。

## 外观目标

保留原有大腹、细肢、破布和角色轮廓。将黄绿大色块调整为低饱和灰绿、灰褐皮肤，腹部用局部炎症、细弱血管与脓包表达肿胀；分别处理暴露组织、湿脓液和干痂的颜色、粗糙度及微小起伏。

材质分区从原贴图的肤色范围提取，并以原模型静止姿态坐标补充不规则局部损伤。原来的黄色区域作为病变分布依据，不直接保留整片金黄色。皮肤与破布采用不同的粗糙度范围；眼部、牙齿与布料不覆盖为统一皮肤。

本轮不修改网格、UV、骨架、蒙皮、动画、碰撞、战斗数值或 AI。继承原有 F6 胖子入口，通过当前 SkeletalMesh 的单一材质槽接入。

## 资源和重建入口

- 可编辑节点材质源：`SourceAssets/FatZombieStyleV1/FatZombie_StyleV1_Authoring.blend`。
- 参数：`SourceAssets/FatZombieStyleV1/style_parameters.json`。颜色为线性 RGB，凹凸幅度以米计。
- 烘焙：`Tools/FatZombie/author_style_sample.py`，用 Blender 5.1 后台运行。只烘焙材质贴图，不生成预览。
- UE 导入：`Tools/FatZombie/install_style_sample.py`，用 UE Python commandlet 加 `-AllowCommandletRendering` 运行，完成纹理导入及材质编译，不运行游戏。
- 接入：编辑器打开且已停止 Play 时执行 `Tools/FatZombie/activate_style_sample.ps1`。通过 MCP 只设置并保存 `SK_FatZombie_Meshy` 的 `Material_002`，不覆盖其他会话的磁盘版模型。工程编辑器已关闭时，可用 UE Python commandlet 运行 `Tools/FatZombie/activate_style_sample.py` 完成同一材质槽的离线保存。

新资产：

- 母材质：`/Game/Monsters/Shared/InfectedSurfaceV1/M_InfectedSurface_V1`
- 胖子实例：`/Game/Monsters/FatZombieMeshy/StyleV1/MI_FatZombie_Infected_V1`
- 4K 贴图：`/Game/Monsters/FatZombieMeshy/StyleV1/Textures/T_FatZombie_StyleV1_*`
- 当前模型：`/Game/Monsters/FatZombieMeshy/SK_FatZombie_Meshy`

贴图合同：

| 贴图 | 含义 | 导入 |
|---|---|---|
| BaseColor | 皮肤、病变、布料的基础色 | sRGB |
| Normal | 原解剖法线加浅表组织及毛孔，已烘焙为 DirectX | Normalmap；不再翻转绿通道 |
| ORM | R 环境遮蔽、G 粗糙度、B 金属度（此样板为 0） | 线性 Masks |
| TissueMasks | R 皮肤、G 湿组织、B 干痂 | 线性 Masks |

表面分区在原 UV 上烘焙，随蒙皮运动；不在运行时用世界坐标投射伤口。共用母材质可以接收其他角色按同一合同烘焙的贴图，不能把胖子的 UV 贴图直接套给其他角色。

母材质参数：`SkinTint`、`ClothTint`、`DryRoughnessBias`、`WoundWetness`、`ScabRoughnessBias`、`NormalStrength`、`DrySpecular`、`WetSpecular`。采用 Default Lit 的 Substrate 输出，局部干湿差异优先由贴图控制；没有为皮肤添加整体发光或金属反光。

## 来源和恢复

模型与原 PBR 为用户提供的 Meshy 胖子，来源见 `SourceAssets/FatZombieMeshy20260913/source_manifest.json`。局部微表面复用工程已有 `ZombiSkinMaterial` 的 Height / Roughness / AO，来源边界沿用 `SourceAssets/HandBrain20260910/material_v04/provenance.json`；不重新认定其许可。局部伤口和分区为本次程序化节点制作。没有新增购买、下载或模型生成。

旧材质 `/Game/Monsters/FatZombieMeshy/Materials/M_FatZombie_Meshy` 及旧贴图保持原样。若用户决定恢复，只需把 `Material_002` 指回旧材质并保存模型。

## 完成记录

作者产物记录 `SourceAssets/FatZombieStyleV1/authoring_manifest.json`，UE 导入记录 `ue_import.json`，最终材质槽保存记录 `activation.json`。这些记录表明对应制作/保存操作完成，不代表视觉或游戏测试通过。

按用户全局规则，本次不启动预览、不截图、不跑自动测试或游戏验收。用户随后同意继续，手脑、毒蛆、突变体已按各自特点制作并接入，见 [后续三只怪物](MonsterStyleV1.md)。2026-09-19 用户允许本轮整理和发布，制作记录中的未测试状态保持真实。
