# 715 两款枪口配件模型

## 当前修订：靶射配重套 V2

用户截图反馈旧配重套呈厚方块、与枪身衔接突兀。该配件已使用 `SourceAssets/DanWesson715MuzzleWeightFitV2_20260927/` 的新制作入口重做并重导入；下文首版配重套的三角数与编辑入口仅作为历史记录。轻量紧凑补偿器保持首版。

- 外形从圆角矩形改为原枪外壳的截面轮廓，下部跟随原枪收窄，去掉原先侧下方空余的方块体积。
- 向后延展渐薄的衔接段，内侧沿真实枪模截面形成包覆面，顶部延续枪身轮廓并保留原厂准星空间。
- 前肩与下沿改为连续圆润过渡；保持原挂点、局部坐标和 1.17 cm 的枪口特效出口。
- 配重套外表面使用独立 `M_DW715_TargetWeightSteel_V2`，沿用既有钢材 PBR 贴图和雨滴图，降低干态粗糙度以接近原枪的抛光反射。公共钢材不改；独立材质已加入现有湿润材质库。
- 同步重制配件灰阶透明 PNG 和 UE Texture2D 图标。三级 LOD 的作者三角数为 18146 / 9980 / 5080。

新版沿用正在使用的 `MuzzleModels20260927/Meshes/SM_dw715_target_muzzle_weight` 资产路径，无 C++、属性、存档或枪口出口变更，不需要再次原生构建。通过已运行编辑器的互斥 MCP 批次完成重导入并保存网格、专用材质、湿润库及图标；具体保存结果见新版目录的 `install_receipt.json`。修改前磁盘资产和枪匠 PNG 保留在同目录 `Before/`，旧 Blender 源保持原样。没有启动编辑器、游戏或执行验收渲染／测试。

当前编辑入口：`SourceAssets/DanWesson715MuzzleWeightFitV2_20260927/dw715_target_muzzle_weight_Editable.blend`；制作脚本 `author.py`、`author_icons.py`、`install.py`。旧模型导入脚本的作者批次保护会阻止覆盖这一版。

## 首版制作与接入记录

按用户“直接制作模型”的要求完成写实游戏模型制作与资产保存，并在用户关闭 UE 后继续接入 715 枪匠。模型采用 Blender 硬表面建模；先前被否决的金属块、科幻装饰图均不作为造型依据。

落盘状态：UE 无界面导入已完成，两个 StaticMesh 均含三级 LOD，另存两张 Texture2D 图标；本批四个资产保存成功，记录为 `import_receipt.json` 的 `imported_and_saved`。未启动交互编辑器或游戏。

## 模型设计

| 配件 | 独立网格 ID | 外观 | LOD0 / LOD1 / LOD2 三角数 |
| --- | --- | --- | --- |
| 轻量紧凑补偿器 | `dw715_compact_compensator` | 短型前端、单组侧向可见开口、连续过渡肩与圆润边角 | 9848 / 4924 / 2264 |
| 靶射枪口配重套 | `dw715_target_muzzle_weight` | 包覆原枪口附近、下部略厚、上部开放避让原厂顶部结构 | 6772 / 3386 / 2016 |

配重套的包覆轮廓从现有枪模钢制枪管与枪身外壳的截面共同生成；这属于虚拟网格贴合，不是现实制造或安装方案。保留原枪体、原厂准星及现有枪管，不恢复已取消的枪管改造类别。

## 可编辑源和导出

制作目录：`SourceAssets/DanWesson715MuzzleModels20260927/`。

- `dw715_compact_compensator_Editable.blend`：补偿器编辑入口。
- `dw715_target_muzzle_weight_Editable.blend`：配重套编辑入口。
- `DW715_MuzzlePair_Assembly_Editable.blend`：包含不可选的宿主线框参考和两款互斥显示的原点对齐配件。
- `DW715_MuzzlePair_IconScene.blend`：两张灰阶透明游戏图标的作者场景。
- `Exports/SM_dw715_compact_compensator.fbx`、`Exports/SM_dw715_target_muzzle_weight.fbx`：各带三级 LOD。
- `prepare_source.py`、`author_models.py`、`author_icons.py`、`import_assets.py`：对应来源提取、模型制作、UI 图标制作与 UE 资产导入入口。
- `source_frame.json`、`authoring.json`、`icons.json`、`import_receipt.json`：源坐标、导出和保存记录。

实际宿主引用为 `DanWesson715WeaponAssets.h` 中的 `/Game/Weapons/DanWesson715/Chrome20260914/SK_DW715_Manny`。制作沿用 `DanWesson715GripBrake20260927/FitInspection/host.json` 的游戏网格快照与参考姿态。Blender 使用米、局部 +X 向前、+Z 向上；原点为原有 `WPN_SOCKET_Muzzle`，与 `DanWesson715FittedParts::Configure` 的坐标约定相同。FBX 按既有导出约定输出厘米资产。

## UE 资产

目标目录：`/Game/Weapons/DanWesson715/MuzzleModels20260927/`。

- `Meshes/SM_dw715_compact_compensator`
- `Meshes/SM_dw715_target_muzzle_weight`
- `Icons/T_dw715_compact_compensator`
- `Icons/T_dw715_target_muzzle_weight`

两款配件均复用当前 `SM_dw715_muzzle_brake` 的 `DW715_Steel`、`DW715_DarkSteel` 材质绑定，沿用现有 PBR 与湿润参数，不重复创建纹理或修改公共材质。导入保留作者法线、按最终 UV 生成切线，不生成物理碰撞。

图标按当前标准制作：1024×1024、透明背景、单件、无彩色灰阶、水平左向。两张 PNG 已复制到当前枪匠目录 `Content/ColdSteelData/AttachmentIcons20260913/`，采用 `ue_dan_wesson715_muzzle_<配件 ID>.png` 命名；对应 Texture2D 已保存于本批 UE 资产目录。

## 已确定的游戏属性

| 配件 | 后坐力 | 枪械稳定性 | ADS 瞄准时间 |
| --- | --- | --- | --- |
| 轻量紧凑补偿器 | -10% | +5% | 不变；无负面 |
| 靶射枪口配重套 | -25% | +20% | +10% |

上述数值已写入 `Content/ColdSteelData/gunsmith.json` 的 715 专用 `muzzle` 槽，与原厂枪口和现有制退器互斥。轻量紧凑补偿器没有 ADS 或其他负面属性；稳定性统一通过 `stability_mult` 接入既有枪械操控计算，不单列镜头震动属性。

`DanWesson715FittedParts` 共用识别、网格路径和局部枪口出口；`M4MuzzleVisual` 的 715 分支从该处取得出口。补偿器出口为局部 `(1.95, 0, 0)` 厘米，配重套为 `(1.17, 0, 0)` 厘米，原制退器保持 `(3.4, 0, 0)` 厘米。装备及预览沿用现有 `Configure` 贴合变换；左手双持沿用现有附件复制及 `MuzzleLocalTip` 复制逻辑。

新增选项通过现有枪匠目录参与装备和存档识别，无存档格式变更。图标预加载复用 `Supports` / `MeshPath`；全局异步预加载表已从源码重新生成，加入两条完整网格路径。现有 `/Game/Weapons/DanWesson715` 打包目录包含这批 UE 资产，现有湿润材质库继续覆盖复用的金属材质。

## 交付边界

模型、UE 资产、枪匠选项、属性和原生接入代码已落盘。用户保存并关闭编辑器后，已通过 `Tools/Build/Build-Editor.ps1` 完成 `FPSGAMEEditor Win64 Development` 正式构建，结果 `Succeeded`、退出码 0；`UnrealEditor-FPSGAME.dll` 已重新链接。构建日志：`Saved/BuildEditor/build-20260927-214048.log`。

未启动交互编辑器或游戏，未执行测试、检查探针或验收渲染，由用户自行测试。

`import_receipt.json` 记录先前模型阶段的实际导入与保存结果，其中 `gameplay_published: false` 是当时阶段状态；本次接入与构建进度以本文为准。UI 图标是制作资产，不能代替游戏验收。

来源：两款为本地原创游戏网格；复用项目现有宿主参考及已在用材质。未复制商品宣传图片、生成概念图或其他枪型网格作为最终组件。
