# 恢复完整 UE5 内容

## 暗纹猎弓 ContactV9（2026-09-25）

恢复 ContactV9 手模与八段动作、ArmsV4 骨架及衣袖／手套、ArmsV2 静态箭／木纹、细节弓体 `RiserDetail20260925/SM_DarkBow_RiserDetail`、结构重构作者源 `RiserForm20260925`、木质长弓替换 `WoodLongbow20260925`，以及原 dark bow、Normandy `T_WoodSurface_00A` / `T_RottenWoodSurface_00A` 和裸手材质依赖。弓体木纹见 [木纹表面](Weapons/dark-bow-wood-finish-20260925.md)，网格升级见 [弓体细节](Weapons/dark-bow-riser-detail-20260925.md)，结构重构见 [弓体结构](Weapons/dark-bow-riser-form-20260925.md)，长弓替换见 [木质长弓](Weapons/dark-bow-wood-longbow-20260925.md)。源码、配置、作者脚本与技能公开；含第三方表面／姿态的 JSON、Blend／FBX／UE 包及回执留在本机。175 个废案文件已归档至 trash；保留输入、重建顺序、散列清单和未游戏测试边界见 [V9 整理与恢复](Weapons/dark-bow-publication-v9-20260925.md)。

## V7 默认裸手与独立手套／衣物（2026-09-25）

恢复本机 `Characters/ModularOutfit20260924`、20 个已写入裸手的基础视模及各自原生骨架／动作；保留 V7 原手套恢复件、Body 旧版基底、皮肤材质与物品图标／掉落件。源码、配置和作者脚本公开，含第三方表面／绑定的网格、贴图、密集 JSON、Blend／FBX／UE 包及导入回执留本机。当前依赖链、71 份废案归档、配方重建边界和未运行测试的状态见 [手模与换装发布／恢复](Characters/modular-outfit-publication-20260925.md)。

## 方形祭坛、出征面板、传送门、探险宝箱与 HDR（2026-09-25）

恢复本机 `Props/SquareAltar20260922`、`Props/GamedevPortal20260922`、`Props/GamedevTreasureChest20260922`、相关关卡／调色板及 PWL／NaturalV2 天空资源。宝箱沿用原路径，当前空心结构和材质写回由 20260923 制作链负责；旧源仍提供骨架和开盖动作。七张 PWL HDR 已保存 BC6H 压缩，原分辨率不变。源码发布、54 份废案归档、旧祭坛保存阻塞和未确认的 M4／天空亮斑问题见 [本次发布与恢复](Publication/gamedev-sky-publication-20260925.md)。不公开模型、贴图、原始材质／蓝图导出或 UE 包；本轮未启动引擎或进行游戏测试。

## 裸皮感染犬与 Godot 四足模板（2026-09-25）

恢复 `Content/Monsters/InfectedDog/MeshyV2`、`BP_InfectedDog`、共享血迹 `M_FleshStainV3`，保留合法 Wolf 动作/行为树与完整 Meshy 作者源。当前奔跑为用户认可的 GodotRunNaturalV3；飞扑、咬击和索敌升级仅完成后台构建与保存，未作游戏测试。废案 319 文件已归档至 `trash/infected-dog-retired-20260925`，重建依赖、来源许可及发布边界见 [感染犬发布记录](Monsters/InfectedDogPublication20260925.md)。

## 仓库储物箱五档与统一 E 交互提示（2026-09-24）

运行资产 `Content/Props/WarehouseCrateTiers20260924`（体素贴图×10、材质×5、母材质实例×8、骨骼网格×5 共享源宝箱骨架与开合片段）为内容目录，不随公开仓库分发，克隆后需从本机恢复。制作链脚本与逐环节收发布尔在 `SourceAssets/WarehouseCrateTiers20260924`（作者化→导入安装→骨骼变体派生→贴图材质→usage 标志修复→探针，见其 README）。本轮废案探针两份（v1 顶面探针、FBX 导出尝试）归档至 `trash/warehouse-crate-tiers-probes-20260924/`，散列清单 `trash/warehouse-crate-tiers-probes-20260924.sha256.txt`。C++ 侧发布五档储物箱 Actor、按容器储物面板与统一准星毛玻璃小浮窗（模型上方世界名牌全部撤除）；共享文件（HUD/PlayerController/Backlog 等）按 hunk 过滤只取本次改动，远征面板、弹药轮、木质占位迁移等并行内容留在其会话未提交状态。表面材质提升计划 `SourceAssets/WarehouseCrateTiers20260924/material_upgrade_plan_20260924.md` 待办于 [Docs/Backlog.md](Backlog.md)。完整构建成功（23:26），未做游戏内验收，由用户测试。

## 地牢生成、墙面与两档加载（2026-09-24）

恢复 `GameMaps/L_Dungeon_Randomized`、本机 `Dungeons` 模板/墙面/杂物资源、Boss 与最终宝箱/返回传送门依赖；完整档主界面直接覆盖当前启动地图，无需新的菜单地图。当前源码、制作链、八份归档、第三方署名及本机二进制边界见 [地牢与加载发布说明](Gameplay/dungeon-loading-publication-20260924.md)。本次只做源码整理和推送检查，未重新运行游戏测试。

## 流体特效与交互（2026-09-24）

恢复本机 `Content/Fluids`、枪口 V14 密度／V15 系统、火系流体燃烧场、血液新材质、冰锥冷雾及喷泉／地牢水面与腐液的既有依赖。原始 Mantaflow 源、缓存、图集、UE 包和制作回执留在本机；源码仓库不替代完整内容备份。重建顺序、68 份退役快照／自动备份的 trash 清单、许可和未测试边界见 [流体整理与恢复](Fluids/fluid-publication-20260924.md)，后续制作遵循 [流体特效工作流](../skills/ue5-fluid-vfx-workflow/SKILL.md)。

## 突变体-3 狂奔、爪型与飞扑（2026-09-23）

恢复 KhaimeraV2 主体/骨架/9 段动作、SurfacePolish 四贴图与 MI、Effects 落地材质和声音，并保留 Meshy 原物理/Death/Stagger、共享感染母材质、AI 与合法 Fab 纹理/音源。先完整身体重排，再叠加飞扑手部旋转，最后安装表面修订；完整依赖、76 份归档及本次源码发布边界见 [突变体恢复与发布](Monsters/Mutant3FeralPublication20260923.md)。用户反馈基本成功，本次整理未运行游戏测试；二进制仍留本机。


## 近战手臂开口、相机顺序与突刺双肘（2026-09-23）

当前标准柄/长柄下砍保留肩部避让 V1，第三段突刺叠加 ThrustElbowSupportV1；共用剑组件在相机缓存前更新。正式动画、实际手模、密集输入、完整可编辑源与回执保留本机，Git 只发布源码和制作方法。恢复顺序、411 份退役取帧文件的归档及未进行本次游戏验收的边界见 [近战手臂发布与恢复](Weapons/melee-arm-publication-20260923.md)。


## PKM 低模重建（2026-09-23）

当前 PKM 是 `PKMLowpoly20260922`，与下文退役的早期 Meshy `PKM20260921` 不同。恢复本机 `Content/Weapons/PKMLowpoly20260922` 的模块化枪体、五类握姿动作、干湿材质、绿色弹箱、配件、脚架和原声资产，同时保留共享 Manny／QBZ-191／AKM 等依赖。最新空仓尾段来自 Charge34，声音来自 ChargeAudio35；作者链、31 项归档及公开源码／本机素材边界见 [PKM 低模恢复与发布](Weapons/pkm-lowpoly-publication-20260923.md)。最新后台构建成功，未运行实机验收。

## 早期 Meshy PKM 分支废案（2026-09-22）

用户已否定并退役本轮 PKM，`SourceAssets/PKM20260921`、`Content/Weapons/PKM` 及专用接入头文件归档至本机 `trash/pkm-rejected-20260922`。武器目录、初始发放、动作/材质引用、预加载和 cook 入口已移除；这些 PKM 包不再属于当前运行内容恢复清单。全部修订均不得按“最新版”自动恢复。范围、SHA-256 清单、构建限制及公开发布边界见 [PKM 废案归档](Weapons/pkm-retirement-20260922.md)。


## 近战旋风与战术冲刺（2026-09-21）

恢复旋风V5并应用V6后摇，保留V2/V3后处理与边框修订；战术持剑采用V4六条移动动画、V5两条0.25秒前摇攻击动画。当前源、顺序、90份归档散列、许可与源码／本机素材边界见 [近战发布与恢复](Weapons/melee-publication-20260921.md)。最新前摇已通过Live Coding，公开源码不包含完整动画或参考视频，运行效果仍由用户测试。

## 唯一巫婆与重建依赖（2026-09-22）

用户指定只保留 F6「巫婆·重建候选」作为唯一巫婆。当前模型、八个动作、Fabric09 布面和 Drape07 位于 `Content/Monsters/WitchRebuilt`；普通巫婆和 Foundation 的独立运行入口退役。原生构建、旧包归档及实际接入状态见 [唯一巫婆](Monsters/witch-single-variant-20260922.md)。Foundation 模板网格/骨架/物理、原 Meshy 外观贴图及法杖和外部动作源仍是保留版本的依赖，不能按目录名一并删除。

当前包含 FlightDistance12 投瓶/距离修正及 LiquidProjectile13 普通毒弹表现。公开源码、有效作者输入、未采用 MeshLab 实验与自动备份的 trash 归档边界见 [巫婆发布与恢复](Monsters/witch-publication-20260923.md)；最新修订未进行游戏或性能测试。

### 历史：巫婆暂停与人体候选（2026-09-21）

当时普通巫婆 V06/V07 未获用户满意，暂停开发；独立 `WitchFoundation` 人体待机/慢走粗模可用，保留两个 F6 入口作对照。此入口安排已被上方唯一巫婆决策替代。原始素材、分件、恢复依赖与当时的 trash 散列清单见 [巫婆暂停与发布](Monsters/witch-paused-publication-20260921.md)。公开仓库只发布代码、作者脚本、参数和文字；Meshy 模型/PBR、Epic Quinn 与动作、UE 包、密集姿态采样留在本机，不能从 Git 克隆恢复完整外观。

## 大旋风 V4（2026-09-20）

恢复普通柄和加长柄 `A_RuneSword_WhirlwindV4`、`Skills/Whirlwind20260920/M_WhirlwindFocus` 与 `ForegroundV3`，保持前景材质JSON映射。保留Manny握持源、ChargedErgoV43母版、共享双臂求解器及V4可编辑源；旧V1–V3动画已归档，V2背景模糊/V3前景材质作者源仍有效。公开脚本与本机授权素材边界、98份归档清单、最后移动限制尚待构建的状态见 [大旋风整理与源码发布](Skills/whirlwind-publication-20260920.md)。

## 丘陵河岸、天空与地表加载（2026-09-20）

恢复 `WorldGeneration/TemperateHills` 的地表、河岸生态、卵石、水体、天空和 `DA_TemperateHillsStreaming`，以及原有 PN/Normandy、WaterMaterials、PWL 和 Fab 河岸来源。当前重建入口、树木再生接入、旧材质归档及源码/本机素材边界见 [丘陵发布与恢复](WorldGeneration/hills-publication-20260920.md)。地表最后使用 `build_hills_ground_v2.py`，不要让旧三层脚本覆盖；进入范围改为附近约 96 m，加载修复已完成 Editor 构建，实际清晰度及耗时待用户测试。

## 双手伐木斧与矿镐（2026-09-20）

运行需要 `Items/ProductionTools/BattleAxe20260919`、`GripMotion20260913`、`RusticPickaxe20260919` 及两种竖直背包图标。当前动作源、导入顺序、骨架/声音依赖和本机归档见 [采集工具发布与恢复](Weapons/production-tools-publication-20260920.md)。公开代码与调参；用户 Meshy 源、Manny/Fab 派生资产、完整骨架采样、贴图与音频保留本机。矿镐沉重反馈已于 2026-09-20 完成正式 DLL 构建，未重新进行实机测试。

## 采集工具强化外观档（2026-09-25）

运行需要 `Items/ProductionTools/Enhance20260925`（2 个母材质＋8 个等级实例）、拆槽后的 `SM_BattleAxe`／`SM_RusticPickaxe`（槽 Metal/Wood）、拆槽视模 `SK_Harvest_Axe`／`SK_RusticPickaxe` 与重烘的 `ColdSteelData/ProductionTools/{axe,pickaxe_upright}` 图标。作者源与可复跑脚本在本机 `SourceAssets/ToolEnhance20260925/`（拆槽、视模拆槽 blend、图标渲染、commandlet 安装与回执）；被覆盖的 6 个网格 FBX 与 2 个旧图标原件在 `SourceAssets/ToolEnhance20260925/Before/`，散列见同目录 `before-backup.json`。设计与阶段记录见 [采集工具强化系统设计](Weapons/tool-enhancement-design-20260925.md) 第 2、11 节；目录自检 `Tools/Production/check_tool_enhancement_consistency.py`。未做实机验收。

## 云层、雷电与柔和火光（2026-09-19）

本轮需要恢复项目云/天空材质、四张引擎云纹理、三段 `Weather/Audio/S_Thunder_I/II/III` 派生雷声，以及火把柔光实例和 `NS_FPS_MuzzleFlashV10`。具体路径、制作顺序、音频来源及归档边界见 [天气与火光发布整理](Weather/weather-lighting-publication-20260919.md)。源码及散列元数据公开，原始/派生音频、uasset、第三方素材与 trash 保留本机。

## 怪物材质统一与僵尸犬 V5.1（2026-09-19）

本轮恢复需要胖子共享母材质 `Monsters/Shared/InfectedSurfaceV1`、胖子/手脑/毒蛆/突变体的 `StyleV1` 资产，以及僵尸犬 `RefinedWoundsV5`、其 V1/V3/V4 有效上游资源和原狼动作。来源、恢复顺序、F6 接入、归档与公开发布边界见 [怪物材质发布说明](Monsters/monster-surface-publication-20260919.md)。Blend、FBX、贴图、uasset 和密集骨架/表面坐标输入留在合法本机素材中；源码发布不是完整资产远程备份。

## 建筑喷泉、星图穹顶与面板（2026-09-19）

当前喷泉采用V8随机溢流和V9石材／双层循环水声（三倍播放音量），凉亭采用C4白色大理石真实星座穹顶；建筑面板保留完整装配预览与冷钢字体。运行资产、V7/V8重建依赖、C4原主体备份、CC0声音和BSD星图来源，以及本机归档范围见 [建筑精修发布整理](Building/building-polish-publication-20260919.md)。公开代码不包含UE资源、模型、音频、字体或预览二进制，需从合法本机素材恢复。


## 寒晶剑模块化与三款握把（2026-09-19）

用户已确认拆分改造结果。恢复 `/Game/Weapons/FrostCrystalSword20260915/Modules20260915`、`GuardsSmooth20260915`、`PommelsRepair20260915`、`Grips20260919`（含 LongGripAnimations）以及 `/Game/Weapons/MeleeRunes20260915/SurfaceV2`。保持 `Content/ColdSteelData/frost-sword-modules.json` 的模型/动画路径、部件位置与符文范围一致；图标从本机 `AttachmentIcons20260913/ue_frost_crystal_sword_*` 恢复。

作者源依赖 Meshy 原剑、已接受手臂/原剑动画与现有共享材质。Blend/FBX/uasset、生成 GLB/PBR、逐帧派生动作及接口密集网格数据保留本机，Git 发布可复用代码、作者脚本和恢复说明。具体来源链与归档记录见 [寒晶模块化发布](Weapons/frost-sword-modular-publication-20260919.md)。

## 火球写实命中（2026-09-14）

恢复 `Content/Skills/Fireball/ImpactRealistic20260914` 的爆燃系统、材质、混音和声音衰减资源。新命中引用由 `FPSFireballComponent` 加载，原悬浮／飞行资产仍沿用现有路径。作者入口为 `Tools/Skills/build_fireball_impact_realistic.py`；运行前从 `SourceAssets/FireballImpactRealistic20260914/author_audio.py` 生成混音，保留 Epic `T_Explosion_EOO`／法线、已有薄烟和 `Realistic_Starter_VFX_Pack_Vol2/T_NoiseNormal_A` 的授权依赖。材质制作需真实 RHI 编译。详见 [写实命中接入](Skills/fireball-realistic-impact-20260914.md)。

## 火球流体燃烧贴图（2026-09-14）

同日镜头残影／悬浮热浪调整增加 `M_FluidThinWispMotion` 与 `M_FluidHoverHeatHalo`，继续使用原运行系统路径。热浪依赖剑气同源的 `Realistic_Starter_VFX_Pack_Vol2/Textures/T_NoiseNormal_A`；增量恢复入口为 `Tools/Skills/tune_fireball_motion_heat.py`，完整流体生成器也已同步。参数、备份及未测试范围见 [镜头残影与悬浮热浪](Skills/fireball-motion-heat-20260914.md)。

恢复 `Content/Skills/Fireball/FluidBurn20260914` 的两套纹理／材质，以及更新后的 `NS_FireballSlowBurnCore`、`NS_FireballVelocityTrail`。作者目录 `SourceAssets/FireballFluidBurn20260914` 保存原创 Mantaflow 模拟、可编辑 Blend、缓存、场数据、图集烘焙脚本和两张 RGBA 图集；保留 Epic Niagara Examples 薄烟／热扰动、Dr.Game Free Spline VFX 短外焰及现有父材质依赖。已有两张图集时，运行 `Tools/Skills/build_fireball_fluid_burn.py` 完成 UE 恢复；完整 `build_fireball_assets.py` 已把这一阶段加入末尾。制作与用户测试边界见 [流体燃烧主体](Skills/fireball-fluid-burn-20260914.md)。

## Meshy 胖子僵尸（2026-09-14）

恢复 `Content/Monsters/FatZombieMeshy` 的网格、Skeleton、物理资产、四段 Animations、Materials/Textures、Pus；动作重建还需 Sources/Rig/RetargetedRaw。主场景保留 `Content/GameMaps/DayNight_Lighting.umap` 与 `Geometry/SM_MainGround_Subdivided`，以及适合怪物胶囊尺寸的导航。脓液素材依赖 WaterMaterials 的河流法线、泡沫及 RuralAustralia 的浑水遮罩，继续按原素材来源恢复。

作者源为 `SourceAssets/FatZombieMeshy20260913`：用户 Meshy ZIP/解包模型、原蒙皮 Blend、成品 Blend/FBX、prepared、native_retarget、四张 PBR 和当前 UEAuthoring。制作顺序与来源见 [作者说明](../SourceAssets/FatZombieMeshy20260913/README.md)，运行和归档边界见 [本次整理](fat-zombie-workflow-publication-20260914.md)。Mesh2Motion 动画的 CC0 许可不覆盖 Meshy 模型或水体资产；本次只发布源码、制作脚本和必要文字记录，不公开上述二进制。

命中反馈的可选音效路径为 `Content/Audio/PlayerHitFeedback20260914/S_Player_MonsterHit`；缺少音效不影响真实生命条、命中和击杀文字。完整本机 F6 开发面板还包含并行的基本调参页，本次怪物核心源码未将整个控制器/UI 并行改动一并发布。


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

恢复 `Content/NiagaraExamples`（已获授权的 Epic Niagara Examples Pack）及 `Content/Weapons/GunplayFX`。当前引用为 `NS_FPS_MuzzleFlashV10`、`NS_FPS_MuzzleSmokeStreamV12`、`M_BallisticTracerVisibleV12`，以及枪口后备、烟、弹壳材质；以下 V5–V11 记录保留作者依赖与迭代过程。第三方派生 Niagara uasset 仅本机保留，本次没有上传其二进制。

基础生成器 [build_muzzle_presentation_v5.py](../Tools/AssetPipeline/build_muzzle_presentation_v5.py) 直接以原包 `FX_Weapons/MuzzleFlashes/NS_MuzzleFlash` 重建，不需要 trash 中的旧候选。需项目 `RainAssetEditor`、UE 5.8 NiagaraToolset 和原始素材；`-MuzzleRebuildProbe` 写独立测试资产。当前曳光材质由 [V6 制作器](../Tools/AssetPipeline/build_gunplay_presentation_v6.py) 创建基础，再用 [V12 制作器](../Tools/AssetPipeline/build_gunplay_visibility_v12.py) 升级。参数、历史迭代和本机证据见 [烟火记录](muzzle-smoke-presentation-20260911.md)，归档记录见 [清单](gunplay-archive-20260911.json)。

2026-09-13 步枪抛壳源码新增引用原包 `FX_Weapons/MuzzleFlashes/Meshes/SM_BulletShell` 与 `MI_BulletShell_FX`，恢复时连同该目录的颜色/法线贴图和父材质一起保留；没有新增公开分发的第三方二进制。曳光与烟雾升级建议、LPVO 隐藏弹壳规则和未测试交付边界见 [Gunplay 升级建议与抛壳修改](Weapons/gunplay-vfx-casing-20260913.md)。

后续已接入 `NS_FPS_MuzzleEpicV6`、`NS_FPS_BarrelSmokeEpicV6` 和 `M_BallisticTracerSoftV2`。新生成器为 `Tools/AssetPipeline/build_gunplay_presentation_v6.py`，依赖上述 V5 两套系统以及 Epic 原包的枪口烟雾、wispy 材质和配套贴图。保留新材质副本 `MI_MuzzleSmokeV6`、`MI_BarrelWispyV6`；完整当前依赖、构建与未测试边界见 [V6 交付记录](Weapons/gunplay-vfx-v6-20260913.md)。

2026-09-14 烟火继续升级为 `NS_FPS_MuzzleEpicV7`、`NS_FPS_BarrelSmokeEpicV7`，配套 `MI_MuzzleSmokeV7`、`MI_BarrelWispyV7`；曳光仍用 `M_BallisticTracerSoftV2`。运行 `Tools/AssetPipeline/build_gunplay_presentation_v7.py` 从本机 V6 恢复增强烟量和动态焰瓣，保留 V5/V6 作为作者依赖。参数和未测试交付边界见 [V7 交付记录](Weapons/gunplay-vfx-v7-20260914.md)。

同日白烟与火光边缘精修转为 V8 两套 Niagara 系统，新增 `M_MuzzleFlashFeatherV8` 及四项烟火材质实例。`Tools/AssetPipeline/build_gunplay_presentation_v8.py` 依赖 V7、Epic `M_SmokeAndFire_Sprites` 母材质及其纹理/材质函数；保持原包和 V7 作为重建输入。完整资产名与参数见 [V8 交付记录](Weapons/gunplay-vfx-v8-20260914.md)。

后续 V9 改为 `NS_FPS_MuzzleFlashV9` 与独立 `NS_FPS_MuzzleSmokeStreamV9`：手枪火光缩放、步枪保留 V8 火光，烟雾改为连续供烟和扩散。`Tools/AssetPipeline/build_gunplay_presentation_v9.py` 依赖 V8；新材质 `M_MuzzleSmokeSheetV9` 从项目源 `SourceAssets/GunplayVFX20260914/ContinuousSmoke.hlsl` 创建。原资产与 V8 继续作为恢复输入，见 [V9 交付记录](Weapons/gunplay-vfx-v9-20260914.md)。

V10 使用 `NS_FPS_MuzzleFlashV10` 和 `NS_FPS_MuzzleSmokeStreamV10`，扩大白烟扩散、增加停火余烟并细化火光柔边。`Tools/AssetPipeline/build_gunplay_presentation_v10.py` 从 V8/V9 创建新版，烟材质沿用已修复 Niagara Sprite 标记的 V9；新增火光源为 `SourceAssets/GunplayVFX20260914/FlashFeatherV10.hlsl`。见 [V10 制作记录](Weapons/gunplay-vfx-v10-20260914.md)。

V11 烟雾降低透明度与累积烟量、加快消散，并保留连续扩散和少量余烟，以持续射击视线清晰为先。`Tools/AssetPipeline/build_gunplay_smoke_v11.py` 依赖 V9 材质及 V10 烟系统，创建 `M_MuzzleSmokeSheetV11` 与 `NS_FPS_MuzzleSmokeStreamV11`；火光保持 V10。作者源为 `SourceAssets/GunplayVFX20260914/SmokeSightlineV11.hlsl`，见 [V11 调整记录](Weapons/gunplay-smoke-v11-20260914.md)。

当前烟雾和曳光使用 V12：恢复新生烟气密度，保留短寿命，并补足曳光端部发光及可见宽度。`Tools/AssetPipeline/build_gunplay_visibility_v12.py` 从 V11 烟雾和 V2 曳光创建 `M_MuzzleSmokeSheetV12`、`NS_FPS_MuzzleSmokeStreamV12`、`M_BallisticTracerVisibleV12`；火光仍为 V10。材质源在 `SourceAssets/GunplayVFX20260914`，见 [V12 调整记录](Weapons/gunplay-visibility-v12-20260914.md)。

## 云、雨与附着水滴（2026-09-12）

先恢复 `Content/Weather/NaturalV2/DA_WeatherPresentation.uasset` 基础表现库。恢复既有 `Weather/VFX`、`PWL_Light_Manager/Shader`、M4InfimaV3、M4HK416Replica、AKM SovietFab 和现用配件后，编译 FPSGAMEEditor，再运行 [天气生成器](../Tools/Weather/build_natural_weather.py)。它以本机已授权资产生成 39 个独立副本及程序化材质，不下载资源。原始 HLSL 位于 `SourceAssets/WeatherNatural20260912`；新库中的枪械及天空材质仍依赖原包纹理与函数，不能把衍生 uasset 当作可自由分发的美术包。具体范围、控制参数与验收见 [天气升级记录](WeatherNaturalUpgrade-20260912.md)。

随后运行 [雨滴可见性修正生成器](../Tools/Weather/fix_rain_visibility.py)，生成 `Content/Weather/RainVisibility` 下四个修正版资产。当前运行入口是该目录的 `DA_WeatherPresentation`；它沿用 NaturalV2 的屏幕、枪械、天空与其余雨效，仅替换下落雨丝和水坑材质。原始雨丝着色器在 `SourceAssets/RainVisibility20260912`，详见 [雨滴与水坑修正](RainVisibility-20260912.md)。两个生成器都通过 UE Python commandlet 执行。

## 冷钢玻璃改造台（2026-09-12）

保留 `Content/UI/GunsmithWorkbench/T_WorkshopBackground`，恢复同目录 `ColdGlass` 中的九张分类纹理与 `M_CategoryIcon`，以及 `Fonts` 中四份字体、两个 OFL 许可和 provenance。字体可用 [准备器](../Tools/UI/prepare_cold_glass_fonts.py) 从固定官方提交重新下载；分类图标需本机 `SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1` 原图，再通过 UE Python 运行 [导入器](../Tools/UI/import_cold_glass_icons.py)。本机 PNG 保持 RGB，透明效果由 UI 材质完成。详见 [接入与验证](UI/gunsmith-cold-glass-implementation-20260912.md)。


## QBZ191 与逐枪配件涂层（2026-09-13）

保留本机 `Content/Weapons/QBZ191` 的 Refined20260913、Attachments20260913、MetalCoat20260913 及其骨架、源纹理和当前机械瞄具；基础枪身/弹匣来自用户提供的 QBZ191 包，许可边界见 `SourceAssets/QBZ19120260912/provenance.json`，不可公开原素材。手臂和参考动作沿用已有合法 M4/Manny 来源。

M4/AKM 新材质变体位于 `Content/Weapons/AttachmentFinish20260913/{M4,AKM}`，包含 14 个网格、逐槽材料和 M4 机匣裁片。它们仍依赖原配件法线、光学材料、M4InfimaV3 材质函数和 AKM SovietFab ArmSupport 枪钢纹理；先恢复这些来源，再使用 `SourceAssets/WeaponAttachmentFinish20260913` 中导出、纹理准备、UV 制作和导入脚本。QBZ 涂层依次运行其 MetalCoat 目录的 export_current、bake_coating、record_export_slots、import_coating、finish_editable；输入及前置版本见 [材质记录](Weapons/qbz191-receiver-coating-20260913.md)。

最终可编辑源、贴图与已交付预览保留本机，不提交 Git。公开制作脚本需要已有授权资产，不能单靠克隆仓库恢复画面。归档及本次发布范围见 [整理记录](Weapons/weapon-publication-20260913.md)。

## 感染矿工退役（2026-09-13）

感染矿工整案已判废，`Content/Monsters/InfectedMiner`、`Content/Tests/InfectedMiner`、两日作者源与专用代码/工具移入本机 `trash/infected-miner-rejected-20260913`。恢复 Content 时使用已删除 `InfectedMiner_Village_01` 的村庄关卡，不从旧快照恢复该矿工；共享护士、AI、EBS 动作库继续保留。废案边界与逐文件散列见 [废案记录](Rejected/infected-miner-20260913.md)。trash 和授权不允许再分发的原始素材不在公开仓库内。

## Meshy 共振握把与高性能后托（2026-09-13）

- 共振握把作者入口：[MeshyIntegration](../SourceAssets/ResonanceGrip20260913/MeshyIntegration/README.md)。本地源 Selected_Meshy_Source.fbx 的原路径与 SHA256 见 source.json；每枪参考 FBX、输出 Blend/FBX/GLB 和微表面贴图需从合法本地备份恢复。仍依赖 AngledForegrip20260910/WristNatural 的 M4 idle Blend、其引用库，以及 ResonanceGrip20260913/Repaired91871/Game 的三枪材质区域参考 Blend。
- 后托作者入口：[MeshyPerformanceStock20260913](../SourceAssets/MeshyPerformanceStock20260913/README.md)。用户 ZIP 的路径和 SHA256 见 provenance.json；Source/、Imported.blend、Textures/ 和三枪输出均为本地依赖。
- 材质依赖：WeaponAttachmentFinish20260913 的 M4 机匣纹理、AKMArmSupport20260911/Metal、StableAntiSlipRearGrip20260913/Selected91727/Textures。UE 需恢复 AttachmentFinish20260913/M4/Textures、AKMIntegration/SovietFab/ArmSupport/Textures 和引擎 MF_PhongToMetalRoughness。
- 运行 Content：Weapons/ResonanceGrip20260913/MeshyIntegration 与 Weapons/QRPerformanceStock/Meshy20260913，下含 M4、AKM、QBZ191 专用网格/材质。先恢复已有枪体、骨架和装配依赖，再按作者及导入脚本恢复资源；只克隆源码不能得到可运行的完整模型工程。
- 本次使用 Repaired91871/ImportHost 内容宿主导入，其 Content 是正式 Content 的目录联接，不可递归移走或删除；主项目曾有 AutoFootstep 启动冲突，此方法不代表该冲突已修复。
- 用户提供资源的公开再分发权尚未确认，源 ZIP/FBX、贴图、Blend、GLB、uasset 及渲染不提交公开仓库。保留源与当前资源，仅归档明确淘汰版本，见 [清单](AssetArchives/resonance-meshy-20260913.json)。本次整理未启动游戏测试。

## M1911 手枪（2026-09-13）

公共仓库包含手枪运行代码、物品/枪匠参数、制作/导入脚本、来源记录和审计入口。完整枪体、手臂、原始 P9 动作及其采样、Blend/FBX/uasset、贴图与音频保留本机；克隆仓库本身不恢复完整模型画面。M1911、Manny、P9、枪钢、光学和声音分别沿用各自许可，第三方 GitHub 镜像不能作为原资产再分发授权。

- 当前枪身：`Content/Weapons/M1911/RearFinish20260913`；当前动作：`Contact20260913` 的待机/射击/拔枪以及 `ReloadReady20260913` 的普通/空仓换弹。枪声仍依赖 `Integrated20260913/Audio`。不要将整份 Integrated 目录当废案删除。
- 配件：`CompactFit20260913` 的全息/普通消音器/激光/手电；`MuzzleRedDot20260913` 的制退器；`SculptedMount20260913` 的全景红点。保留 `Attachments20260913/Materials`、`Tactical20260913/Materials` 和 Wet 依赖，以及来源 M4 光学玻璃/分划、枪口内腔材料。
- 后部涂层与雨滴：从 `SourceAssets/M1911RearRain20260913/install_finish_and_rain.py`、`M1911Tactical20260913/register_rain.py` 恢复实际材料映射，包括 RainVisibility / NaturalV2 的 `DA_WeatherPresentation`；需先恢复项目天气母材质与参数。
- 图标：恢复本机 `Content/ColdSteelData` 中 M1911 原厂图标、`AttachmentIcons20260913` 的轻型扳机、短/长枪管、枪口及战术配件图标。动态武器图标还依赖既有 GunsmithWorkbench 的工作室环境和预览材质。
- 源重建顺序及保留输入见 [手枪标准](../skills/ue5-weapon-workflow/references/pistols.md)。首先恢复当前 M4/Manny 可编辑源、用户 M1911 FBX 与合法取得的 P9 源；旧源目录即使不再直接加载，仍可能参与重建。
- 已退役首版输出和备份位于本机 `trash/m1911-development-20260913`；[归档清单](AssetArchives/m1911-development-20260913.json) 保存原路径、替代物和散列。[审计记录](Weapons/m1911-development-audit-20260913.md) 区分本次检查与历史未测试制作。

## 表面命中反馈（2026-09-14）

运行资源位于 `Content/Weapons/GunplayFX/Impacts`，由 [制作入口](../Tools/AssetPipeline/build_surface_impact_assets.py) 在 UE Python commandlet 中生成，包含实例化火星/粉尘/碎屑材质、弹痕及 18 个短命中音效。作者源 `SourceAssets/SurfaceImpacts20260914` 使用本项目原创程序化 HLSL 和合成 PCM；几何及淡出依赖引擎 BasicShapes Plane/Cube 和 DitherTemporalAA 函数，不必复制 Niagara 命中示例包。先生成资源，再编译原生世界共享池；仅源码不能替代本机 uasset。表面绑定规则、固定性能预算、枪型后坐力参数与未测试范围见 [接入记录](Weapons/gunplay-impacts-recoil-20260914.md)。

肉体血雾后续升级还需恢复合法本地包 `Realistic_Starter_VFX_Pack_Vol2` 的 `T_Smoke_Wisp`、`T_Droplets_A`，再运行 [血液材质制作器](../Tools/AssetPipeline/build_flesh_impact_assets.py)，生成 `Impacts/Blood` 中的血雾和血滴两个材质。作者 HLSL 和来源记录在 `SourceAssets/FleshImpacts20260914`，未改源包或新购资产；血液材质仍引用第三方贴图，不作为可独立公开再分发的素材包。初版参数仅作为历史记录，见 [血雾接入记录](Weapons/flesh-impact-blood-20260914.md)。

当前落地血迹使用 `M_FleshStainV2`，还需运行 [落地血迹 V2 制作器](../Tools/AssetPipeline/build_flesh_ground_v2.py)。它沿用同一来源贴图，扩大血迹轮廓并加入共享材质的湿/干变化；最新预算为 192 活动命中粒子、48 独立血迹贴花及原有 24 普通弹痕。恢复说明、历史构建和用户确认以 [V2 记录](Weapons/flesh-impact-ground-v2-20260914.md) 为准。已退役文件及保留的制作依赖见 [本轮整理记录](Weapons/gunplay-publication-20260914.md)。

## 改造配件图标：水平左向与单件机瞄（2026-09-14）

当前图标加载优先使用 `Content/ColdSteelData/AttachmentIcons20260913` 中的武器专属透明 PNG，再回退共享 PNG；分类图也使用同一透明规则。恢复本轮 104 张 PNG 和对应 UE Texture，不能仅恢复旧黑底分类图。5 张已接受枪托 PNG 保留，99 张替换／新增图已在本机导入。实际模型渲染和含第三方资产的可编辑场景保留本机，未核准为可公开再分发素材。精确图标哈希、来源、脚本依赖和制作阶段构建记录见 [配件图标发布与恢复说明](Weapons/attachment-icons-publication-20260914.md)。

## Dan-Wesson 715（2026-09-14）

当前资源入口、Fab/Manny/用户录音许可边界、保留的上游制作链及恢复顺序见 [715 资源恢复说明](Weapons/dan-wesson715-publication-20260914.md)。主体保持 Chrome，手电/激光/全息镜使用独立聚合物材质。两轮已否决模型在本机 trash 归档，清单见 [715 废案记录](Rejected/dan-wesson715-models-20260914.md)。二进制及受许可约束的密集派生数据不进入公开源码。

## 闪电（2026-09-20）

恢复已许可的 Dr.Game Free Spline VFX 原包 `/Game/_SplineVFX`、`SourceAssets/Lightning20260920` 中的图标与两层原施法音频。`Tools/Skills/prepare_lightning_sources.py` 从原 game-dev 音频转码，`Tools/Skills/build_lightning_assets.py` 经 UE 桥制作 `/Game/Skills/Lightning/NS_LightningChain` 并导入声音；图标恢复已进入 `Tools/UI/prepare_cold_steel_skill_icons.py`。原包和音频派生二进制继续保持本机许可边界。完整来源、数值、三维适配及未测范围见 [闪电迁移](Skills/lightning-migration-20260920.md)。

### 圣光魔法（2026-09-20）

同一已许可原包的 `/Game/_SplineVFX/NS/NS_Spline_Holy` 提供圣光光粒副本。恢复 `SourceAssets/HolyLight20260920` 图标和音频后，通过 `Tools/Skills/build_holy_light_assets.py` 在现有 UE 编辑器内生成 `/Game/Skills/HolyLight` 下的光柱／光池材质、`NS_HolyLightMotes` 和 `S_HolyLightCast`。声音可用 `prepare_holy_light_sources.py` 从原 game-dev 转码，图标可由共用 `prepare_cold_steel_skill_icons.py` 恢复。光柱几何由 `FPSHolyLightEffect` 运行时构造；源脚本与参数为可编辑交付。来源、完整接入与未测状态见 [圣光迁移](Skills/holy-light-migration-20260920.md)。

## 冰锥（2026-09-15）

当前冰体与寒气运行目录 `/Game/Skills/IceSpike/FrostV2`；碎片、命中、冰裂纹贴图与音频仍在 `/Game/Skills/IceSpike`。首轮恢复链：保留 `SourceAssets/IceSpike20260915` 的 `IceSpike.blend`、`SM_IceSpike.fbx`、`ice_impact.wav`、`ThirdParty/CrackedIceSelected/ci_cracks.png` 和许可，UE 执行 `Tools/Skills/build_ice_spike_assets.py`。V2 另恢复 `SourceAssets/IceSpike5080_20260915` 的三视图、TRELLIS 母版、`IceSpike5080_Editable.blend` 与 `Game/` FBX／贴图，再执行 `Tools/Skills/build_ice_spike_frost_v2.py`。生成与导出入口为该源目录的 `generate.py` 和 `Tools/Skills/author_ice_spike_5080.py`，前者不会自动生成验收渲染。图标恢复由 `Tools/UI/prepare_cold_steel_skill_icons.py` 处理。依赖已有 Epic Niagara Examples、火球拖尾结构和 Realistic Starter VFX Pack Vol2，二进制原素材沿用许可边界，不公开提交。详见 [5080 模型与寒气升级](Skills/ice-spike-frost-v2-20260915.md)。

GitHub 冰裂纹采用 MIT（Shader Vault），已保存并随 `Content/ColdSteelData/Licenses/CrackedIce-MIT.txt` 打包。完整来源及生成提示见 `SourceAssets/IceSpike20260915/provenance.json`，迁移公式与范围见 `Docs/Skills/ice-spike-migration-20260915.md`。本轮未测试或渲染验收。

## 2026-09-19 枪械快速近战收尾

M4 N、AKM／ASH-12 跨枪适配、QBZ191 O 与 recover 衔接的运行路径、有效作者依赖、废案归档及公开恢复边界，见 [快速近战发布与恢复](Weapons/quick-melee-publication-20260919.md)。Blend／FBX／uasset、原始参考及密集骨骼数据继续仅保留本机；公共源码不包含完整资源包。

## 扩容弹匣（2026-09-19）

当前四枪作者入口、保留输入、最终资源及本地素材恢复边界见 [扩容弹匣发布记录](Weapons/extended-magazines-publication-20260919.md)。未经审核再分发许可的模型、纹理、动画和完整采样数据保持本地。

## ASH-12 配件、动作与专属声音（2026-09-20）

当前表面、参考换弹／右侧拉栓、战术冲刺、通用瞄具与握把、托腮板、战术枪口、左侧激光／手电及音频的本机恢复路径与源码发布边界，见 [ASH-12 发布与恢复](Weapons/ash12-publication-20260920.md)。公开代码不包含第三方模型／贴图、手模与动作二进制、用户原声及衍生音频。专属消音声已导入并完成当前进程 Live Coding，基础 DLL 仍待后续常规构建。

## 六款剑类通用配重（2026-09-20）

用户已认可符文长剑与寒晶剑的六款共享方案。[最终恢复入口](../SourceAssets/SixSharedSwordPommels20260920/README.md) 和 [整理清单与发布边界](Weapons/six-sword-pommels-publication-20260920.md) 记录当前依赖。

- 先恢复四份现行数据：`melee-gunsmith.json`、`rune-sword-modules.json`、`frost-sword-modules.json`、`shared-sword-pommels.json`，均在 `Content/ColdSteelData`。
- 本机保留的 UE 内容包括 `Weapons/AzureRunesword20260913/Modules20260919`、`Weapons/AzureRunesword20260913/Pommels20260920`、`Weapons/FrostCrystalSword20260915/PommelsRepair20260915`、`Weapons/SharedSwordPommels20260920` 以及对应附件图标。原手臂／动作／长柄动画和上游材质继续恢复原已许可版本。
- 四个本轮作者目录中的 Blend／Export／Textures／Icons 和实际接口采样继续留本机。还需要 FrostSwordModules20260915、FrostSwordPommelsRepair20260915、MeleeGuards20260915 的已许可输入；脚本不是这些素材的替代品。
- 现行脚本最终入口为 `SourceAssets/SixSharedSwordPommels20260920/install_catalog.py`。旧三款安装器与回滚目录已归档，恢复时不要重跑；`restored-options.json` 保留恢复款原属性和独立 ID。安装器操作现行配置，不重写玩家存档。

公开仓库不包含本轮模型、贴图、图标、uasset 和密集几何采样；重建前需在本地恢复输入并调整作者脚本中明确的宿主路径。必要 native 构建照常进行，游戏测试由用户按需执行。

## M16A2（2026-09-20）

用户已确认最新换弹回位与四款枪托接口修复成功。正式物品 `ue_m16a2` 的源码、三连发数据、作者依赖和废案归档见 [M16 发布与恢复](Weapons/m16-publication-20260920.md)。当前 Content、Manny/M4 上游动作、原模型 PBR、用户 M16 原声及密集几何/姿态输入保留本机，不公开上传。恢复时保留 Refinement → M4Insert → RemovalMelee 作者链，并最后安装 RecoveryStocks 四款枪托；AuthoringRecovery 中仍被正式资产引用的 8 个包不能随旧失败包一起删除。

## 2026-09-20 双持快速近战与冲刺下砍

双持改造后完整转枪 V5、双手剑全段伸展 V5、保留腕部 V4 及竖直扰动的当前运行路径、有效作者依赖与废案恢复，见 [发布说明](Weapons/dual-melee-overhead-publication-20260920.md)。合法本地 Blend／FBX／uasset、密集姿态输入和参考视频不公开提交；DW715 形变反馈仍待定位，不将静态骨轨道刚性记为问题已修复。

## A762 与数字弹药袋（2026-09-21）

A762 当前模型、配件、统一瞄具材质、目录图，以及 LP绿／PS蓝／AP红三款弹药图的本机恢复目录、制作顺序和来源边界，见 [本轮发布记录](Weapons/a762-ammo-publication-20260921.md)。公共仓库包含源码、目录与制作脚本；模型、动画、PNG、UE 资源和密集采样保持本地。基础弹药袋构建记录早于最终弹种更新，最新弹种改动仍待编译，未做游戏测试。

## 陨星坠落与灼锋焰甲（2026-09-21）

最新火焰为 RealisticV5：恢复本地 `Realistic_Starter_VFX_Pack_Vol2`、`MilitaryTrench` 及下述旧火系作者链，通过 MCP 桥执行 `Tools/Skills/build_fire_magic_realistic.py` 的 `materials → weapon → aura → mantle → trail → ground → impact`，输出 `/Game/Skills/FireMagic20260921/RealisticV5`。五个材质、六个 Niagara 系统覆盖两项技能的火焰，写实 V3 岩体继续使用。来源、参数、构建和未测范围见 [Realistic V5](Skills/fire-magic-realistic-v5-20260922.md)。

SplineV4 为历史候选及 V5 容器来源：恢复本地 `_SplineVFX` 包及旧火系制作依赖后，通过 MCP 桥执行 `Tools/Skills/build_fire_magic_spline.py` 的七个阶段，输出 `/Game/Skills/FireMagic20260921/SplineV4`。其原材质曝光修复和 GitHub 参考见 [Free Spline VFX 替换](Skills/fire-magic-spline-vfx-20260921.md)。

陨星主体最新为写实 V3：恢复 RuralAustralia 的 `StaticMeshes/Rocks/Rock_M_02`、`Presets/M_Nature_01` 及其材质函数/细节贴图依赖，运行 `Tools/Skills/build_meteor_realistic.py` 的 `material`、`mesh` 两阶段，输出 `/Game/Skills/FireMagic20260921/RealisticV3`。当前 C++ 主体与碎片均取此目录，外层火焰使用上述 RealisticV5。记录见 [写实陨星](Skills/meteor-realistic-assets-20260921.md)，素材与制作回执在 `SourceAssets/MeteorRealistic20260921`。

V2 作者链作为恢复输入保留：另恢复 `SourceAssets/FireMagicPolish20260921`，运行图标使用 `meteor_hex.png` / `flame_armor_hex.png`。恢复下述初版依赖后，通过 MCP 桥对 `Tools/Skills/build_fire_magic_polish.py` 依次执行 `materials`、`mesh`、`weapon`、`mantle`、`trail`、`ground`，资产保存到 `/Game/Skills/FireMagic20260921/PolishV2`。模型后处理依赖本机 Vibe3D；火舌材质复用 `/Game/Skills/Fireball/TorchBurn20260921/M_FireballTorchErosion`。作者源与出处见该 SourceAssets 目录 `provenance.json`，实现见 [V2 计划](Skills/fire-magic-polish-plan-20260921.md)。保留旧图标和初版资产以支持重建；不再将旧方框图标写回当前技能定义。

恢复本机 SourceAssets/FireMagic20260921 及青铜火把、Vefects Free Fire、Niagara Examples、EasyBuildingSystem 依赖。使用 Tools/Skills/prepare_fire_magic_sources.py 准备原音频与图标，再经 UE MCP 桥分阶段执行 build_fire_magic_assets.run；运行资产集中于 /Game/Skills/FireMagic20260921，复用已有火球飞行拖尾、写实爆炸与热浪。共用技能图标恢复清单已增加两项。详见 [火系魔法迁移](Skills/fire-magic-migration-20260921.md)。资产已制作保存并完成必要 Editor 构建；未启动游戏或测试。


本对话技能、施法和飞剑的恢复顺序、废案与公开边界见 [2026-09-22 整理发布](Skills/skills-magic-publication-20260922.md)。

## 地牢工作间组合件（2026-09-22 收尾）

当前工作台源为 `SourceAssets/DungeonWorkbenchKit20260921`，货架源为 `SourceAssets/DungeonWorkshopRackPolish20260922`，地图为 `/Game/GameMaps/L_Dungeon_Prototype`。最新完整可编辑源是 `DungeonWorkbenchKit20260921/Authored/DungeonRooms_WithWorkbenchKit.blend`；旧作者目录仍提供材质、对象和整场景装配输入，不能按版本日期整体清除。

本次公开作者脚本、配置、文档和归档索引；FBX／Blender／UE 包、贴图、下载原件和原始回执留本机。Fab 免费工具包等不因免费而具备原件再分发许可。恢复依赖、当前组合件入口、废弃发动机与旧备份归档、未测试范围统一见 [工作间收尾与恢复](Gameplay/dungeon-workshop-publication-20260922.md)。Git 克隆不能替代完整本机素材备份。

## Player world body (2026-09-22)

Manny, separate first/third-person animation, skin reconstruction, local-only dependencies and retirement records: [player-body publication](Characters/player-body-publication-20260922.md).

## 近战符文与高地双手剑（2026-09-22）

本批次发布代码、目录与配方；完整模型、PBR、手臂源、密集采样和 UE 资产留在本机。最终外观、恢复顺序、保留的旧输入与废案归档见 [近战符文发布记录](Weapons/melee-runes-publication-20260922.md)。

## 随机地牢与 Boss 主泵房（2026-09-23）

作者房间、随机目录、门洞修复、粘液与手脑首领接入的源码链和本机资产依赖，见 [随机地牢与主泵房源码发布](Gameplay/dungeon-random-boss-publication-20260923.md)。公开作者脚本、配置及原生代码；关卡、授权素材和导入回执仍从本机与合法来源恢复。被退回的方盒房配方和失效恢复脚本已归档到 trash。构建和地图保存记录不等于游戏测试。

## 地牢性能优化与光照恢复（2026-09-23）

保留恢复后的硬件光追、Lumen、PWL 原预设和 DayNight_Lighting 关卡。当前地牢网格及依赖材质需本机已保存的 Nanite 制作结果；源码克隆不包含 49 个修改网格、72 个材质用途更新和 2 个 ASH-12 静态弹匣材质。作者脚本、剩余资产依赖、25 项废案归档及用户反馈边界见 [地牢性能整理与发布](Performance/dungeon-performance-publication-20260923.md)。旧 RasterProfiles 和全面剔除光追脚本已退役，不从 trash 自动恢复它们。

## SVD 完成、抓握与接口细化（2026-09-23）

恢复当前 SVD 需要本机 `Content/Weapons/SVDDragunov20260922`、跨枪 `Content/Weapons/PSO1Russian20260923` 及共享 Manny／配件资产。当前换弹为用户认可的 `SVDThumbUp20260923`，模型／材质为 `SVDRefinedFinish20260923`；旧 Blend 制作链仍需保留，退役导出与恢复快照按清单归档。来源、当前入口、公开发布边界及本机恢复见 [SVD 发布说明](Weapons/svd-publication-20260923.md)。视频提取音频未获公开再分发许可，公共仓库仅提供脚本与来源记录，不包含音视频本体。
