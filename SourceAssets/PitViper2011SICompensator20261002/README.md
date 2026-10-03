# 2011 限定改造：SI 枪口补偿器

制作于 2026-10-02；2026-10-03 已完成 UE 资产保存、原厂分区替换、单双持装配、改造目录与专属图标接入，Editor / Game 正式构建成功。交付记录为 `delivery_receipt.json`，各阶段落盘记录为 `integration_receipt.json`、`icon_delivery.json`、`catalog.json` 与 `build_receipt.json`。未进行游戏测试或验收渲染。

## 交付文件

- `Blender/SICompensator_Editable.blend`：可编辑源文件，保留布尔开孔、倒角、材质及隐藏的 2011 装配参考。
- `Blender/SICompensator_ExportReady.blend`：整理后的导出场景，包含最终网格与安装标记。
- `Exports/SM_PitViper2011_SICompensator.fbx`：后续引擎导入文件。
- `Exports/SM_PitViper2011_SICompensator.obj`：通用模型文件及材质描述。
- `author_si_compensator.py`：后台建模与导出脚本。
- `authoring_receipt.json`：制作结果、来源、尺寸、坐标变换及未来接入说明。
- `Reference/SI-compensator-user-reference.png`：用户提供的外观参考。
- `Integration20261003/`：单持、右手双持、左手双持的原厂补偿器分区 FBX，保留既有骨架、权重、UV 与其余材质槽。
- `author_body_sections.py`、`import_si_compensator.py`：分区制作及定向 UE 导入，不导入或改写动画。
- `Icons/`：基于实际 SI 模型制作的专属灰度卡片图标及可编辑图标场景。
- `publish_catalog.py`、`import_icon.py`：限定选项发布及 PNG / Texture2D 落盘。
- `run_import.ps1`、`build_native.ps1`：使用现有批次互斥的后台导入、Editor / Game 正式构建。

## 外观与材质

方形切面外壳、后部顶部开口、两道顶部贯穿侧面的排气槽、圆角侧窗、每侧四个小孔、前下部斜面，以及灰色 SI / HOT 标识。沿原厂枪口的真实侧视斜线和复合侧角延展 29 mm，最大宽度为约 23.861 mm，全段沿用原厂鼻端轮廓；这些尺寸用于游戏模型适配。

主体采用现有 2011 的金属母版实例，内孔采用项目深色金属，灰色激光标识使用独立实例。新材质位于 `/Game/Weapons/PitViper2011/SICompensator20261003/Materials`，并加入现有枪械湿润材质表。材质通过实例参数完成，不额外生成整枪贴图。

当前枪身延展修订的导出网格为 11,954 三角面。可编辑文件保留完整原厂枪口段与准星支架。

## 安装基准

2026-10-03 当前修订使用原厂枪口的实际前端外表面作为接合基准，包括侧视下缘约 33.024° 的斜切线与两侧复合倒角。SI 后面由原始鼻端表面反向构成，贴合后沿枪管轴向延展，完整原厂前段随 SI 静态资产一同保留。整段宽度保持约 23.861 mm，取消之前加宽到 26.2 mm 的壳体。内部凹腔、排气孔和 SI / HOT 标记随新位置布置，并沿用细腻金属材质。当前修订来源和落盘记录见 `../PitViper2011SIBodyExtension20261003/`；旧的上肩斜切方案仅保留历史记录。未进行游戏测试或验收。

模型使用米制单位，+X 朝枪口，+Y 朝右，+Z 朝上。原点位于原厂补偿段的主要后安装面与枪管中心线交点；原始模型中该安装面 Y 为 -0.09058 m。

- `SOCKET_MountRear`：安装原点。
- `SOCKET_Muzzle`：前端中心，X = 0.046218629 m。
- `SOCKET_AimGuide`：朝向参考，X = 0.071218629 m。

原厂 h-190 材质同时用于其他枪体部件，因此将原厂黑色补偿器及其安装支撑的 430 个三角面移至独立 `M_PitViper2011_FactoryCompensator` 分区。安装 SI 时只隐藏该分区；卸下或切换普通配件时恢复。SI 模型保留完整原厂黑色枪口段和准星支撑，并从实际原厂前端向前延展；原枪管与发光准星继续显示。

装配跟随 `WPN_Barrel`，相对既有原厂枪口标记沿枪管方向后移 1.72186285 cm，使模型安装面与原厂接口对齐。枪口火光和出射参考使用 SI 的 `Muzzle` / `AimGuide` 插槽。双持临时左手模型显式继承补偿器分区隐藏状态；法杖副手沿用同一路径。

## 游戏选项

入口为 2011 的改造栏 → 枪口 → **SI 枪口补偿器（限定）**。

- 改造 ID：`pit_viper_si_compensator`；宿主：`ue_pit_viper2011`；槽位：`muzzle`。
- UE 网格：`/Game/Weapons/PitViper2011/SICompensator20261003/SM_PitViper2011_SICompensator`。
- 枪匠目录：`Content/ColdSteelData/gunsmith.json`，保持既有按零件 ID 保存与恢复的通路。
- 数值与效果（用户于 2026-10-03 指定）：开镜耗时 −10%、后坐力 −10%、枪械稳定性 +5%、腰射随机散布 −20%。`stats` 分别使用 `ads_percent=-0.10`、`recoil_mult=0.90`、`stability_mult=1.05`、`hip_spread_mult=0.80`，提示与目录生成脚本同步维护。
- 图标 key：`ue_pit_viper2011_muzzle_pit_viper_si_compensator`；PNG 位于现有 `AttachmentIcons20260913/FramedFirearms`，对应 Texture2D 位于新资产目录的 `Icons`。
- 常规通用改造继续复用已有图标，本次只制作 SI 专属外形的限定图标。

原始 2011 制作脚本已记录 `FactoryCompensator` 分区，通用改造目录发布脚本会恢复已保存的 SI 选项，后续重新制作或发布时保留此改造。

原生接入由 `Source/FPSGAME/Weapons/PitViper2011SICompensator.*`、`M1911AttachmentVisual.cpp`、`PistolDualWieldComponent.cpp` 负责；卡片和预加载沿用既有枪匠代码。后台构建产物状态以 `build_receipt.json` 为准。未自动启动 UE 编辑器或游戏，表现由用户测试。

## 来源

用户图片仅作为外观参考。外壳、开孔和标识在 Blender 中制作；保留的安装端及准星支架来自现有 2011 接入源文件 `PitViper2011Integration20261002/canonical_parts.json`。

原模型：D_U 的 [Low Poly TTI JW4 Pit Viper 2011](https://sketchfab.com/3d-models/low-poly-tti-jw4-pit-viper-2011-2daaf7fe78604ee7941a4ad5fd4d0153)。原接入记录为 CC BY 4.0；后续发布继续保留原模型署名与修改说明。


2026-10-03 整理发布：上肩 SIChamfer 方案已归档；当前源使用 SIBodyExtension20261003 的原生枪口延展，仍使用本目录的实际模型和 FBX。归档清单与恢复范围见 `Docs/Weapons/pit-viper2011-publication-20261003.md`，所有移动文件均可从 trash 恢复。
