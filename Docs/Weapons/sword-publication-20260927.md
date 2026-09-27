# 高地改造、通用握柄与幽蓝飞剑发布记录

发布仓库：`https://github.com/allang2208/3D-FPS.git`，从实际工程 `D:/FPS3D/FPSGAME` 精确暂存，普通推送到 `main`。本记录区分本机制作成果与公共源码；没有为整理启动 UE、游戏、渲染或新的运行测试。

## 本轮直接发布

- 高地剑连续接口 V5、棱脊穿甲刃收窄根部 V2、棘冠配重球、两款共用握柄的作者配方与导入脚本；模块目录、改造属性及对应显示字段。
- 符文长剑命中减冷却的武器身份限定；第三段突刺和重击专属韧性快照；改造装配目录缓存随游戏实例刷新。
- 幽蓝灵体剑网格和 Substrate 材质配方、随机爆炸 V4 运行实现、严格按当前主手显隐的 G 槽、新图标及其生成提示词。
- 近战／工具 130 张灰阶图标的制作配方、现有灰阶助手及 SKILL。源网格、纹理、可编辑场景与最终二进制结果仍在本机。

数值：棱脊刃第三段伤害与韧性伤害各 +40%、物理穿透 +10%、基础伤害 −10%；铁脊强攻柄重击伤害 +20%、重击削韧 +30%、攻速 −8%；锁纹稳握柄格挡耐力消耗 −25%、格挡减伤倍率 ×1.10，无伤害惩罚。棘冠快速近战倍率 +0.5、削韧与击退各 +50%、25% 概率一层流血；陨星锤首快速近战多目标且范围不变。

## 与并行代码相交的发布边界

当前工作区还包含其他会话的快速近战动作优先级／取消眩晕／低位小目标判定，以及整个 HUD 金色高亮改造。它们不属于本次提交。

1. 配重的目录、倍率解析、技能数值快照和面板已直接提交；**公共主线尚未接通棘冠流血与陨星多目标命中**。独立交接件为 [配重接线补丁](RuntimeHandoff20260927/sword-pommel-area-bleed.patch) 和 [范围查询函数](RuntimeHandoff20260927/sword-pommel-area-query.cpp.inc)。补丁针对本次公开的旧命中合同整理，保留原合同的眩晕与冷却；不要用它覆盖本机已经改为新动作合同的完整函数。
2. 使用上述查询前，需先整合另一分支的 `MeleeSmallTargetQuery.h/.cpp` 及其 `QueryQuickContact`、`QueryLowSector`、`LivingSmallHand`、`Covered` 等依赖。在命名空间头文件补上 `TArray<FHitResult> QueryQuickAreaContacts(UWorld*, ACharacter*, const FTransform&, const FVector&, float, float);`，查询函数放在其实现文件相同辅助函数作用域可见的位置。它保持原距离／半径、场景遮挡、去重和既有低位补判规则。
3. [快捷栏填充补丁](RuntimeHandoff20260927/sword-quickslot-fill.patch) 只修复 `MakeBox` 未传画刷透明 tint 的问题，依赖未发布的金色 `NativePaint`。主线旧版没有该高亮绘制函数，因此不直接塞入依赖不全的 UI 改造。本机已经包含修复，资料见 [白块问题记录](../UI/fireball-prepared-slot-white-fix-20260927.md)。

两个补丁使用零行上下文，整合依赖并核对相应函数后用 `git apply --unidiff-zero --recount` 应用；不是供当前脏工作区重复执行的安装脚本。

以上不是待制作的本机功能，而是未混入公共 `Source/` 的依赖边界。本机代码、已保存资产及已有构建产物未被本次精确暂存覆盖。生成预加载目录、工具伤害公式、其他 HUD／武器动作改动也继续保留在原工作区，不随本提交发布。未从本次暂存子集重新编译，既有 DLL 构建记录不能当成此公共快照的独立构建证明。

## 本机资产恢复链与许可

| 成果 | 制作／导入入口 | 需要的本机输入 |
| --- | --- | --- |
| 高地连续接口 | `SourceAssets/HighlandClaymoreMeshy20260922/JunctionBlendV5_20260927/author_junction_v5.py` → `import_junction_v5.py` | `Integration/`、`BroadbladeThicknessV2_20260922/`、`ClovenGuard20260922/` 的可编辑源及贴图 |
| 棱脊刃 V2 | `RidgePiercerRootV2_20260927/author_ridge_piercer_root_v2.py` → 同目录 import 脚本 | 上一步 V5 Blend |
| 棘冠配重球 | `ThornCrownPommel20260927/author_thorn_crown.py` → `import_thorn_crown.py` → `integrate_menu_icon.py` | 棱脊刃 V2 Blend、原装配重材质与安装端 |
| 两款握柄 | `SourceAssets/SharedSwordGrips20260927/read_mounts.py`、`make_surfaces.py`、`author_grips.py` → `import_grips.py` | 三剑当前模块源；`grip_materials.py` 为最终 Substrate 配方，旧白膜用 `repair_materials.py` 修复 |
| 灰阶改造图标 | `SourceAssets/MeleeAttachmentIconsGray20260927/render_icons.py` → `import_icons.py` | 当前模块、纹理以及本机 `baseline.json`／`runtime_sources.json`；旧目录保留读取这些几何来源的脚本 |
| 幽蓝灵体剑 | `SourceAssets/RuneSpectralBlade20260927/build_spectral_blade.py` → `import_spectral_blade.py` | Blender 5.1、UE5.8 Python；完全程序几何与解析材质，无第三方贴图输入 |

作者工具的绝对路径表示原制作宿主，其他机器先调整项目／工具位置，不原样运行会覆盖资产的导入脚本。历史 README 的模型尺寸与构建记录是当时记录；当前入口以上表为准。V5 更新的是仍含 `SurfaceRepairV4_20260927` 名称的现役 UE 包，不能归档该 Content 目录。

公共仓库不含本轮 Blend、FBX、GLB、uasset、PBR 贴图、密集几何快照或运行存档。宿主模型及材质沿用既有许可，不以可商用授权代替原资产再分发许可。飞剑快捷图标为本次内置 image_gen 原创生成，随提示词与运行 PNG 提交；其他灰阶成图默认本机保留。完整内容恢复见 [AssetSetup](../AssetSetup.md)。

## 整理和检查记录

283 个确认已被替代或未选中的文件（11,077,709,692 字节）移入 `trash/sword-publication-20260927`。包括高地 V3/V4、棱脊初版、未选波刃的制作中间物，旧彩色图标的 Icons／Scenes，以及飞剑自动备份和已完成的一次性修复脚本。逐文件原路径、目标、SHA-256、大小、替代物与理由见 [归档清单](sword-publication-trash-20260927.json)。移动前后哈希一致；旧 README 保留当前入口与恢复位置。没有删除文件，也未清理其他会话的废案。

推送前仅按本次授权执行发布检查：完整暂存差异、路径范围、空白错误、JSON 解析、作者脚本语法、敏感信息、大文件及许可边界。历史制作记录中的构建与保存结果保留原含义；游戏效果由用户测试。

本次发布检查结果：102 个明确路径，38 个 Python 文件语法解析、7 个 JSON 解析通过；暂存差异无空白错误，扫描未发现凭据或私钥，无超过 5 MiB 的新增文件。两份原创图标 PNG 的 SHA-256 一致（`09ac416e4ec79fb85bd5d3a96dcb3c38a574344dbc28bb004b72bf049d8a41ad`）。本机 `Saved/PublicationSword20260927/` 留存暂存快照与检查记录。
