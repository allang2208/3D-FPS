# 怪物材质统一 V1：手脑、毒蛆、突变体

日期：2026-09-19。用户同意在胖子材质样板后继续处理三只怪物。此轮是制作与接入，实际画面由用户在 F6 中判断，未进行预览、截图或游戏测试。

## 共用规则与角色差异

复用胖子样板的 `M_InfectedSurface_V1`，统一低饱和感染组织、干皮肤、局部湿组织及干痂的材质含义。每只怪物仍使用自身 UV 和独立贴图，不把同一张皮肤图覆盖所有角色。

| 怪物 | 本次处理 | 保留的外形身份 |
|---|---|---|
| 手脑 | 灰绿、灰褐皮肤；暗红湿伤口与不规则干痂边缘；指甲、褶皱、肌腱的浅表细节；沿现有解剖标记微调指节和指段 | 缠绕手臂、冠部手指、口腔与牙齿分别处理 |
| 毒蛆 | 乳白偏灰的虫皮；体节污渍、细弱皮下色差、细纹及局部湿膜；躯干加入很小的非对称起伏 | 原体节、口器、步足及虫体轮廓 |
| 突变体 | 灰白皮肤的局部色差、轻微淤色、浅表凹凸；裤子保留深色并提高干燥感 | 原体型和服装，无网格修改 |

手脑局部网格偏移上限为 2 mm，毒蛆为 6 mm。调整现有顶点坐标，沿用原拓扑、UV、顶点组及骨架；不重制骨骼和动作，不替换物理资产。毒蛆的脚部、腹部接地面及头部由位置遮罩排除。微表面参数以米计，烘焙后使用模型 UV；运行时没有滑动的世界坐标贴图。

V1 使用不透明 Default Lit 材质。虫皮的薄膜层次由颜色、细纹与局部粗糙度表达，没有加入透射或整体发光。

## 资源及制作入口

- 参数：`SourceAssets/MonsterStyleV1/settings.json`，共用色板来自 `SourceAssets/FatZombieStyleV1/style_parameters.json`。
- 制作脚本：`Tools/MonsterStyle/author_surface.py`。Blender 后台运行，末尾依次指定 `-- handbrain`、`-- maggot`、`-- mutant`。执行贴图烘焙与导出，不渲染预览。
- 可编辑源：`SourceAssets/MonsterStyleV1/<角色>/<角色>_StyleV1_Authoring.blend`。手脑保留独立的身体、攻击手臂、冠手和牙齿，保存后才在 FBX 导出副本中合并。
- UE 导入：`Tools/MonsterStyle/install_surfaces.py`。在工程编辑器关闭时用 UE Python commandlet 运行并启用 `-AllowCommandletRendering`，用于材质资源构建。只导入新版本网格、贴图和材质实例，不执行游戏。
- 接入：`Tools/MonsterStyle/activate_surfaces.py`。同样在工程编辑器关闭时运行，只保存指定蓝图的 `VisualMesh` / 网格组件引用及突变体模型的材质槽。

| 角色 | 新资源文件夹 | 接入位置 |
|---|---|---|
| 手脑 | `/Game/Monsters/HandBrain/StyleV1` | 原 `BP_HandBrain` 引用 `SK_HandBrain_StyleV1` |
| 毒蛆 | `/Game/Monsters/PoisonMaggot/StyleV1` | 原 `BP_PoisonMaggot` 引用 `SK_PoisonMaggot_StyleV1` |
| 突变体 | `/Game/Monsters/Mutant3Meshy/StyleV1` | 原 `SK_Mutant3_Meshy` 替换一个材质槽 |

主身体贴图为 4K；手脑其余五个槽为 2K。每槽包含 BaseColor（sRGB）、DirectX Normal、ORM（AO / Roughness / Metallic）和 TissueMasks（皮肤 / 湿组织 / 干痂）。非金属材质的 Metallic 为零。材质实例可通过 `SkinTint`、`ClothTint`、`NormalStrength`、`WoundWetness` 及粗糙度参数继续调整。

本轮沿用原 F6 入口、战斗数值、攻击接触时间、全部动画、AI、毒液特效、碰撞及布娃娃配置。无需编译 C++。现有女僵尸、狼和僵尸犬资源未纳入本次替换。

## 来源与恢复

模型分别来自工程已有的 `HandBrain20260910/surface_v07`、`PoisonMaggot20260911/delivery`、`Mutant3Meshy20260915` 源文件。手脑与突变体的浅表 Height / Roughness / AO 复用已在工程中的 `ZombiSkinMaterial`，沿用 `SourceAssets/HandBrain20260910/material_v04/provenance.json` 的来源记录。毒蛆细纹为程序化制作。没有新增下载或模型生成。

每个角色的 `authoring_manifest.json` 记录生产输出；根目录 `ue_import.json` 记录导入目标，`activation.json` 记录保存操作。这些文件不代表视觉或玩法验收通过。

`SourceAssets/MonsterStyleV1/previous_references.json` 保留接入前的模型和材质引用。恢复时将两个蓝图的 `visual_mesh` 及网格组件指回记录中的旧模型，将突变体单槽指回记录中的旧材质并保存即可。旧网格和旧材质保持原样。
