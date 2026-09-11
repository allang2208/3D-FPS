# 恢复完整 UE5 内容

源码来自 2026-09-10 的本机 `D:/FPS3D/FPSGAME`。此次换引擎整理保留完整模块与配置，未公开整套本地 Content 和二进制作者源。许可证及图片 provenance 只说明已有记录，不自动授予原始文件公开分发权。

## 本机继续开发

本机原工程未移动，仍打开 `D:/FPS3D/FPSGAME/FPSGAME.uproject`；本目录现已接入独立 Git，日常开发、提交、推送全部在 D 盘完成，不需复制到 E 盘。如使用新的 Git checkout，在确认拥有使用许可后，从完整宿主复制 `Content`，保持相对路径和 World Partition 的 `__ExternalActors__`/`__ExternalObjects__` 成套；不要用旧快照覆盖当前源码。复制前处理目标同名文件的差异，不批量覆盖新工作。

作者编辑还需要本机 `SourceAssets` 中的 Blend、FBX、声音和引用源；仓库只包含当前 M4 三段依赖链的作者脚本及记录，恢复本地源目录可补齐其输入。`Tools` 中部分旧参考导出器仍指向本机 Godot 归档，不参与 UE 游戏运行。历史工具带绝对宿主路径，运行前检查其输入和输出路径。

## 主要资源依赖

2026-09-11 瞄具恢复补充：本次发布源码与作者脚本，二进制仍按本文件的本机恢复规则处理。需要 `Content/Weapons/PanoramicRedDot`、`PrismScope2XMachined`、`LPVO1to6X`（镜身与倍率环两网格）。对应 `SourceAssets/PanoramicRedDot20260911/GameIntegration` 依赖同案例 `Reroll03` 母版；`PrismScope2X20260911/MachinedControls` 依赖上级 scope2x 母版；LPVO 依赖本目录母版、三视图、参考和四张 PBR 贴图。不要从 trash 的旧瞄具输出恢复当前资源。生成图、源 GLB/Blend/FBX、uasset 和第三方参考图此次未公开上传。

| 内容 | 当前恢复位置/说明 |
| --- | --- |
| 启动地图 | `/Game/GameMaps/DayNight_Lighting`；按 Config 的真实路径恢复 |
| 枪械/手臂 | `Content/Weapons`，包括 M4HK416Replica、M4WrapGripFinal、M4SlapImpactFinal、M4TacticalTossFinal 及枪匠配件 |
| 声音 | 枪械 HK416 派生音效和天气资源；具体引用见当前源码及已有来源说明 |
| UI/物品图标 | `Content/ColdSteelUI`、`Content/UI`、`Content/ColdSteelData/Icons`；JSON provenance 不等于图标授权 |
| 天气/场景 | `Content/Weather`、PWL_Light_Manager、Lighting、SceneTests 及相关地图和场景包 |
| 怪物 | `Content/Monsters`、`Content/ZombieFemale`；用户提供包的许可尚需独立确认 |
| 作者源与 MAT | 本机 `SourceAssets` 与原 MAT 工具资产；MAT 不是本次公开发布的插件包 |

`ContentInventory.json` 列出宿主各内容目录的文件数和大小，供检查恢复范围；它不是每个资源的授权证明。

## 插件和构建

保留宿主原 `FPSGAME.uproject`。CommonUI、EnhancedInput、PCG、PythonScriptPlugin、EditorScriptingUtilities、ModelingToolsEditorMode 等按描述符启用。`ModelContextProtocol` 与 `AllToolsets` 是额外编辑器工具，需要安装兼容 UE 5.8 的版本；不需要这些工具时可以在自己的 checkout 中关闭这两个 Editor 插件，再生成工程，切勿因此移除游戏模块依赖。

C++ 编译不需要先公开地图素材；成功编译也不意味着缺失地图/动画可以运行。恢复资源后用对应 `Tools` 脚本和真实游戏镜头验证；重建原生模块后启动新编辑器进程，避免旧模块仍在内存。

Windows 系统字体及其派生字体仅按工具中的本地用途处理，不随本仓库公开发布。现有天气来源说明见 [ThirdPartyNotices](../ThirdPartyNotices/WEATHER_ASSETS.md)。

## 非枪械物品（2026-09-11）

物品模型、材质和光效恢复 `Content/Items/{Consumables,EnhancementMaterials,MagicScroll,LootFX}`；背包图标恢复 `Content/ColdSteelData/Icons` 中相应文件。精确路径、大小与 SHA-256 见 [本机素材清单](Art/non-weapon-items-local-content-20260911.json)。三视图、原始高模、可编辑 Blend 和 UE 导入输入仍需从完整本机 SourceAssets 恢复。此次只发布源码、作者脚本、参数/证据和技能，未开放整套素材二进制；不代表完整资产远程备份。

## 第一人称攀爬（2026-09-11）

恢复本机 `Content/Movement/Traversal/Native`（手臂网格、动画及动画包围盒版本），以及初始地图及其 ExternalActors/ExternalObjects。测试障碍可由 `Tools/SceneTests/place_traversal_course.py` 在已打开的初始地图重建。源参考与可编辑工程位于 `SourceAssets/GASPTraversal20260910/{Reference,Native}`，作者脚本还依赖本机 `SourceAssets/M4TacticalToss20260910/M4_Hand_MAT_Editable.blend`。需自行取得官方 Game Animation Sample 的使用许可；原始动画、FBX、Blend、参考截图与运动采样数据本次不公开分发。

Git 包含攀爬 C++、配置、作者工具、导入/包围盒/作者校验摘要和技能。AKM 完整宿主集成属于独立内容依赖；发布核心的攀爬测试在缺少 AKM 目录定义时使用第二把 M4，不将其报告为 AKM 素材验收。完整宿主之前的 AKM 运行记录保留在攀爬文档。

## AKM 瞄具与枪钢（2026-09-11）

本机当前恢复还需要 `Content/Weapons/AKMIntegration/SovietFab/{Attachments,ArmSupport,Optics,OpticSteel}`，以及同枪的动画、原始 Soviet Fab 模型/贴图和 M4 共用手模。`Optics` 为当前侧装桥架，`OpticSteel` 为 AKM 独立瞄具及材质，保留共享 M4 镜片/分划等依赖。完整材质来源仍遵守原 Fab 许可，不能从本次公开脚本推断获得了原资产分发权。

作者复现源需要 `SourceAssets/AKMArmSupport20260911`、`AKMAttachments20260911`、当前 M4 瞄具源以及 `AKMBridgeRefine20260911`、`AKMOpticSteel20260911` 的本机二进制输入；按各案例 README 顺序执行。旧方块底座和失败中间件已移入 trash，当前恢复不从旧文件覆盖正式资产。此次只整理发布工作流、脚本与记录；未将混合并行修改的 AKM 运行模块当作新源码基线发布。见 [整理与验收记录](Weapons/akm-optics-workflow-20260911.md)。


## Gunplay 与枪口 VFX（2026-09-11）

恢复 `Content/NiagaraExamples`（已获授权的 Epic Niagara Examples Pack）及 `Content/Weapons/GunplayFX`。当前引用为 `NS_FPS_MuzzleEpicV5`、`NS_FPS_BarrelSmokeEpicV5`、`M_BallisticTracer`，以及原有枪口、烟、弹壳材质。第三方派生 Niagara uasset 仅本机保留，本次没有上传其二进制。

最终生成器 [build_muzzle_presentation_v5.py](../Tools/AssetPipeline/build_muzzle_presentation_v5.py) 直接以原包 `FX_Weapons/MuzzleFlashes/NS_MuzzleFlash` 重建，不需要 trash 中的旧候选。需项目 `RainAssetEditor`、UE 5.8 NiagaraToolset 和原始素材；`-MuzzleRebuildProbe` 写独立测试资产。曳光材质用 [build_ballistic_tracer.py](../Tools/AssetPipeline/build_ballistic_tracer.py) 创建。参数、历史迭代和本机证据见 [烟火记录](muzzle-smoke-presentation-20260911.md)，归档记录见 [清单](gunplay-archive-20260911.json)。
