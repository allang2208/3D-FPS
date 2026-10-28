# 恢复完整 UE5 内容

## 高地长弓、观峰镜与传说弓弦（2026-10-28）

本批公开高地长弓及普通/特殊/传说改造的配置、原创制作配方、归属裁剪的源码接入补丁和 SKILL。包含观峰镜主摄像机变倍/开放外围、战斗 HUD、弓快速近战与联机反馈、详细浮窗精简。模型、PBR、图标、音频、UE 包和构建产物保留本机；退役候选和快照带散列归档到 `trash/HighlandBow20261028`。当前依赖、前置补丁、历史构建/隔离检查及真实双端未验收范围见 [高地长弓发布](Publication/HighlandBow20261028/README.md)。

## 弓系技能与持续拉弓联机修复（2026-10-27）

公开四项弓技能的定向源码增量、精确配置、图标/箭雨/照明制作配方、平衡音频作者链与 SKILL；共享库存/身体/武器前置及 UE 资产仍需本机恢复。废案带散列移入 trash，保留当前输入和检查证据。上一轮 355 项为隔离检查，未作真实双端验收；本次不重跑玩法测试。归档、音频最终保存状态与发布边界见 [弓系整理发布](Publication/BowSkills20261027/README.md)。

## 焚化炉焚烧表现与联机审计（2026-10-27）

公开炉体表现源码、原创燃烧声制作／导入工具、SKILL 和审计记录；库存事务及共享档案接入以具备基线散列的定向补丁保留。正式声音 UE 包、WAV、完整本机库存前置和构建回执保持本机。旧快照及导入宿主缓存按清单移入 trash；恢复方法、补丁前置和未运行联机测试的边界见 [焚化炉整理发布](Publication/Incinerator20261027/README.md)。

## 随机地牢性能阶段收尾（2026-10-27）

两份不具备等价战斗负载的独立包及四个空输出目录已退役；正式工程、修复后的动画和采样证据保留。公开可分离的布娃娃／尸体与姿势锚点修复、动画和材质作者配方，以及带前置散列的性能接入补丁。共享生成器、技能和玩家宿主没有整文件发布，持续低帧尚未解决。归档清单、恢复边界和未完成项见 [阶段收尾](Publication/DungeonPerformance20261027/README.md)。本次仅整理与推送检查，没有构建或游戏测试。

## 五款背包与动态适配（2026-10-23）

公开五款背包目录、穿戴配置、动态／容量迁移源码及作者配方；模型、PBR、图标、UE 包和原始检查证据保留本机。客机净化入口依赖未完整公开的联机前置，保留精确迁移补丁，不夹带其他开发。152 份废案／快照已移入 trash 并读回校验。恢复链、历史检查范围和源码发布边界见[背包整理发布](Publication/Backpacks20261023/README.md)。

## 手枪与魔法书、战锤恢复与配置工作流（2026-10-21）

公开 V5 ADS/原待机门控、非手枪副手换弹及服务器等待、物品实例匹配修复、39 个战锤动作入口、5 个 Cook 目录与配置工具。交织的第三人称宿主以带基线散列的接入材料保存，尚未全部应用到公开运行树，不把配置清单通过当完整运行集成。16 个废案/旧快照已带散列移入 trash；当前 V4/V5、战锤混合版本及其旧版有效输入保留。原素材、密集采样、UE 包和构建产物留本机；历史隔离检查与真实主客机、Cook 和视觉验收分别记录。见 [发布范围与恢复](Publication/AnimationHandoff20261021/README.md)。

## SVCH、KV 瞄准镜与狙击消音器（2026-10-20）

公开 SVCH 新枪体接口、机械准星、弹道标定、弹匣/握把、V9 快速近战 R7、KV 1/2/4× 镜及狙击消音器的源码和配方。第三人称与诊断夹具的共享宿主以带前置散列的增量保存；许可模型、贴图、密集姿态和 UE 包留本机。330 份废案完成带散列归档后，用户已清空 trash 并确认无需恢复；原始清单与回执保留，有效旧版生产输入未移动。历史检查不等于完整联网伤害链、连续第三人称或五种改造枪托已验收；本次只整理发布。见 [发布范围、恢复链与未完成事项](Publication/SVCH20261020/README.md)。

## S12K 枪体、配件与联机修订（2026-10-19）

本轮 S12K 的当前制作链、通用件、前向 20 发传说大弹鼓、S12K撞火枪托、左手修订和第三人称/联机清单修复见 [发布与恢复](Publication/Saiga12K20261019/README.md)。独立源码/配方与 S12K 配置精确发布；交织公共宿主以逐文件基线补丁保留。完整几何、蒙皮/姿态、贴图、声音、UE 包和私有前置留在本机。废案进入 `trash/saiga12k-retired-20261019`，逐文件散列清单与移动回执可追溯；不凭旧日期删除活动输入。历史检查与本次 Git 整理分开记录。


## 生活区、设施刷怪与怪物命中修复（2026-10-19）

公开三名生活区员工的配方、肩部连续性修复、逐模型命中体积与联机命中源码；共享地牢/玩家宿主及依赖它们的诊断工具按具名前置增量保存。126 份确认退役文件已带 SHA-256 移入 trash，当前母版、碰撞回退源、密集采样和 UE 包留本机。历史隔离权威结果不等于真实双端联机验收，本次只作归档与推送检查。恢复顺序和边界见 [发布说明](Publication/FacilityMonsterHits20261019/README.md)。

## M870 第三人称瞄准与联机表现（2026-10-18）

公开抵肩坐标、泵动支撑手、激光 ADS 门控、持续泵动同步、装备实例匹配和服务端静止瞄准修复。共享角色文件只重放本轮修改；检查用例依赖尚未公开的共享夹具，随带前置散列的补丁保存。108 份失败／中断输出和重复日志、20 份发布临时文件已带 SHA-256 移入 trash。原素材、UE 包、密集采样与完整回执留本机；历史 Editor/Game 构建、29 项隔离检查及 12 项受控本地 UDP 场景，与仍未验收的画面和互联网范围分别记录于 [发布说明](Publication/M870ThirdPerson20261018/README.md)。本次只整理发布，没有重跑游戏检查。

## 生活区收集品、火甲、冰甲与持锤施法（2026-10-18）

公开四件非装备收集品的制作配方、生活区 67 个入口与排水 2 个工具箱绑定、升级奖励修复、武器火焰/足环、第一人称冰头盔 V5、第三人称冰甲 V6 和双手锤左手施法源码。共享宿主增量带前置散列发布，保留其他未提交改动；原始模型、授权素材、UE 包与完整回执留本机。废案带散列移入 trash，V2 共用冰甲导入器和 TorchV2/FireRingV4 活动路径保留。历史构建、有限火甲主客机结果与冰甲离线检查分开记录，本次仅整理和发布，未重新运行游戏或测试。见 [发布与恢复说明](Publication/LivingArmor20261018/README.md)。

## 守寝者（2026-10-17，未通过，暂停迭代）

用户否定 V18 行走，问题已记入 [待办](Backlog.md)。公开当前原创源码、保留的制作配方、历史记录与失败经验；只作可恢复开发断点。原始模型、第三方动作/密集关键帧、贴图与 UE 包留本机。废案按依赖关系移入 trash，当前接入及恢复输入保留。范围、归档和未完成事项见 [收尾发布记录](Publication/NightWarden20261017/README.md)。

## 物理配方手册（2026-10-16）

公开无背景阅读器、双面骨骼纸页、目录/拖动/书签与联机清理源码，补齐炼药工作台上一批列出的手册前置。采用 V5/V6/V8/V9/V10 混合恢复链，404 份退役输入和测试临时数据已带散列移入 trash。模型、字体、UE 包和完整回执留本机；既有 89 项单机及 10 阶段真实主客机检查通过，本次整理未重新测试。恢复链、许可、共用宿主边界和剩余跨机验收见 [手册发布记录](Publication/AlchemyManual20261016/README.md)。

## 药水工作台与炼药进入页（2026-10-16）

公开坩埚小游戏、台面交互/仪表/装瓶、八个配方及进入页修复的源码、原创制作配方与 SKILL；五处档案接入和手册审计的参数编译修正以具名前置补丁保留。151 份旧快照/一次性脚本已带散列移入 trash，当前模型、供体、共享导入宿主、包及历史回执留本机。并行物理手册与库存宿主前置单独列明，公开切片不等于干净检出完整构建。完整本机 V12 Game/Editor 已编译通过，本次整理未开 UE 或运行测试；范围、恢复链及依赖见 [本轮发布记录](Publication/AlchemyWorkbench20261016/README.md)。

## 枪械配件表面与 SUPER90 组合（2026-10-16）

公开本轮后托/握把表面、M16/ASH 瞄具、改造导航及 SUPER90 枪口/加长弹仓的原创配方和独立源码。18 个共享接入目标以带宿主前置散列的补丁保留，不夹带 M870、步枪音效等并行开发，也不代表干净检出已能完整运行。237 份废案及 8,003 份临时测试宿主文件已带散列归档；活动模型与恢复依赖留本机。用户已停止 UE 测试，完整联机验收交用户；范围、恢复链与技能更新见 [本轮发布记录](Publication/WeaponAttachments20261016/README.md)。


## M66 焚骸与焚化区（2026-10-15）

公开 M66 专属源码、制作/导入配方、六件蓝紫收集物与 40 个容器绑定。交织于共享地牢框架的 11 个区域接入目标保存为带前置散列的增量补丁；源码切片不等于干净检出可构建完整游戏。13,243 个废弃参考、备份、缓存与临时宿主文件已移入 trash，当前混合版本作者输入、实际 Content 和失败证据留本机。怪物、调试和物品 SKILL 已补充。V19/V22 旧网络检查通过不代表 V23 楼梯修正验收；最后复查中断且用户叫停，本次不重开 UE 或测试。恢复链、音效许可、归档与未完成项见 [发布记录](Publication/M66Incineration20261015/README.md)。

## 法杖面板、技能准备与联机修复（2026-10-15）

公开当前龙息 R6 原创作者／颜色 HLSL、喘息制作脚本、对应 SKILL 和验证摘要；依赖未公开战锤及档案框架的 88 个运行代码路径以逐文件具名前置补丁保存，不能当作干净检出的一键构建。13 个废案已带 SHA-256 移入 trash，当前母版和供体保留。本机整合版正式构建、45 项权威逻辑、110 项上挑及限定真实主客机用例已完成；本次整理不重复玩法测试。恢复顺序、源码切片和未覆盖边界见 [本轮发布说明](Publication/SkillMagic20261015/README.md)。

## 战锤改造与共用符文（2026-10-15）

公开六件原装拆分、五槽目录、通用改造、双棱尖头／陨星熔核／无配重、力量与共鸣符文的原创配方和可分离源码。依赖尚未公开的战锤战斗及档案协议的接入部分按具名基线保存补丁；本机完整代码已经应用，公共切片不等于完整可构建工程。86 个废案／Before 快照带 SHA-256 移入 trash，当前模型和供体留本机。既有 47 项目录与 103 项原生隔离检查通过，未做真实双端网络验收。资产恢复、归档及联机待测范围见 [战锤改造发布说明](Publication/WarhammerMods20261015/README.md)。

## 货运、发电与医疗／生态收集物（2026-10-15）

公开两种工人衣物、三件工具、三件电气收集物、六种调配材料的原创制作配方，以及目录、掉落、回收、占格与共享容器迁移修复。区域遭遇和客机缓存前置仍与共用框架交织，独立实现及修复以具名基线接入补丁保留；本机完整工程已接入并完成 Editor/Game 构建，公开切片不等于干净检出完整构建。164 份退役快照/旧模型/预览与一次性脚本已带 SHA-256 移入 trash。模型、纹理、图标、UE 包、导入宿主和构建证据留本机；恢复链、技能更新、发布边界和待用户联机测试范围见 [本轮整理发布](Publication/RegionalLoot20261015/README.md)。

## 根冠、园艺师与医疗／生态区域（2026-10-14）

公开根冠 M-01 原生角色、园艺师实体服装制作配方和本次共享修改；区域目标、生成分派与远端命中等交织于未公开框架的部分以带散列补丁保存。当前本机资产和整合代码已接入；公开切片不等于干净检出完整构建。393 份旧快照/作者备份已移入 trash 并核对散列，保留园艺师 V01 作者输入及根冠混合版本依赖。模型、贴图、音频、UE 包和密集蒙皮数据留本机；恢复顺序、技能经验、历史检查与未实际联机测试边界见 [本次发布记录](Publication/RootCrownEcology20261014/README.md)。

## 持续魔法与龙息体积火焰（2026-10-14）

公开本会话的龙息 V8 R2 原创作者、持续魔法联机收尾、书本采样／远端金光及相关技能接入。77 份旧 Sprite 方案与探针、旧系统／专用材质已带散列移入本机 trash；保留 R1/R2 当前重建链。UE 包、Epic/Fab 依赖和构建产物留本机；完整工作区 Editor/Game 构建成功，未运行主客机测试。公开快照与未合入共享框架边界见 [魔法收尾发布](Publication/Magic20261014/README.md)。

## 联机排查批次源码与覆盖台账（2026-10-14）

监听服务器的档案传输、物品／世界权威、状态恢复、工作站和动作表现按明确范围发布；独立源码直接提交，共用文件的联机修改以具名 Git 基线补丁保留。完整本机 Editor/Game 已有成功构建记录，公开源码仍需整合共享依赖及授权资产，不能视为干净检出编译或联机验收。83 份一次性脚本已带散列移入 trash，构建与覆盖证据保留。接入方式、补丁限制和技能入口见 [联机批次发布记录](Publication/Multiplayer20261014/README.md)。


## 地牢性能优化阶段收尾（2026-10-13，暂停）

独立的预览场景生命周期修订、闲置资源回收、AI 采样与导航投影缓存按原路径发布；与未发布的玩法/联机前置改动交织的地牢准备、有限 GPU 预热及 F6 扩展，以包含基线散列的接入补丁保留，不能视为公开仓库已获得完整接入。本机 DLL 已构建，但最新崩溃修订尚未运行复测。模型、贴图、UE 包、原始追踪、CrashContext 和构建产物留本机。31 份过期快照/一次性脚本/失效链接产物已带散列移入 trash。后续入口与恢复限制见 [性能收尾记录](Publication/DungeonPerformance20261013/README.md) 和 [待办](Backlog.md)。

## 武器动作、联机表现与镭射（2026-10-13）

71 个本轮源码／配置目标按修改块直接发布到对应路径，其他并行开发内容保留在工作区。翻越制作配方与供体来源公开，UE 动画、模型、声音及构建产物留本机；仍需按本文恢复授权资产。过期快照与一次性请求已带散列移入 trash；最终架枪仍要求退出再进入 ADS。范围、恢复链、构建和未实测边界见 [本轮整理发布](Publication/WeaponRound20261013/README.md)。


## 搜索收集物、两厅投放与联机接入（2026-10-13）

公开17件收集物的原创制作配方、物品目录、形态图标规则、31个容器的1～3件概率配置及相关库存改动。完整本机已有共享搜索实现并完成构建；其依赖的共享库存框架尚未提交，因此本次联机源码以带基线哈希的接入补丁发布，不能视为公开仓库已获得完整联机框架。模型/PBR、参考图、UE包、日志和构建产物留本机。224份废案/旧快照已移入trash并核对散列；恢复链、补丁前置条件、构建及未实机联测边界见 [搜索收集物整理发布](Publication/SearchCollectibles20261013/README.md)。

## SUPER90 通用后托（2026-10-13）

五款通用后托已制作专用连接杆与闭合接口，接入枪匠、原厂恢复及第三人称展示。公开源码与制作/检查配方，26 个 UE 资产、模型和纹理留本机；恢复链、收尾检查与正式构建边界见 [后托收尾发布](Weapons/super90-common-stocks-closeout-20261013.md)。

## SUPER90 弹药、局部修订与联机收尾（2026-10-13）

公开本枪弹药与装填权威、远端表现、四段圆环、弹药轮盘和配件接入源码及原创制作配方。当前动画恢复普通 Cransh 按压释放、快速装填按压收尾和臂根局部修订；手臂采用 JointSurface，保留原生绑定。339 份确认废案已带散列移入 trash，活跃表面输入与恢复基线保留。模型／动画／贴图／声音、密集采样和 UE 包均留本机；完整恢复链、旧方案边界与未实机联机验收状态见 [发布更新](Weapons/super90-publication-20261012.md)。


## M 系列、鼓囊与大厅遭遇（2026-10-12，收尾 2026-10-13）

公开鼓囊原骨架动作/抛射/事件音效/场景预警、半速游荡与延迟发现、两厅共同封门和 12 类接地的源码、原创制作脚本及 SKILL。保留 V01/V02/V03/V04/V08/V10/V11 混合恢复链，吸气蓄力和落地引信声音继续关闭；正式模型、原音频、51 个 uasset、密集绑定和构建产物留本机。56 份旧快照及一次性恢复脚本已带散列移入 trash。恢复顺序、发布范围、构建和未游戏验收边界见 [阶段收尾](Publication/MSeries20261012/README.md)。


## 魔法书（2026-10-10，暂停）

公开魔法书 C++、原创制作配方、CC BY 4.0 署名、暂停待办和动作 SKILL。保留 V17 阅读基线恢复现场及 V3 持握；recover 未获认可。原模型、PBR、图标、V7 手模、Blend/FBX、密集作者数据、UE 包和构建产物留本机；589 份废案与旧备份已带散列归档。恢复链与最新编译边界见 [暂停与发布记录](Weapons/spellbook-paused-20261010.md)。

## 法杖与近战配件（2026-10-10）

公开法杖动作／联机快照／预览修复、近战配件数值与介绍标准，以及白水晶 V41、元素表面 V42、杖冠／符纹／握柄尾饰和符文主体图标的原创制作配方。模型、贴图、作者资产和导入回执保持本机。162 份废案与旧备份已带散列归档；因现有编辑器桥不可达，47 个旧 UE 包保留原位。当前恢复链、验证范围及未清理包清单见 [本次发布记录](Publication/StaffAndRunes20261010/README.md)。

## 装备稀有度与强化掉落光束（2026-10-10）

公开装备稀有度清理、实例迁移、界面适配、强化掉落分档与鲜红传说色的源码、目录和 SKILL，无新增二进制资产。原有 LootFX 材质继续使用 `Tools/AssetPipeline/build_loot_glow.py` 恢复，物品网格／贴图保留各自授权边界。本轮无独立废案；源码回查、常规构建与未游戏测试的范围见 [整理发布](Publication/equipment-rarity-loot-glow-20261010.md)。

## 无面职员 M-03／M-04／M-05（2026-10-09）

当前安保为 V13 身体衣物、V14 帽子、V06／V10／V12 动作；接待员和研究员为 V05 衣物与状态，保留各自 V04 核心动作。公开原创源码、制作配方、说明和 SKILL；完整身体、动作包、模型、纹理、UE 包及密集修形数据留本机。102 个退役导出、预览和备份带 SHA-256 移入 trash。混合版本输入、归档恢复与未游戏测试边界见 [无面职员整理发布](Publication/FacelessStaff20261009/README.md)。

## 设施大厅、六主题路线与静态设施（2026-10-09）

公开生态/发电区、大厅/分流、双主题生成、光照和异步准备的原创源码与配方；正式地图、Content、Blend/FBX、纹理、几何采样及合法复用输入留本机。1307 份退役中间文件和自动备份已带散列移入 trash；当前母版仍保留。当前门/井盖/通风口是关闭的静态布景，新出怪扩展已撤回。41 个旧动画/切孔 UE 包因编辑器仍打开而保留，未从磁盘搬动。恢复顺序、发布边界与技能更新见 [设施地牢整理发布](Publication/FacilityDungeon20261009/README.md)。本轮仅做仓库整理与发布检查，未重新运行游戏或视觉测试。

## 枪械轴向往复与抛壳口（2026-10-09）

公开本轮运行代码、稀疏校准表、制作配方与 SKILL；16 款单枪及 10 套双持的 UE 网格、原始 FBX、NPZ 几何、密集姿态采样、检查图与构建产物留本机。17 个过期请求、失败探测和前版本备份已带散列移入 `trash/weapon-gunplay-retired-20261009/`。恢复输入与发布边界见 [本轮整理发布](Weapons/gunplay-calibration-publication-20261009.md)。两项目标已在完整本机工程中构建成功，未运行游戏；公共切片未在隔离克隆中重新构建。

## M 系列减面、战斗与移动修订（2026-10-08）

四只当前为 M14 TeethRemeshV4 与 M08/M09/M10 AnatomyRepairV5，保留认可结构、原生产骨架/动画和重新绑定的软体尸体。另有螺柱 V21 撕咬/V22 下砸/旋转范围、M09/M08 死亡及 M07/M10/M14/M25 移动同步。39 个废案文件已带散列移入 trash；V3 制作中间源仍是 V4/V5 的恢复依赖。公开源码、工具、时序与 SKILL，模型/PBR/音频/UE 包/密集绑定留本机。恢复顺序与本轮未游戏测试边界见 [M 系列整理发布](Monsters/m-series-publication-20261008.md)。

## 缚群 M-88（2026-10-10）

开发已恢复，当前为 V29 活体／V25 衣物、V28 攻击、V33 撕咬及 V34 无支撑死亡；拍击已获用户认可，V34 已保存但待用户体验。V32 尸体网格仍为 V34 输入，旧版身体／骨架／材质模板不得整包删除。本次另归档 308 项，历史 618 项归档保留。公开源码、作者脚本、少量配方、BSD 参考许可与 SKILL；Meshy 原模型、模型派生物、纹理、密集采样、UE 包和日志留本机。恢复顺序、散列清单和许可边界见 [缚群发布记录](Monsters/bound-congregate-publication-20261010.md)，仅 Git 源码不足以恢复完整怪物。

## 苍龙 V10（2026-10-07）

**运行版本**：Fab 龙爪 `/Game/Weapons/AzureDragon20261004/ClawFab`（9 个资产）+ 能量条 `HudV10`（6 个）。另外依赖共享法线 `Textures/T_AzureDragonNormal`、`ClawV10/Textures` 的脉络贴图，以及本机已授权的 Realistic Starter VFX Pack Vol2 火焰序列 `T_Fire_F`／`T_Fire_D`（只读引用）。用户已确认特效与判定，后续几版尚待体验。

**恢复**：根目录 `SourceAssets/AzureDragon20261004/run_install.ps1` 依次执行共享法线 → `ClawV10/install_textures_ue.py` → `HudV10/install_hud_ue.py` → `ClawV10/install_fab_ue.py`。

**本机输入**：Fab 原模型、百炼生成源图、Blend／FBX 和回执只留本机。

**本轮归档**：113 份废案（19 个 UE 包：V9 爪与能量、V10.1 原创爪、旧爪痕／余烬材质、V9 共享爪材质）已带散列移入本机 `trash/azure-dragon-retired-20261007`。

公开范围与归档清单见 [苍龙 V10 整理发布](Combat/enchant-azure-dragon-v10-publication-20261007.md)。本轮没有运行游戏或画面验收。

## 螳螂 M27（2026-10-07）

当前为 BindingV2、RunV4、ClawV16、PounceV11、CloakV1、CombatV15 和 AudioV1。保留 Meshy 原始输入、ProductionV1、ClawV3、PounceV5/V6 及已认可的 ClawV14 恢复版本。声音 15 个 SoundWave 和蓝图已后台保存，Editor/Game 已构建；未试听或运行游戏。源码、作者配方、SKILL 和归档元数据公开，模型/PBR、授权派生动作、密集采样、音频与 UE 包留本机。恢复顺序和废案位置见 [螳螂发布与恢复](Monsters/MantisM27Publication20261007.md)。

## 裤鞋与第一人称共用身体（2026-10-06）

恢复裤鞋九件、休闲鞋单只斜视图标、锁甲裤护膝护腰 V2、皮革裤靴、连续裆缝七分裤与本机连续肩口。保留原生第一人称手部，身体共用世界姿态；换装加载交接修复已有本机 DLL 构建记录。131 份旧腿模、旧肩口、旧镜头和快照带散列移入 trash。公开源码、配方与 SKILL；授权模型、密集绑定、图标及 UE 包留本机。恢复顺序、发布边界与历史检查范围见 [整理发布](Characters/lower-equipment-publication-20261006.md)。本轮没有运行游戏或画面验收。

## 伏窥者 M-08：表面追击与背环空气炮（2026-10-05）

恢复用户 Meshy 输入、背部 V02、CanineV03 皮肤／骨架、BoneheadV04 基础动作、V05 越障、V09 飞扑、V10 死亡和 V11 空气炮预警。V12 索敌与追击已完成本机常规构建；游戏表现未测试。45 份废案／旧快照已带散列移入 trash，仍被制作链读取的旧版源保留。公开 C++、原创配方、MIT 参考、预警 HLSL 和 SKILL；媒体、密集采样、UE 包及回执留本机。恢复顺序和发布范围见 [M08 整理发布](Monsters/LurkerM08Publication20261005.md)。

## 苍龙：能量条与龙爪未达标、待返工（2026-10-05）

用户体验 Coherent V9 后反馈“不是很合格”，已登记 [返工待办](Backlog.md)。当前仍被运行引用的 V9 十一份资产、原创作者入口、共享爪材质、原 Fab／Epic 输入及认可设计图暂留本机；保留不表示视觉或动作认可。九次充能／30 秒、左右双爪交替与既有伤害合同不改。

117 份废案含 17 份旧 UE 包已移入 `trash/azure-dragon-retired-20261005`，逐文件移动前后 SHA-256 相同。RigV2、EnergyV3、EnergyV6、ReferenceV7、CombatV4、DualClawV8 和旧静态输出均按 [本轮整理发布](Combat/enchant-azure-dragon-publication-20261005.md) 查询；认可设计图移到 `SourceAssets/AzureDragon20261004/References`。根目录兼容入口转发当前 V9，共享基线不恢复旧静态爪与能量材质。公开源码、配方、HLSL、待办、SKILL 和归档元数据；授权模型／参考／UE 包及回执留本机。上一轮完整工作区的保存与构建不是本次公开快照的新验证，本轮没有游戏、PIE、渲染或验收。

## M-14 与通用连续软体死亡（2026-10-05）

本机使用 M-14 V15 活体、V19 连续软体尸体、V16 绿色毒液与 V20 旋风范围；嘴部已接入统一弱点。另有 11 个非人形角色条目、10 份独立尸体绑定已后台保存，人形暂不推广。现有 Game/Editor 构建和保存回执保留本机，游戏表现未测试。

公开 C++、原创制作脚本、毒液 HLSL、MIT 来源和 SKILL；Meshy/其他怪物资产、密集绑定、UE 包与回执不公开。58 份旧快照和废弃脚本已移入 trash 并核对散列。M08 独立实现未夹带，M25 独立提交已到达远端，本轮直接整合其软体挂接。当前依赖、恢复顺序、资产边界和归档详见 [整理发布](Monsters/SpiralPillarM14Publication20261005.md)。

## M-25 涡电匣与战斗修复（2026-10-05）

恢复用户 Meshy 输入、RigV01 专用蒙皮／动画、BiteV01 与受击死亡、BackElectricV02，以及 OptimizationV01 四级游戏网格。怪物已获用户认可；最新撕咬遮挡与客机奖励修复已完成本机 Editor/Game 构建，未游戏测试。60 份旧快照和废案带散列移入 trash；公开源码、原创配方与 SKILL，原媒体／密集数据／UE 包留本机。连续软体死亡挂接以独立补丁记录，地牢刷新按用户要求暂不接入。恢复顺序与公开边界见 [M25 整理发布](Monsters/m25-publication-20261005.md)。

## M-09 悬钟 V24 与源码整理（2026-10-04）

保留 Meshy 原始输入、V03 专用骨架、V13/V15/V16 连续表面链、V18 抓击、V09/V07 鸣震、V08/V10/V12 凝视、V13 死亡、V22 材质、V23 受击与 V24 屋顶移动。136 份废案及旧快照已带散列移入 trash。公开源码、原创配方、HLSL 和 SKILL；模型/PBR、授权动作供体、密集数据、UE 包和运行回执留在本机。恢复依赖、路径覆盖关系、归档及检查边界见 [M09 整理发布](Monsters/HangingBellM09Publication20261004.md)。V24 仅完成构建，未游戏测试。

## 唐刀改造、G18 弹鼓与韧性整理（2026-10-04）

保留虎头 SideProfileV6 眼位修订、G18 弹鼓 V2 与 Reload Profile、唐刀山岳符文及既有原生手模/材质输入。22份明确旧稿已移入本机trash并记录散列；公开效果源码、五档韧性数据、制作脚本和SKILL，原模型/参考/UE包及构建产物留本机。共享M14新类及其专用路由未混入本次发布，完整本机接入仍保留。来源、恢复、发布依赖及尚未结案的联机审计见 [本轮整理发布](Publication/AttachmentEffects20261004/README.md)。未运行游戏验收。

## M-10 沉匣制作与接地整理（2026-10-03）

保留 SurfaceRigV5 的 62 骨模型与十段动作、RearGasV7 八秒动作、HowlV4 音波及手脑声音、LocalGasV8／CombatPaceV10 毒雾、原 F6 蓝图和大体型导航。公开 M10 源码、原创制作配方、SKILL 与散列归档说明；Meshy 原始媒体、几何／权重采样、UE／Blend／FBX 与构建产物留本机。20 份废案已移入 `trash/m10-retired-20261003`。玩家 SAN 生存模块尚未公开，嚎叫受击接入以补丁保存，公共源码不具备该完整效果。恢复顺序、依赖和未测边界见 [M10 整理发布](Monsters/m10-publication-20261003.md)。

## 2011 握把与 SI 制作源整理（2026-10-03）

当前 VIP 与三款通用防滑纹均为纵向握把侧面覆片，下沿沿真实斜缝裁切，不覆盖弹匣、底板和扩口；SI 为原生枪口的完整轮廓延展。200 份废案与旧快照已归档，当前模型、原生手模/光学供体、音频响度输入、私有材质和 UE 包留在本机。公开源码、恢复顺序、来源与未测试边界见 [2011 整理发布](Weapons/pit-viper2011-publication-20261003.md)。本次只做用户要求的归档和仓库发布检查，不启动 UE 或游戏测试。

## 怪物布娃娃、巫婆与飞扑修订（2026-10-03）

恢复连体巫婆 CorpseFollow、专用完整法杖碰撞、巨手死亡 Physics Asset，以及突变体 V3 空中／V4 落地／V5 蓄力动画。公开运行源码、原创制作脚本、ALS 固定修订与 MIT 许可、制作及归档说明；Meshy／Epic／第三方模型、采样姿势、UE／Blender／FBX 包和构建产物留本机。115 个退役文件（约 98.57 MiB）已带散列移入 `trash/monster-ragdoll-retired-20261003`。完整输入、重建顺序和本轮未测试范围见 [怪物布娃娃整理发布](Monsters/monster-ragdoll-publication-20261003.md)。纯源码克隆不包含这些运行内容。

## M-07 盲祷者 V38 与源码整理（2026-10-04）

当前 F6 角色使用原 V18 路径的 V35 蒙皮／V38 肩部固定与巫婆式背膜布料、V20 待机、V25 移动、V32 近战、V30 悬浮施法、V29 方向死亡和 V33 过渡支撑。慢走／追击 63／129 cm/s，动画源速 42／86；最终魔攻 60。V38 资产已保存，尚未游戏验收。93 份独立废案、旧快照与重复备份已移入 trash；V22/V23、V27/V28/V30、V35/V36 及旧原模型链仍是必要本机输入。原 Meshy、Epic／Quinn／Rampage、ZombieAnimationPack／Vefects 动作、密集采样、UE 包和构建产物保留本机；纯 Git checkout 不含完整资源。恢复顺序、来源和散列见 [M-07 V38 整理发布](Monsters/BlindSupplicantM07Publication20261004.md)。本次只执行归档与推送检查，未启动 UE 或游戏测试。

## 本轮手臂动作与撞门（2026-10-02）

恢复 V7 原生手臂、法杖快速近战／积蓄／释放、空手走跑、HK416 换弹接触、201 托握和 M16 腕部／奔跑的本机制作依赖。撞门声音使用用户指定 `撞门.mp3`，保持 `/Game/Audio/Interactions/DoorPush20261002/S_DoorPushImpact` 的完整音频与 ForceInline 设置。公开原创代码、配方及说明，不公开原生绑定导出、供体完整采样、UE／Blender 包和未经再分发核准的音频。恢复顺序、废案归档与未测试边界见 [手臂与撞门整理发布](Weapons/fps-arms-publication-20261002.md)。

## 附魔迭代、牛仔补弹与 M1911 消音声（2026-10-01）

恢复汇聚蓝色 V2、碎裂紫晶 V1、感电 V3 武器电弧，以及裂空 V4 双尖蓝白剑气和刃部扰动。原生源码、附魔数据、原创 HLSL、制作脚本与技能记录公开；UE 资产、原音频、既有闪电与枪械依赖保留本机。感电的旧圆箍和裂空的月牙／暗色裂口已退出当前制作版本，观感尚待用户测试。牛仔在滑铲 0.25 秒后消耗真实备弹补弹并显示「已自动换弹」；M1911 修复切枪后复用错误消音音源，保留原共用音色。两份废案脚本已归档，恢复顺序、来源边界及构建记录见 [本轮整理发布](Publication/enchantment-closeout-20261001.md)。本次只做发布检查，未启动 UE 或运行游戏测试。

## G18、HK416 与步枪待机／换弹衔接（2026-10-01）

恢复本机 G18 与 HK416 原始素材、原生手模／共享配件、最终图标、HK416 六动作家族和 AnimationProfiles20261001 运行握把资料；弹鼓与普通／扩容空仓分别使用完整 M4 拍击，检视使用当前六家族 4.2 秒版本。24 份退役文件已放入 trash；来源许可、制作顺序、公开源码与本机二进制边界见 [本轮整理发布](Publication/g18-hk416-publication-20261001.md)。本次只执行仓库发布检查，没有运行游戏测试。

## 冰墙凝聚、预览与双形态（2026-09-30）

当前冰墙网格与冰材质使用 `/Game/Skills/IceWall/FabIceV3` 的四种破裂冰块、派生冰面和 `T_IceSurfaceColor` 颜色副本，需恢复用户导入的 `/Game/Ice` 原包第 6 套 normal／roughness／AO 依赖；重建颜色副本时还需原 basecolor。颜色副本必须使用 `TC_DEFAULT`、sRGB 和 Color 采样，不能恢复原包的法线压缩设置。预览材质与施法声继续使用 BlockV1，碎裂粒子和声音来自现有 IceSpike。新增寒雾为 `/Game/Skills/IceWall/ColdMistV1/NS_IceWallColdMist`，依赖冰锥 FrostV2 的 `MI_ColdMist`、母材质及原烟雾图集，由 `Tools/Skills/build_ice_wall_cold_mist.py` 重建；表现、预算和落盘状态见 [冰墙寒雾](Skills/ice-wall-cold-mist-20260930.md)。制作、落盘与棋盘格修复见 [冰墙 Fab V3](Skills/ice-wall-fab-v3-20260930.md)，数值、存档及操作见 [冰墙迁移](Skills/ice-wall-migration-20260930.md)。Fab 二进制与导出贴图参考保持本机，不作公开再分发。V2 保留为历史版本。未运行游戏测试。

## 衣物、锁子甲与手臂续修（2026-09-30）

野行长袖 22 个第一人称绑定已重建为 `FieldSweaterNativeFamily20260930`，用户反馈当前效果“没什么问题了”；Body 使用 SurfaceRepair。炭灰保留 BodyV4/TraversalV2/PickupsV3，锁子甲镜头保护与 SVD/法杖臂链继续沿用活动配置。247 份退役输出/候选已移入 trash；原生几何、材质/骨架输入、密集动作、UE 包和回执保留本机。当前来源、公开边界与恢复依赖见 [整理发布](Publication/outfit-closeout-20260930.md)。本次整理没有重新运行游戏测试；历史 SVD 首次空仓色块未复现记录不改写为通过。

## 毒液僵尸固定步态、随机近战与叠毒（2026-09-29）

恢复本机 Meshy 原蒙皮/绿色材质、V10/V11 四步态、V12/V13 三攻击与共用人形布娃娃。V15 已正式构建，每次实际受伤的存活目标叠一层共用中毒。987 份旧攻击、成品、快照和中间帧已归档；V7 采样助手与原生输入、BiteV8 共用参数仍保留。作者脚本、SKILL 和运行交接补丁公开，依赖未发布共享接口的运行改动尚未整体接入公共 Source。来源、恢复顺序与散列见 [本次发布记录](Monsters/spitter-publication-20260929.md)。

## 法杖整臂普攻、免费改造、副手与跟随发射（2026-09-29）

保留 V28 整臂动作、V29/V30/V32 默认水晶回退与照明、V33 元素水晶；法杖限主手，副手手枪、G 键照明及右手施法已写入本机运行层。火球与冰锥跟随至实际接触点才发射。44 份 V27/V34 废案归档，当前脚本、原创图标和三个 SKILL 发布；21 份运行源码及共享接入以补丁交接，未整体集成到公共 Source。恢复依赖、历史构建和本轮未测边界见 [法杖整理发布](Weapons/staff-publication-20260929.md)。

## 工作台、枪械组装与脚架／镭射（2026-09-28）

常规工作台直接制作、弹药／枪械双卡片、分件小游戏与完成后半料返还，按本机已完成源码保留。常规工作台与脚架／镭射的独立修改直接发布；依赖打铁运行层的枪械小游戏保存完整源码和接入补丁，尚未应用到公共 Source。初版／第二版桌面 11 份退役源移入 trash；保留原台灯、库内工具、弹药盒及仍被使用的作者链。本轮不修改独立的中世纪桌面与火炬。资产恢复、补丁边界和检查记录见 [工作台整理发布](Publication/workbench-publication-20260928.md)。未运行游戏测试。

## 主神空间布局、海面、地毯与金属收边（2026-09-28）

恢复本机 `GameMaps/DayNight_Lighting`、`Props/GodSpaceLayout20260927`、罗马建筑/栏杆/喷泉/祭坛与共享天空依赖。地毯 V2 已获用户认可，连续金属条已保存但未作游戏观感确认；下方云海按用户要求隐藏。Git 发布布局参数、制作脚本、定点路由源码和 SKILL，原模型、贴图、UE 包、构建及导入回执保留本机。本次 48 份废案已归档；恢复输入、旧方案边界与公开发布范围见 [主神空间整理与发布](GodSpace/publication-20260928.md)。本轮仅做仓库发布检查，未重新构建或运行游戏。

## PKM 缎面、弓配件与原左轮检视复用（2026-09-27）

恢复 PKM 私有干湿材质与细纹纹理、两款弓弦／箭台／单镜片瞄具，以及 M1911 原左轮动作适配的两段动画。转枪检视已撤回，双持不播放检视；无限备弹箭可靠近收走但不返还真实库存。203 份退役文件已归档。公开源码、配置、作者配方与技能，本机保留模型／贴图／UE 包和导入回执；最终手枪 DLL 与整理后的原生源码仍待构建，未运行游戏测试。当前依赖、恢复顺序和发布检查见 [本轮发布记录](Publication/weapon-bow-inspect-publication-20260927.md)。

## 随机地牢、神像房与刷新池升级（2026-09-27）

恢复随机地图及生成器 ExternalActor、共享房壳/铁闸/楼梯/设施组合件、神像与怪物资源。当前制作链、96 份废案归档、公开源码与运行接口交接范围见 [地牢升级整理与发布](Gameplay/dungeon-upgrades-publication-20260927.md)。公共 Git 包含制作配方和独立辅助源码；完整本机运行仍依赖尚未发布的共享接口与本机授权资源，不能把交接补丁当成已经集成的完整工程。本次没有重新运行游戏测试。

## 猎手长弓、五槽改造与三类箭矢（2026-09-27）

当前使用 ElasticV15 绑骨弓体、WoodBracketV19 木圆环瞄具、GripContactV22 缠带、NockContinuityV21 搭箭和 LocomotionV23 移动动作。三款新箭网格及材质已保存，最新箭种/浮窗源码仍暂缓原生构建；毒箭绿色识别和图标过曝尚待改善。Git 公开本对话可独立的源码、目录、作者配方与技能，不包含模型、媒体、密集拟合数据及其他任务的未发布交叉功能。保留依赖、两份新归档及完整边界见 [弓发布与恢复](Weapons/bow-publication-20260927.md)。


## 人形控制、绿色巨手与小手（2026-09-27）

本机模型/动作、根骨接地、冲锋表现、低位近战和受限布娃娃的当前来源、归档及恢复顺序见 [本次发布说明](Monsters/monster-hands-publication-20260927.md)。公开作者配方与 SKILL；模型/PBR、目标蒙皮、密集数据和 UE 包保持本机许可边界。共享战斗接口含其他任务尚未发布改动，13 份新增运行源码以非编译交接补丁保留，不能把本次 Git 克隆当作完整可运行版本。

## 动态草地：未成功，暂停（2026-09-27）

恢复合法本机 PN_GrassLibrary、丘陵草、WorldGeneration/GrassDeform、高草测试地图及 AutoFootstep 插件／委托。v13 效果被用户否定；v14 主材质已保存但实例尺寸参数未全部落盘，不能作为完成版本。源码、作者、复现工具和 SKILL 保留，49 份废案移入 trash；本轮未继续制作或运行游戏。恢复边界、归档散列和待办见 [草地暂停与发布记录](WorldGeneration/grass-paused-publication-20260927.md)。

## 裁片露指手套与单只图标（2026-09-27）

当前棕色手套为 `TailoredFingerlessV1`，22 套原生绑定共用现有动作，穿戴用皮肤／皮革组合网格。保留对应 UE 家族、Manny／V7 母版、`FingerlessHuntV2` 配对覆盖源、选定裁片样件及 Quixel 皮革扫描。公开本次源码、精确物品配置、作者脚本、技能和归档索引；模型、贴图、密集 JSON、采样动作、回执和编译产物留本机。126 份废案和旧备份已移至 trash；恢复顺序、保留理由及用户反馈见 [手套整理发布](Characters/tailored-gloves-publication-20260927.md)。

## 药水饮用、四品阶瓶型与恢复数值（2026-09-27）

恢复 `/Game/Items/Consumables/PotionTiersV1` 的 16 个三级 LOD 网格、材质与软木贴图，以及 V7 原生手模、备用左臂和已有上游装备依赖。八种物品共享四档瓶型，同档生命／魔法只换液体材质；全部等级可用，恢复量为基础值加最大资源百分比。源代码、简洁参数、作者脚本、技能与归档索引公开，Blend／FBX／GLB／UE 包、设计图、贴图、导入回执与手模输入保留本机。两份自动备份移入 trash；恢复顺序、旧瓶参考边界和最近一次编译被弓模块阻断的状态见 [药水发布说明](Publication/potion-publication-20260927.md)。未进行游戏测试。

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

## 近战检视、格挡与弓快速近战（2026-09-27）

当前本机 Inspect V82、格挡 V23、弓推击 V7 的最终源、合法资源恢复、依赖保留和废案清单，见 [本次整理与发布](Weapons/melee-bow-publication-20260927.md)。本次源码发布不包含授权模型、密集姿态或 UE 资产，也不包含依赖其他任务未发布接口的混合运行改动；具体边界在该记录中逐项列明。


## 高炉、铸造台与实景锻造（2026-09-27）

恢复 CastingStation20260926、ForgeInteraction20260927、FurnaceCasting20260926、V7 原生手臂与授权供体姿态，以及高炉／Normandy／Clearwater／Mantaflow 依赖。三剑配方公开，forge-grip.json 与音频／二进制保留本机。42 份废案已归档；旧 V3 与初版总装仍是当前作者输入。制作链、SKILL、精确运行交接补丁与公开树未完整接入边界见 [锻造整理与发布](Gameplay/forging-publication-20260927.md)。本轮未运行游戏测试。
# 高地改造与幽蓝飞剑增量（2026-09-27）

## 学徒长杖、持杖施法与库存比例（2026-09-28）

恢复 `ApprenticeStaff20260927` 的 V21 木杆、V22 世界水晶、V23 预览材质，以及 V7 M4 裸臂与 V13/V16 密集姿态表。独立目录／装配、图标修正、装备 profile 和作者配方公开；依赖未发布共享接口的第一人称／施法实现以交接补丁保留。156 份废案已移入 trash。来源、制作顺序、归档散列及公开源码边界见 [长杖发布恢复](Weapons/staff-publication-20260928.md)。V26 本机基础 DLL 构建成功，未做游戏视觉验收。


本次增量的当前作者入口、已许可本机输入、归档恢复清单及未混入主线的共享代码依赖，见 [高地与飞剑发布记录](Weapons/sword-publication-20260927.md)。公共仓库提供配方、目录与可独立发布的源码；Blend、FBX、uasset、宿主纹理与密集几何快照仍在本机。飞剑原创快捷图标另有明确 PNG 白名单。仓库拉取完成不等于恢复了本机完整可运行内容。

## 2026-09-27 配件、镜内表现与改造预览布光

本轮公开 SVD／M1911 扩容弹匣、715 握把／瞄具／枪口、通用手枪防滑覆片、LPVO／PSO 镜内与镭射处理、背包装备自动转向及公共预览布光的源码、目录、制作脚本与技能说明。资产恢复顺序、废案与来源边界见 [发布记录](Weapons/attachments-optics-preview-publication-20260927.md)。`trash`、Blend／FBX／uasset、PBR 和图标、密集几何快照及运行日志不公开；仅克隆本仓库不能获得这些生产资产。

## 手套与锁子甲生产依赖（2026-09-29）

当前四款手套、锁子甲 V2 环纹与 SharedSway 第一人称袖口的作者源、原生曲线和材质恢复见 [本次发布说明](Publication/gloves-chainmail-publication-20260929.md)。`SteelGauntletPoseCurves.inl` 是本地授权数据生成的必要构建输入，不随公开源码分发。旧 Chaos 袖口与单只钢甲样件已归档；不要移动仍被最终版调用的 V2/V3、Interlace/Relief 或钢甲辅助脚本。

## 201 原模型废案与新模型恢复（2026-09-29）

首轮 201 Meshy 模型已列为废案；962 个文件（含 116 个无外部引用的旧 UE 包）移入本机 trash，现用新模型及 50 个有引用的旧包保留。当前恢复入口为 Repair36、ClothFeed33、Magazine24 与 Accessories22，主体仍沿用 Cover10 包名。发布仅含选定修复脚本、记录和 SKILL；模型、贴图、动作、参考视频及密集数据需本机合法来源。归档散列、保留依赖和共享源码发布边界见 [201 发布与恢复说明](Weapons/lmg201-publication-20260929.md)。

## 特殊地牢房间收尾（2026-09-29）

七房当前状态、后三房待办、废案归档和源码/许可边界见 [本轮发布](Gameplay/dungeon-rooms-publication-20260929.md)。当前病区与车站从各自 `Scripts/install_pool.py` 恢复，原独立/临时测试路线退役；完整本机 Content、作者几何和原素材许可仍必需。原生接入依赖与共享攻击摘录以发布文档为准，公开源码不等于可直接运行的完整场景。

## 新版改造图标（2026-09-30）

金属框母图、PNG 与 UE 贴图留在本机；公开规则、加载代码、部署/导入脚本与映射。资源恢复、307 份旧图归档及强化入口构建限制见 [改造图标发布记录](Publication/ModificationIcons20260930/README.md)。

## 暴风雪技能与冰系资产（2026-09-30）

暴风雪已接入技能数据、区域伤害/寒冷、冷钢 UI、快捷栏、修炼和 Profile v18。专属资产由后台作者实际保存到 /Game/Skills/Blizzard；复用已导入 Fab 冰面与冰锥寒雾图集。使用方法、公式、来源、资产恢复和构建范围见 [暴风雪迁移](Skills/blizzard-migration-20260930.md)。未进行实机测试。

2026-10-01 运行乌云／砸落声音引用转入 `/Game/Skills/Blizzard/StormV2`。恢复基础资产后执行 `Tools/Skills/build_blizzard_storm_cloud.py`，依赖现有诺曼底风暴云材质／遮罩与 `S_IceImpact`，源素材不再分发；制作与实际构建状态见 [乌云与落地声音](Skills/blizzard-cloud-impact-20261001.md)。未实机测试。


## 冰墙／暴风雪图标与拖拽修复（2026-09-30）

最终写实冷钢图标、来源提示词与恢复脚本见 [图标制作记录](../SourceAssets/IceSkillIcons20260930/README.md)，正式 PNG 已实际替换。暴风雪拖拽入口修复和构建记录见 [修复记录](UI/ice-skill-icons-and-blizzard-drag-20260930.md)。未实机测试。


## 201 弹箱换弹与后续局部修订（2026-10-01）

当前是 ClothReload44.4b+BeltFit53+ArmHinge55 的十条布箱换弹，枪面 F50、提把撤除 H56、固定供弹入口 F57、三款后握把母版恢复 R58。运行时代码已在 main，本轮补充此前遗漏的作者配方与依赖；旧提把及一次性补丁等 86 份文件已归档。当前恢复顺序、公开源码/本机合法资产边界及未实机验收事项见 [201 补充发布](Weapons/lmg201-publication-20261001.md)。不要按目录编号执行旧全量导入器覆盖当前资产。

## 雷暴领域与贯穿雷枪（2026-10-01）

原版两个剩余电系技能已接入数据、修炼、Profile v19、冷钢详情与快捷栏。合法本机闪电／Blizzard StormV2依赖恢复后，运行 Tools/Skills/build_electric_magic_assets.py 生成并保存 /Game/Skills/ElectricMagic；图标从 SourceAssets/ElectricMagic20261001/Icons 恢复。雷枪满充保持的电团 Infinite 系统规则已同步全量作者；杖前魔法阵可由 Tools/Skills/build_thunder_lance_circle.py 独立保存至 ThunderLanceV2，无外部贴图依赖。来源、完整提示词与恢复入口见 [电系迁移说明](Skills/electric-magic-migration-20261001.md) 和 [雷枪充能优化](Skills/thunder-lance-charge-aim-20261001.md)。本轮不主动实机测试，母版与音频不公开再分发。

电矛发射光柱的恢复入口为 `Tools/Skills/build_thunder_lance_column.py`：ThunderLanceV2 的 Column／Coil 两份材质加引擎 Cylinder，无外部贴图／模型依赖。全量电系作者 beam() 调用同一入口；当前源码已从旧 `NS_ThunderLanceBeam` 闪电切到这组连续柱体。制作和实际保存／构建范围见 [电矛光柱](Skills/thunder-lance-column-20261001.md)，不自动运行游戏测试。

电矛光柱加粗／十字准星／杖前魔法阵增强及暴风雪凝聚棋盘格修复见 [可读性与材质修复](Skills/magic-readability-and-blizzard-material-fix-20261001.md)。定向作者 `Tools/Skills/refine_magic_readability_20261001.py` 只保存五份相关材质，已经通过现有桥落盘；全量作者同步关闭凝聚乌云的 Output Velocity，避免与 Normandy DepthFade 再次发生 SM6 编译冲突。普通源码构建状态另见该制作记录；未实机测试。

电矛后续按用户提供的彗星亚兹勒截图改为原创翻卷能量束／跳动电丝，当前引用 `/Game/Skills/ElectricMagic/ThunderFluxV3` 四资产。先用 `make_thunder_flux_mesh.py`（Blender）和 `bake_thunder_flux_fields.py`（NumPy/Pillow）生成 `SourceAssets/ThunderLanceFlux20261001` 的宿主／密度数据，再执行 `build_thunder_flux_v3.py` 实际导入与保存。`build_thunder_lance_column.py` 已转为同一入口；旧V2圆柱／光环包保留恢复。最新参数、制作来源及实际构建范围见 [电矛能量洪流](Skills/thunder-lance-flux-20261001.md)，未运行游戏测试。

该入口已同步后续射程翻倍／视觉增强50%版本：当前技能数据900／15→1800／30，束身直径264／168／87cm、电丝291cm，发光与爆闪规模×1.5；束身使用Translucent实际遮挡背景、电丝保留Additive，HLSL提高分层覆盖。无需重做既有FBX／密度PNG；重新执行定向作者保存当前材质。当前制作回执在 `Saved/ThunderFluxStrength20261001`，与初版回执分别保留。

本对话冰墙／暴风雪／电系技能的源码发布、当前恢复入口及本机素材边界见 [魔法整理发布](Skills/skills-magic-publication-20261001.md)。11份退役脚本／旧电矛资产已归档到本机trash，当前魔法阵和正式制作源保留；旧V2发射包不再位于正式Content目录。

## 九枪表面与动作差量（2026-10-01）

本轮九枪表面配方、A762 扩容/接口制作、SVD 与全武器动作差量制作的当前入口和公开范围见 [阶段发布](Weapons/weapon-surface-animation-publication-20261001.md)。原作者贴图、网格、密集采样、完整动画和 UE 包保留本机来源链；绑定清单必须与实际恢复的材质资产一起使用，不能以公开源码代替本地内容恢复。未进行本次独立构建或游戏测试。

## 主题地牢、错层坡道与全房闸门（2026-10-02）

本对话五个房间主题及其制作脚本、目录、生成/遭遇源码、翻越、出征 UI 和技能沉淀见 [地牢发布记录](Gameplay/dungeon-publication-20261002.md)。112 份退役快照/备份/收尾脚本移入 trash；正式 Blender 源、导出、纹理、生产地图与本机安装回执保留。素材复用与再分发边界见 [主题资产说明](../ThirdPartyNotices/DUNGEON_THEMES_20261002.md)。本轮直接发布现有运行源码增量，不再叠加旧交接补丁；Git 仍不包含完整本机二进制 Content，恢复后才能运行。最新全房封门已有基础 DLL 构建，未进行本轮游戏测试。

## 百目炉渣巨臂与身体浓烟（2026-10-02）

恢复本机 `Content/Monsters/HundredEyedSlag` 的 V1 骨架与基础动作、PolishV2 跑动／死亡／材质、ArticulationV12 三档网格、原路径下的 RampageV8 横扫与 V9 下劈收势、ThreeAttacksV13 激光片段、EyeLaserJumpV11 激光材质、EyeChargeV14 眼部蓄能、RagdollGroundV16 物理资产、WorldSmokeV19 目盲材质与 SmokeVisibilityFixV21 浓烟系统／材质。当前三攻击、伤害和状态以运行源码为准。

公开本次原创玩法、作者配方和恢复说明；Meshy 模型／PBR、Epic Rampage 网格与供体动画／逐帧采样、复用 MayuOrbs／ElectricMagic／Niagara Examples 材质、Mantaflow 图集、UE 包、DLL 和导入回执留在本机。旧日期不能作为判废理由，当前作者仍读 V1–V9 的模型／蒙皮输入和 V17 噪声。归档清单、最新路径、来源与未测试边界见 [百目炉渣整理与发布](Monsters/hundred-eyed-slag-publication-20261002.md)。

## 武器、手臂与呼吸增量（2026-10-03）

恢复裂角护手连续 UV 和剑身金属输入、M16 左指中立绑定、近战湿润材质、空手左右拳生成表，以及撞门 0.25 秒保持的本机作者源。公开原创实现与配方；完整采样、网格、材质包、Blend 和用户音效保持本机。未发布联机基线上的拳击增量以接入补丁保留，不夹带整套联机改动。当前恢复顺序、8 份 M16 废案归档与公开快照未独立构建／未测试边界见 [本轮整理发布](Weapons/weapon-arms-publication-20261003.md)。

## 唐刀与专属改造（2026-10-03）

当前唐刀保留燕翎刀身、游龙 SolidV4 刀身、两款龙凤护手、燕翎 ConeV3 和虎首 ConnectorV4 配重，以及祥云符文与金色限定卡。公开源码、运行目录、小型配方和 SKILL 技法；完整模型、纹理、高度图、参考图、图标与 UE 资产保持本机。废案和旧备份移至 `trash/tang-dao-retired-20261003`，仍在使用的游龙 JointRepair 符文材质保留。恢复顺序、许可和本次未进行游戏测试的边界见 [唐刀源码发布与恢复](Weapons/tang-dao-publication-20261003.md)。

## 生存状态与食水消耗品（2026-10-03）

恢复本机水瓶、Quixel 面包／法棍、Fab Soda Can、四个用户吞咽音效和 V7 手模输入。公开生存／赐福／SAN 归零源码、消耗品参数、作者配方及对应 SKILL；模型、PBR、图标、音频、UE 包和导入回执保留本机。8 个旧候选／备份已归档到 trash，体质型耐力与联机合并的未发布依赖另列，不夹带其他功能。恢复顺序、当前数值与构建／未测试边界见 [生存与消耗品整理发布](UI/survival-consumables-publication-20261003.md)。

## RSH-12：当前双动改造与资源恢复（2026-10-06）

当前为双动五发、715 共用动作与 RSH 私有握姿；基础握姿及 ADS 同步已获用户认可。方形瞄具、PSO 侧架、加长方盒消音器、制退器、三种防滑纹、两款专属握把本体、通用前握把和右偏激光／手电，以及最新原厂扳机图标的恢复顺序见 [RSH 改造发布与恢复](Weapons/rsh12-publication-20261006.md)。模型、PBR、图标、UE 包、完整姿态与原生 DLL 均保留本机；本次公开源码和制作配方，未重新运行游戏测试。下面保留旧单动暂停时的历史记录，不作为当前制作入口。

## RSH-12：五发单动与暂停修订（2026-10-03）

恢复本枪需要 Medji 的 CC BY 4.0 原始包、合法 715／V7 手臂供体、原生姿态与本机已保存的 RSH 资产。最新握持／ADS 拨锤源码未完整烘焙和保存，旧导入回执不能代表当前候选。作者入口、十个目标资产、废案散列、保留输入与恢复顺序见 [RSH-12 暂停与发布](Weapons/rsh12-pause-publication-20261003.md) 和 [待办](Backlog.md)；署名见 [Medji 来源记录](ThirdParty/RSH12-Medji-CCBY4.md)。本轮公开源码／配方／参数，二进制、密集姿态、日志与 trash 留在本机，不新增游戏测试。

RSH 后续采用状态（2026-10-04）：用户已认可 [双手握姿与 ADS 同步](Weapons/rsh12-unified-grip-20261004.md)，当前为双动、五发快速装填器版本，不再沿用上述暂停中的单动拨锤候选。五款通用瞄具及私有导轨转接座的运行依赖、制作入口与保存/构建回执见 [RSH 通用瞄具](Weapons/rsh12-common-optics-20261004.md)。本轮瞄具未进行游戏测试。

## 焚化炉主题与共用宝箱细节版（2026-10-03）

采用的正式主题为 `ShoredBreach → AbandonedIncineratorHall → AbandonedFlueGasStation`，正式地图仍为 `/Game/GameMaps/L_Dungeon_Randomized`。五类原创可动箱柜的建模、标签、材质、候选位和接入配方见 `SourceAssets/IncineratorContainers20261003`；三房为 17–20 件实体、22–25 个独立搜寻入口。平台下宝箱位置见 `FlueUnderPlatformChest20261003`，最终采用入口见 `DungeonTreatmentTheme20261003`。

共用探险宝箱细节制作见 `GamedevTreasureChestDetail20261003`：原创金属 PBR 与内外结构，通过 GeometryScript 写回原正式网格；原 `GamedevTreasureChest20260922` 骨架、动作和本地上游源继续使用，Normandy 木材纹理按已有许可恢复。旧粗糙版本已经可恢复地归档；新版 helper 自包含，不依赖旧版本目录。

公开原创建模/PBR/组装配方、参数、容器通用运行支持和说明；UE 包、Blender/FBX、生成贴图、完整运行快照、第三方源与恢复包留在本机。钢、橡胶、描边材质继续引用本地员工生活区已保存资产；线路测试图的宝箱碰撞蓝图继续引用本地 StationWorkshop，正式运行不依赖该预览蓝图。恢复配方前需具备这些 Content 依赖，不手写资产安装成功回执。

按用户要求保留医院、车站和焚化炉线路测试地图；只归档本轮废案。详情及公开归档摘要见 [采用与发布](Gameplay/incinerator-theme-publication-20261003.md) 和 [归档清单](Gameplay/incinerator-theme-trash-20261003.json)。本轮后台保存完成，未运行游戏、PIE、渲染或测试。


## 上挑与四枚技能图标（2026-10-04）

当前动作源为 GripRecoveryV15，运行技能已接入 V17–V20 的伤害、修炼、消耗冷却、范围成长与前踏时序。上挑、重击、冲刺攻击、旋风采用同系列圆角方框人物图标。414 份废案已归档；当前合法骨架输入、密集姿态、图像和 UE 包仍在本机。作者入口、恢复顺序、历史构建与本轮未测试边界见 [上挑整理发布](Weapons/sword-uppercut-publication-20261004.md)。本轮公共源码按独立上挑整理，不夹带共享文件内其他任务的普通第三段、削韧及其他增量。

## 镇岳资源补充（2026-10-08）

镇岳、镇魔／金刚符文、蟠螭展岳护手及共用改造的现行制作入口、许可边界与本机恢复要求见 [镇岳发布记录](Weapons/xuanchi-publication-20261008.md)。公共仓库仅含源码、目录与作者配方；认可图片、用户 Meshy 模型、Blend／FBX、uasset、字体及活动导入回执仍需从许可完整备份恢复。

## Super90 散弹枪（2026-10-12）

最新整理、恢复依赖与发布边界见 [10 月 12 日整理记录](Weapons/super90-publication-20261012.md)。本轮 598 份废案／旧备份已带 SHA256 移入 trash；下述版本沿革不覆盖最上方的当前入口。

快速装填的最新播放节奏为 [R25 前 30% 对准／后 70% 推进](Weapons/super90-speedloader-r25-align-drive-20261012.md)。用户已确认现有动作，保留当前资产轨迹；`Super90LoaderPushTiming.h` 将完整推进源帧 86–110 映射为 30 个属性帧，前 30% 行程占 18 帧，后 70% 占 12 帧，之后按原速延后六帧。恢复入口 `SourceAssets/Super90LoaderR25_20261012/author_timing.py`；需一起保留 `FPSGAMECharacterSuper90.cpp` 的动作时长与源时间结算、`Super90SpeedloaderVisual.cpp` 的声音队列时钟。原声、镜头强度、完整推进和一次补满保持，未运行游戏测试。

普通空仓收尾的最新播放节奏为 [R2](Weapons/super90-native-empty-pacing-r2-20261010.md)：用户否定上一版的过快节奏，现保持下述 7.4 秒姿态资产，用运行时单调 Hermite 源时钟将 1.4 秒源尾段展至 2.16 秒属性时钟（基础倍率下约 1.66 秒），并同步音效反算与中断续作。时间表和源备份在 `SourceAssets/Super90NativeEmptyPacingR2_20261010/`，恢复时保留两份 C++ 的节奏映射；不能把资产片长直接当作游戏收尾时长。未运行游戏测试。

普通空仓最新采用[抓握拉机柄收尾](Weapons/super90-native-empty-grasped-bolt-20261010.md)，作者源 `SourceAssets/Super90NativeEmptyBolt20261010/`。保留原逐发装填，接 0.3 秒源时长的右手回握，再接原速 1.1 秒 R24 cycle；总源长 7.4 秒，保留 5 mm 枪机额外后拉。普通空仓序列及四份 Profile 对应条目已保存，`save_receipt.json` 为 completed=true，五套可编辑动作位于 `Super90_NativeEmpty_Editable.blend`；其他动作条目保持。恢复需同步三份 C++ 文件的拉柄时钟、音效跳段映射和 cycle-only 续作逻辑，不能仅恢复动画或把 `FullReload` 属性换算参考改为新片长。Editor / Game 构建完成，未运行游戏测试。

普通移动最新采用[待机右手握姿](Weapons/super90-locomotion-idle-right-grip-20261010.md)，作者源 `SourceAssets/Super90LocomotionIdleGrip20261010/`。用户认可当前 idle；walk / run 的完整右链按各自待机枪身空间关系制作，保留原移动起伏。两份原生动画和四份 Profile 已保存，回执 `save_receipt.json` 为 completed=true；十套动作保存在 `Super90_Locomotion_IdleGrip_Editable.blend`。恢复时在原移动动画与握把配置之上应用此补丁，不能反向改写认可的 idle。未运行游戏测试。

快速近战最新右臂修订为 [RightArmR9](Weapons/super90-quick-melee-right-arm-r9-20261010.md)，作者源在 `SourceAssets/Super90QuickMelee20261008/RightArmR9/`。R8 的右前臂轮廓仍被用户指出问题；R9 取消辅助骨向腕锚偏移和完整腕弯混入，按实际站位分配轴向转动，并局部平顺两份 Super90 网格的右肘表面。保留右掌、手指、肩肘路线以及 [R7](Weapons/super90-quick-melee-20261008.md) 的枪路、左臂竖直折叠和动作时钟。近战序列、四份握把 Profile、两份网格共七项及五套可编辑动作已保存；回执 `RightArmR9/save_receipt.json` 为 completed=true。运行保留原近战交接曲线及已编译 `Super90SupportArmNode.cpp`，恢复时保留 R5 校准、R23 左肘补丁及 R9 右肘补丁。R24 快速拉栓及其他动作轨道保持，无新 C++ 改动。本轮后台保存，未运行游戏或新增渲染，待用户体验。

快速拉栓机械修正现为 [R24](Weapons/super90-speedloader-r24-bolt-rear-stop-20261010.md)：用户红圈处是枪机后端越过机匣后上表面，额外后拉由 24 mm 缩至 5 mm，左掌接触位移同步修正，松手后平滑交给原回握。八个动画及四份握把 Profile 已后台实际保存，保留 R7 近战和全部其他条目。作者源、局部平移补丁和保存回执位于 `SourceAssets/Super90LoaderR24_20261010/`；没有新增 C++、没有运行游戏或新增渲染，待用户体验。

手臂支撑基线仍为 [R23](Weapons/super90-speedloader-r23-wrist-support-clearance-20261010.md)：最终姿态后的 Super90 左臂支撑覆盖待机和换弹，修正辅助骨扭转及肩肘；局部平顺裸臂肘部，调整空仓抓握掌心／拇指与接近绕行。R23 的手部数值没有覆盖本次枪机穿模，不能作为机械件已修复的证据。恢复时先保留 `SourceAssets/Super90LoaderR23_20261010/` 的支撑代码和两网格表面修正，再应用 R24 的两骨平移补丁；保留 R21 发力反馈、R22 镜头、完整推进速度、声音、一次补满与 60 ms 间隔。下述 R14–R22 为历史沿革。

源码、原生导入配方、瞄具／前握把、装备派生和 R5 快速近战的恢复入口见 [Super90 整理发布](Weapons/super90-publication-20261009.md)。511 份旧稿／备份已归档到本机 trash；模型、声音、完整姿态、Blender 与 UE 包留在合法本机。快速装填 R11 因手臂扭曲、细节不可见被用户否定；R12 按“枪托抵肩、参考枪姿与取景”重做。R13 随后因推进像接触即结束被用户否定。用户现已确认 [R14 完整推进](Weapons/super90-speedloader-r14-preserved-push-20261009.md) 装填动作没有问题。当前 [R15 原声与推进加速](Weapons/super90-speedloader-r15-audio-drive-20261009.md) 保留认可轨迹，推进 48 → 36 帧，并从参考视频截取七段独立快速装填声音；普通逐发声音保持。15 段动画、四份握把配置及七段 SoundWave 已保存，沿用当前模型、材质和 idle。后续按用户要求继续制作 [R16](Weapons/super90-speedloader-r16-snappy-push-20261009.md)，推进再由 36 → 24 帧，最初松手 5 → 3 帧；七段原声保持，同步接触与镜头时钟。当前编译边界见 R16 记录；R16 节奏与 R5 左臂仍待用户体验，本轮未启动游戏测试。

Super90 快速装填手部续修（2026-10-09）：用户明确手臂没有问题，仅修推完后的反手拉栓手部。当前 [R17](Weapons/super90-speedloader-r17-hand-hook-20261009.md) 只修改左手五指旋转，采用食指主勾、中指辅助、拇指张开及复进前松指；保留 R16 腕部、手臂、完整推进与音画时钟。八个空仓／单独拉栓动画和四份握把配置已通过现有编辑器桥保存；未改 C++，未进行游戏测试。

后续曾制作 [R18](Weapons/super90-speedloader-r18-direct-drive-20261009.md)，其换弹部分随后已被否定：直接从完整推进起点进入换弹，推完快速松手与回握，空仓保留拉栓；Super90 基础射击间隔由 650 ms 改为 60 ms，最快下限也为 60 ms。14 个动画、四份握把配置及常规 Editor/Game 编译均已完成，未运行游戏测试。

当前 Super90 换弹已[恢复 R17](Weapons/super90-restore-r17-20261009.md)：完整取出、对接、推动、松手、空仓拉栓与回握，以及原音画时钟均已恢复，重新保存 18 项资产并完成常规编译。60 ms 基础射击间隔与下限保留。用户真正要求的是保持动作原速、提前掏出、消除阶段间等待，不能删取出／对接或整体快放；该新节奏尚未另行实施。

随后按追加要求制作 [R19 一次补满与上臂避让](Weapons/super90-speedloader-r19-full-fill-arm-20261009.md)：快速装填在原压实点一次结算全部可装弹药，左臂在保留腕点、手型和时间轴的基础上作 4° 弯面避让。当前 normal／empty 的 14 个动画和四份握把配置已保存为 R19；cycle-only 保留 R17。作者源、导出、导入回执及覆盖前备份在 `SourceAssets/Super90LoaderR19_20261009/`，原生构建回执同目录记录。没有主动运行游戏或渲染。

当前左臂更新为 [R20 松手／拉栓臂根修正](Weapons/super90-speedloader-r20-shoulder-clearance-20261010.md)：R19 在锁子甲截图中仍暴露近身上臂，本轮按真实衣袖和当前腰射锚点调整该段肩肘，保留手部、节奏和完整推进。14 个动画、四份握把配置已后台导入落盘；作者源及回执在 `SourceAssets/Super90LoaderR20_20261010/`。本轮按用户明确要求进行源画面与导入采样检查，未启动游戏测试。

Super90 当前继续更新为 [R21 发力反馈与抓握拉栓](Weapons/super90-speedloader-r21-response-grasp-20261010.md)：在用户确认的动作与原速上增加枪体、右臂的短促回弹和较小、稍迟的屏幕反馈；拉栓改为四指收拢、食中指承拉、拇指侧向支撑。15 个 loader 动画、四份握把配置已后台保存，Editor／Game 必要构建成功。保留 R20 左臂避让、原声、机械时点与一次补满，制作源和回执在 `SourceAssets/Super90LoaderR21_20261010/`；本轮未渲染、未运行游戏或测试。

屏幕强度随后按用户要求更新为 [R22](Weapons/super90-speedloader-r22-camera-strength-20261010.md)：保留上述 R21 动画资产，对接／压实／拉栓相机冲量按 ASH-12／PKM 及项目共用倍率标定，参考背景轨迹保持。仅修改相机源码和生成曲线，不重导入资产；制作源及必要构建回执在 `SourceAssets/Super90LoaderR22_20261010/`。

R21 初次导入的动画目录误写为 `Speedloader21261007`，因此上述初次保存不代表运行时已使用新动画。2026-10-10 已修复 `import_r21.py` 并重新后台保存到实际使用的 `Speedloader20261007`：15 个动画、四份握把配置共 19 项，日志 `SourceAssets/Super90LoaderR21_20261010/import-commandlet-20261010-111457.log`。错误回执和修复前配置保留在 `PathFixBefore/`，R22 镜头代码不变，未运行游戏测试。

## 第三人称法杖、持书与进食／饮用（2026-10-10）

当前制作、配置入口、合法素材依赖、归档清单和发布边界见[第三人称动作源码发布与恢复](Publication/ThirdPersonActions20261010/README.md)。右手与空闲左手复用已认可第一人称抓握，整臂使用当前 CarryClearance／StrikeCarry／BookCarryRelax／BookPush 派生；饮用使用 WizardDrink，进食使用已修复上臂覆盖问题的 FoodNative。六组新动画已补齐 Cook 目录；本次没有执行打包。Fab 原包、完整关键帧、派生 uasset 和退役文件留本机，不能仅凭公开配方重建全部资产。

## 玩家观察、近战与穿戴修复（2026-10-12）

公开面板中装备待机、F6 固定第三人称、剑术挂接同步、两段竖劈及唐刀旋风的制作配方、七分裤腰部与背包背带修复。模型、原生动作、密集绑定、UE 包及日志仍留本机。30 份旧备份和失败中间产物已带 SHA-256 移入 trash；恢复链、当前方向、资产许可边界及未游戏测试范围见 [整理发布](Publication/PlayerPresentation20261012/README.md)。

## 魔法书收尾（2026-10-12）

当前 V30 动作、16 面书页和方向修正、受击接书、共用近战时钟、属性及联机专注的恢复顺序与公开边界见 [魔法书收尾发布](Publication/Spellbook20261012/README.md)。627 份废案已带 SHA-256 移入本机 trash；V23/V24/V9、V2 握点和未旋转页面母版仍是活动输入。公开源码、配方和小型参数，原素材、完整采样、Blend/FBX、UE 包和构建产物保留本机。

## 接待大厅灯光标准与出怪门遮蔽（2026-10-13）

公开灯具匹配／射程／廊下补光配方、实际运行灯光方向修正、左右检修门位置与黑色雾幕原创作者源码，以及场景标准。UE 地图、网格、材质、授权灯具和原始场景数据保持本机；重建从最新已保存目录增量安装，不把全场景混合快照当作本次公开补丁。179 份无效预览、失败日志与重复备份已带散列移入 trash，当前恢复源和有效回执保留。恢复顺序、发布范围和未测试边界见 [场景照明整理发布](Publication/SceneLighting20261013/README.md)。

## 木工工作台（2026-10-13）

当前源码、正式整弓/法杖配方、两阶段管理面板、评分品质、局部联机接入补丁及资产恢复边界见 [木工发布记录](Publication/Woodworking20261013/README.md)。当前 V6 台锯与红色锯齿提示仍依赖 V4/V5 制作输入；原模型、贴图和 UE 包留本机，不随源码发布。修改前快照和废弃卡片方案已按清单归入本机 trash。

## 双手战锤动作、格挡与联机修复（2026-10-15）

原创战斗代码、作者配方、格挡接入与网络轮次修复见 [战锤战斗发布](Publication/WarhammerCombat20261015/README.md)。被否定三连击 V2/V3、退役备份及失效日志共 322 份已带 SHA-256 移入 trash；活动原生骨链与母版依赖保留。共享文件按具名基线保存补丁，公开切片不等于完整本机工程；模型、音频、UE 包和密集采样仍需合法本地来源。本次按用户要求不再运行游戏测试，旁观者专用音效和真实双端验收仍有剩余项。

## 战锤检视、第二段换手与普通连击节奏（2026-10-16）

公开战锤 L 检视／行走检视、第二段换手、普通连击 V7 节奏与不改 DPS 的视觉承接的独立源码、作者配方、联机复核修正与 SKILL；与其他战锤及并行工作交织的共享文件只保存本次补丁，公开切片不等于干净检出可构建。被否定的行走检视 V1/V2、普通连击 V6、三份 Before 快照、逐帧诊断图与重复日志共 239 个文件带 SHA-256 移入 trash。Blend、FBX、UE 包、回执与测量数据留本机。恢复链、补丁边界和未实测项见 [发布记录](Publication/WarhammerInspectCombo20261016/README.md)。

## 合阙最终首领（2026-10-15）

公开合阙五类招式、控制恢复、原生击退、心脏弱点、原创制作配方和对应 SKILL；最终房间与未公开共享框架交织的接入保存为 25 路径具名前置补丁。46 个废案/旧备份已带 SHA-256 移入 trash，当前模型、混合版本作者输入、UE 包、日志和存档留本机。此前控制状态联机用例与默认预加载客机载图已有记录，完整地牢并发搜刮/队伍返程未跑完，用户改为自行测试；无界面兼容源码仍未构建。本次不新增运行验收。恢复依赖、发布边界和归档见 [合阙发布记录](Publication/HeQue20261015/README.md)。

## M870 Tactical（2026-10-17）

源码、目录与作者工具见 [M870 发布和恢复说明](Publication/M87020261017/README.md)。完整本机资产位于 `/Game/Weapons/M870/`；当前基础动画为 LeftArm 组合修订、快速近战为 R3、通用握姿与快速装填为独立 Profile。Git 不包含 Blend、FBX、UE 包、音频、图标、原始下载或密集姿态。

枪体、V7 手臂、SUPER90 供体、UC 动作与声音分别保留来源。UC_Workfiles 所选源没有确认独立游戏再分发许可，原始和派生动作留在本机，公开作者脚本不授予该素材权利。恢复后不要重导早期装备／装填版本覆盖当前手型。317 份确认废案已归档，当前母版及有效工具前置保留。

## 食物、手套衣袖与弓动作交接（2026-10-18）

公开本轮手部、消耗品与持弓动作源码、制作配方及 SKILL；混合宿主中的 UI、M870 授权表面控制点和诊断入口分别保存具名前置补丁／恢复依赖。216 份退役初稿、错误服装旧包、中间资产和构建检查输出已带散列移入 trash；Sparrow、原生皮肤、UE 包与完整回执留本机。历史 180 项隔离及 28 组限定本地 UDP 结果与本轮只做仓库检查分开记录。范围、恢复顺序与限制见 [整理发布说明](Publication/BowFood20261018/README.md)。

## 地牢性能与区域提前准备（2026-10-19）

公开本批独立的预加载、F6 采集、预览/尸体资源生命周期和装备通知修正；区域首领/门禁等未发布前置上的准备池接入按散列基线补丁保留。276 项旧快照、空输出和已完成的隔离宿主归入 trash，原始证据可按清单恢复。Editor/Game 本机整合构建成功；客户端每实例缓冲、特殊怪完整 GPU 预热、物理驻留映射与联机运行覆盖仍未完成。发布切片不等于完整可构建游戏，恢复与证据边界见 [本轮发布记录](Publication/DungeonPerformance20261019/README.md)。

## 斩马刀与传说改造（2026-10-19）

模型长度、通用改造、标准图标、背嵬、赤霄、逐风、唐刀刀身群体判定及旋风联机修复见 [斩马刀发布记录](Publication/Zhanmadao20261019/README.md)。共享宿主使用带基线散列的接入补丁；模型、图标、动作和密集姿态输入留在本机，公开树不代表完整工程的独立构建副本。

## ST6、法师套装与钢盔（2026-10-20）

公开源码、制作脚本、当前服装配方及本轮归档清单见 [Outfits20261020](Publication/Outfits20261020/README.md)。原生角色／武器依赖、密集几何、Blender／FBX、PBR、PNG、UE 包与构建／保存回执留在本机，不能从 Git 克隆推断已恢复。当前法袍保留 FacingFix20261020、HemContinuity20261019 与 cross-section-v3；钢盔保留 ReferenceMatchV5。复原顺序、仍有效的旧输入和历史联机证据边界见该入口。

## 连续皮革长靴与装备搭配（2026-10-22）

公开 TailoredV2 制作工具、实际渲染 LOD 读回、旧物品展示兼容、裤装与法袍接入依赖、骨架曲线迁移修复及网络检查夹具。旧版仍被使用的几何／纹理和兼容展示路径保留；确认退役的输出与排除的诊断尝试带散列归档。UE 包、扫描贴图、FBX／Blend、密集采样与测试存档留本机。此前同机监听主机、客机及重连 14 项通过，不代表公开切片已独立构建、专用服务器、跨机打包或画面验收。见[发布范围与恢复](Publication/LeatherBoots20261022/README.md)。

## 符文战锤、传说锤头与能量条（2026-10-23）

公开符文战锤被动、两种魔力符文、两款传说锤头、模块数据和原创制作脚本。共享框架中交织的动作/权威消费者以带基线散列的接入补丁保留；本次公开切片不等于干净检出完整编译。用户提供Meshy模型、UE包、贴图、动画与图标母图留本机。543份退役快照、错误图标、一次性改码器和重复导入宿主已带SHA-256移入trash；本机已有73项资源检查、37项隔离权威和一次真实UDP测试通过，未做渲染验收，整理阶段未重跑。恢复与发布边界见 [本次整理发布](Publication/RuneboundWarhammer20261023/README.md)。

## 公寓与海湾增量制作、联机修补（2026-10-24）

本次公开公寓/海湾制作配方、楼体与灯光、广告/道路、水体、阳台玻璃栏杆、设备与门原生代码，以及共享消费者中的限定差量。最新坐卧动作已经由另一轮精修接续，本批不重写其配置，不恢复历史 V14 默认；共享搜索与坐卧基础的本机前置及限定补丁单独列出。二进制地图、模型、贴图、动画、字体、密集采样和完整运行回执仍需本机合法来源，仓库克隆不等于可运行完整场景。退役快照和首次失败检查已带 SHA-256 移至本机 trash。恢复顺序、资产和发布边界见 [公寓发布说明](Publication/CyberpunkApartment20261024/README.md)。

## 手枪动作与弹药修复的恢复边界（2026-10-24）

本机已保存的左右单持／双持动作、五枪左主手与六段换弹精修，使用本地 Jason、枪械原生输入、Twinblast 及用户选定的 GitHub 动作源。原始二进制和密集姿态数据不随源码公开。公开代码、待接入补丁、20 个角色配置键、资产散列、许可及制作顺序见 [手枪发布交接](Publication/Pistol20261024/README.md)。当前为部分源码发布，完整角色／库存／联机消费者尚有共享基线依赖；历史本机构建与测试不代表公共提交已独立验收。
## Kaitlin 女性身体、装备与外观同步（2026-10-24）

公开 F6 身体切换、原生毛发/服装配置、家具相机与夹克背包作者脚本；联机/家具共享宿主修复和九个依赖较新包体/动作的字段，以带前置散列的接入材料保留。93 份废案已移入 trash，正式资产、授权源与制作输入留本机。历史完整本机 Editor/Game 构建成功，公开切片未重新构建，也未进行实际联机或视觉验收。范围与恢复顺序见 [女性角色发布说明](Publication/Kaitlin20261024/README.md)。

## 服装、帽子和腰带（2026-10-25）

本段制作入口、精确发布范围、依赖补丁、技能沉淀和废案归档见 [Equipment20261025](Publication/Equipment20261025/README.md)。正式模型／贴图／UE 包与有效作者输入留在本机；公共配置与其所属消费者一并记录，混合宿主的未独立发布依赖单列。

## 家具坐卧、双人床与存储入口（2026-10-25）

椅子／沙发／床铺共 25 个模型配置、45 个位置，其中 7 款双人床分左右占位；Bed Idle 权威恢复 SAN 5 点/秒。公开运行组件、镜像接入、精确动作／相机配置及作者工具。Meshy/Fab 原素材、密集骨骼／几何数据、UE 资产包和存档仍需从合法素材与本机/NAS 备份恢复。当前 Content 通过 D 盘工程入口联接到 F:/FPSGAMEData/Content，DDC 使用独立 Caches 目录，不能混作废案。发布内容、14 个旧保存／发布入口及一次性辅助脚本的 trash 清单、制作依赖和未验收范围见 [家具坐卧发布说明](Publication/FurnitureRest20261025/README.md)。

## 战锤后续改造与冲刺发布（2026-10-25）

本对话新增的传说锤头刻纹/PBR、紫蓝配重球、破势古印与鸣雷锤座、V5 原生重击复用、冲刺及第三人称联机修复，恢复范围见 [发布说明](Publication/WarhammerRefinements20261025/README.md)。源码和配方精确发布；混合共享消费者以具名接入片段记录，公共快照不声明可独立编译。模型、贴图、动画供体和 UE 包保留本机，未移动 Content；旧废案移至 trash 并记录散列。Kaitlin 当前接触修正版动作字段保持原值，勿重跑 V5 旧发布器覆盖。

## 背包与战斗腰带修订（2026-10-26 发布）

七款背包贴合、正面图标、容量与重力；破阵／星律腰带和非箭袋横 3 × 竖 2；共享减耗公式的源码、配置键、制作源依赖与废案恢复边界见 [BackpacksBelts20261025](Publication/BackpacksBelts20261025/README.md)。UE 包、贴图、模型及原生身体衍生数据留本机。坚冰铠甲／雷电迅捷扩展以带前置散列的接入补丁保存；本批不包含这两项完整独立技能，不宣称公开子集重新完成构建或联机。

## 篝火食品与面板补充发布（2026-10-27）

篝火面板、食品保鲜与事务、七类菜谱、野味模型制作工具及共享接入资料见 [篝火发布清单](Publication/Campfire20261027/README.md)。六款野味衍生模型、贴图、图标及 UE 包留在本机授权内容恢复链；源码和工具已按精确路径整理发布。

## 弯刀改造、流血与传说符文（2026-10-28）

本轮源码、最终目录、原创制作配方及共享接入补丁见 [发布说明](Publication/KukriMods20261028/README.md)。基础弯刀与合法素材、生产模型、PBR／法线、图标、UE 包和制作宿主留在本机，GitHub 不包含这些二进制。当前 HUD 为 WolfHeadComposite；VolumeRefine 的刀面投射仍为活动供体，废弃整体能量柱及旧浮雕已移入 trash。按发布说明恢复供体和资产，再整合同版本战斗／网络前置；不要把公共源码切片当作完整可运行工程。

## 弯刀霜鸦定稿与联机回查增量（2026-10-28）

霜鸦最终鹰头和刀面纹样分别以 `SourceAssets/KukriFrostRaven20261028/CrystalCrownV3`、`BladeSigilV2` 为准，生产入口已同步。原图、已保存 UE 包、法线及图标在本机保留，公开仓库仅保存原创配方和参数；旧银色头像、低模鹰头及粗羽纹移入 `trash/kukri-refinements-retired-20261028`。

本轮发布还包含右侧能量条、弯刀稀有度及观察者狂战士表现修复。双刀组合冲刺流血的共享文件增量独立保存，依赖前轮宿主框架；公共检出仍非完整可运行内容。归档哈希、资产恢复清单和既有75项隔离／6阶段UDP证据见 [发布说明](Publication/KukriRefinements20261028/README.md)。整理发布未启动 UE、重新构建或重跑玩法测试。
