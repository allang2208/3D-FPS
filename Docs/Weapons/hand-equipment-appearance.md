# 手部装备替换标准

2026-09-12 用户接受现有效果，并指定以后增加衣物、手套装备时沿用此方法。基线为 Manny 手模、原色棕皮革手套、裸露前臂皮肤、炭灰布袖；手套沿手腕向前臂延长 3 cm，开口用约 4 mm 薄卷边、浅沟槽与窄接触色过渡处理。

作者入口：[SourceAssets/HandEquipmentAppearance](../../SourceAssets/HandEquipmentAppearance/README.md)。技能入口：[手部装备表现](../../skills/ue5-fps-arms-animation/references/hand-equipment-appearance.md)。

## 现用资产与适用边界

| 用途 | 保留的 UE 路径 |
| --- | --- |
| 共用上臂实例 | `/Game/Weapons/M4InfimaV3/MI_Manny_01` |
| 炭灰布袖父材质 | `/Game/Characters/ArmsSkinSleeveCandidate/M_Manny_Sleeve_01` |
| 共用前臂/手套实例 | `/Game/Weapons/M4InfimaV3/MI_Manny_02` |
| 已接受手套父材质 | `/Game/Characters/ArmsGloveCuff3cmCandidate/M_Manny_RolledCuff3cm_02` |
| 卷边作者贴图 | 同上目录的 `T_Manny_Cuff3cmField`、`T_Manny_Cuff3cmRollNormal` |
| 皮肤与衣袖分区 | `/Game/Characters/ArmsSkinSleeveCandidate/T_Manny_ForearmRegions` |
| 皮肤散射配置 | `/Game/Characters/ArmsSkinSleeveCandidate/SSP_ForearmSkin` |
| 皮革与缝线共用纹理 | `/Game/Characters/ArmsLeatherCandidate/Textures/` 下五张纹理 |

路径中的 `Candidate` 已被现用实例引用，保留路径避免破坏依赖。不能仅凭名字将其当作废案。完整实例依赖及退役组引用见作者目录的 `dependency_audit.json`。

本例保留原始网格，所谓延长是把皮革区域覆盖到前臂；卷边由切线法线和表面明暗表现，轮廓没有新增几何。要求真实开口厚度、宽松袖口或明显突出轮廓时，应另建带权重的手套/袖子网格，并验证腕肘变形、遮挡和穿模。

当前 M4 与 AKM 共用上述 Manny 材质。核对 `Source/FPSGAME/FPSGAMECharacter.cpp` 中实际加载路径再验收；本次核对了 M4 HK416Replica 和 AKM StockV2（Attachments 备用），以后不能按目录日期推断现用资产。

## 制作方法

1. 查看当前持枪与换弹近景，读取材质槽、网格连通壳、UV、手骨权重和肘腕距离。现用 `MI_Manny_02` 同时覆盖手套与前臂，不能直接整槽染色。
2. 从现有壳与权重生成手套遮罩，按真实表面分区。皮革区域图 R=手套、G=掌面/指腹、B=真实壳边缝线；皮肤区域图 R=裸露皮肤、G=肘腕坐标、B=内侧权重、A=布袖口。UV 岛切口本身不是服装缝线。
3. 使用经许可的 PBR 材质，保留来源、扫描尺寸、散列与通道约定。本例 Quixel 25 cm 扫描按网格/UV 面积得到重复数 4.311859；保留原始棕色 RGB，金属度 0，掌面更粗糙。此比例不能无测量套用到另一手模。
4. 皮肤仅在裸露区域使用低幅色差、细毛孔及 Subsurface Profile。本例 `SkinScatterStrength=0.18`，皮肤基础线性色 `(.36,.235,.185)`；衣袖 `(.02,.024,.027)`。原盔甲板法线不能残留在皮肤或新增皮革区，保留原手套自身细节并叠加皮纹与缝线。
5. 用参考姿态的肘到腕轴定义 `t=0..1`。本例前臂长 27.251 cm，3 cm 开口为 `t=1-3/27.251=0.8899122968`。把局部坐标烘焙为独立未压缩线性 G8：`t=0.8849122968+R*0.045`；不要直接对全前臂 BC 压缩坐标作很窄的阈值，否则开口会阶梯化。
6. 沿表面方向烘焙薄卷边：本例 0.65 mm 法线隆起中心距开口 2.2 mm，0.10 mm 浅槽中心距开口 4.8 mm。依据原三角形 UV、平滑法线及镜像手性计算切线方向；边缘扩展 4 px。与局部距离场同步的明暗/粗糙度和窄接触色过渡使皮革接皮肤更自然。

修改延长距离时，同时调整 `bake_rolled_edge.py` 的长度/起点、`rolled_cuff.hlsl` 的局部编码/距离换算和 `build_material.py` 的起点，再重烘焙场与卷边法线。只改实例的 `GloveCuffStart` 会令开口与已烘焙卷边错位。3 cm 是本次选择，不是所有手套的固定长度。

## 将来接入衣物与手套装备

本次交付的是已接受的外观和作者管线。新增装备时，按项目装备/存档合同接入稳定物品 ID 与外观配置，通过角色组件的独立材质实例或覆盖材质选择皮肤、衣袖和手套；避免玩家换一副手套就修改全局共用 `MI_Manny_01/02` 资产。

衣物控制袖子覆盖区，手套控制手部及袖口覆盖区，未覆盖处恢复基础皮肤；明确重叠处的遮挡顺序，脱下、切枪、重生和读档时由装备状态重算。保持武器网格的对应槽和已接受动作；如另加网格，复用现有骨架与有效蒙皮权重。用不同角色或预览实例同时显示不同装备，检查是否互相污染。这里只规定后续接入验收，未宣称已经完成衣物装备系统。

## 本地恢复与验证

所需原模型：`SourceAssets/M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend` 的 `SK_Manny_Arms_Export`。同时需要原项目 Manny 材质实例、基础贴图和现用武器网格。原手模及 Fab 原始二进制依赖按 [资源恢复规则](../AssetSetup.md) 留在已许可本机，Git 不是完整素材备份。

皮革来源：[Quixel Fabric Generic Leather Top Grain Brown](https://www.fab.com/listings/ccd7a956-27f6-4417-b4e0-d1eb92e55ea0)。用户提供的 ZIP SHA-256 为 `04ceb8684d80e4d0ff1ceafc10fd15b28d0633829bed8f9fd0add172f3dab0a5`；本地源与逐文件散列在 `source_maps.json`。本次只使用既有已下载依赖，未重新核验商城价格或扩大再分发许可。

若恢复时没有作者贴图，在正式作者目录依次执行：

```powershell
$author = 'D:/FPS3D/FPSGAME/SourceAssets/HandEquipmentAppearance'
$blender = 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
& $blender --background --python "$author/inspect_regions.py"
python "$author/bake_glove_mask.py"
& $blender --background --python "$author/inspect_leather.py"
python "$author/bake_leather_regions.py"
& $blender --background --python "$author/export_surface.py"
python "$author/bake_forearm_regions.py"
python "$author/bake_rolled_edge.py"
# Source/ 缺失时，先按实际本地 ZIP 路径调整并执行 prepare_leather_source.py。
```

普通 Python 需 numpy、Pillow、scipy；Blender 脚本使用 bpy。`validate_authoring.py` 在临时目录重烘焙六张图并逐字节比对本地已接受贴图，检查原 Blend 不变，不覆盖正式贴图。

纹理和材质重建使用 UE Python（会显式恢复共用基线）：

```powershell
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript -script="$author/restore_assets.py" -NullRHI -unattended -nosplash -DDC=InstalledNoZenLocalFallback -ModelContextProtocolPort=18012
```

随后用同一命令将脚本换为 `verify_saved.py`，以新的进程回读磁盘。`restore_assets.py` 会导入皮革图、皮肤区域、卷边图，重建两个正式父材质并应用；没有恢复 6 cm/白色废案的分支。

BaseColor 使用 sRGB；roughness/mask 线性；法线使用 Normalmap。此 Fab 包经 Bump 梯度核对是 OpenGL，UE 翻绿；自己烘焙的缝线/卷边为 DirectX，不翻绿。局部袖口场为线性 G8。UE 5.8 标量 setter 的布尔返回值可能不代表赋值结果，必须 getter 回读和保存后重载。

已有 UE 编辑器或并行游戏进程占用资产时，等待有限重试并核对保存结果，不停止其他任务。缓存/端口使用本进程参数；失败应看明确脚本标记与 fresh readback。本项目已有 GameFeatureData 配置错误会让 commandlet 退出 1，不能把它写成干净退出 0。

实际画面使用 `run_preview.ps1 -Label <新名称>`，检查两手、掌背、握枪、空仓换弹及腕部旋转时开口是否完整/平滑、卷边是否接齐、皮肤有无漏色/原盔甲法线、皮纹是否像塑料。需要真实厚度时另做几何，不能用正面材质截图宣称轮廓正确。

整理前已接受的 M4 2560×1440 DX12 捕获位于 `Saved/GunplayUpgrade/arms-glove-cuff-3cm-rolled-20260912`：进程退出 0，47 项通过，仍有两项既存粒子过期失败 `fx_particles_expire`、`fx_expire_after_input_regressions`。AKM 在该次是材质引用验证，不能称为 AKM 全动作实机验收。历史记录在作者目录 `Evidence/`，本次整理与发布证据单独记录。

## 归档与发布

确认退役组无外部引用后，旧黑白/白皮革/短袖口/6 cm 资产、早期脚本与试验捕获移入 `trash/hand-equipment-standard-20260912`；有效作者源已经集中在正式目录。逐文件原位置、归档位置、大小、散列、原因和保留替代物见 [归档记录](hand-equipment-publication-20260912/archive_manifest.json)。

发布只包含作者脚本、参数、来源说明、紧凑验证记录和技能。贴图、扫描、源网格、UE 资产、日志、截图与 trash 不随本次公开 Git 提交。整理和推送遵循根目录 [WORKFLOW.md](../../WORKFLOW.md)，精确提交本任务文件，保留并行修改。
