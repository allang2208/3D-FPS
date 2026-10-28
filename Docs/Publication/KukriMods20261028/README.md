# 弯刀改造、传说符文与寒冷统一整理

2026-10-28。工程为 `D:/FPS3D/FPSGAME`，发布目标为 `allang2208/3D-FPS` 的 `main`。本轮整理弯刀模块、数值、材质、图标、挂饰、流血、狂战士／霜鸦符文及既有联机修复；不包含其他任务的基础动作、动画或其他武器开发。

## 最终内容与当前来源

最终选项以 [弯刀目录](../../../Content/ColdSteelData/kukri-gunsmith.json)、[通用刀身](../../../Content/ColdSteelData/shared-knife-blade-options.json)、[通用组件](../../../Content/ColdSteelData/shared-knife-component-options.json) 为准；[模块表](../../../Content/ColdSteelData/kukri-modules.json) 保存实际装配、材质与挂饰参数。共五个改造槽，常规每槽三款，另有猎手／犬牙特殊刀身与狂战士／霜鸦传说符文。原厂选项不计入这些改造数量。

- 双持按实际刀实例独立求伤害、耗体和附加属性。组合动作保持既有总费用规则，分别计算两刀贡献后合并。攻击速度以各刀原厂间隔为基准；达到上限仍显示配件标称加成与实际零变化。
- 犬牙刀身物理伤害+20%、韧性伤害-50%，有效近战接触叠加流血。流血通过通用生命值接口扣血，伤口喷发跟随身体，落地血迹复用现有预算与贴花池。
- 狂战士常驻本刀物理伤害+10%，12次有效出手激活20秒；同符文双持共用槽、效果不叠加，切换武器退出。当前能量条保留原下段柱体，顶端使用 `WolfHeadComposite` 的立体观感图层；这是2.5D HUD，不能称作新增世界三维狼头。
- 霜鸦常驻暴击率+20%，8次有效出手激活16秒霜狱，韧性伤害+35%；期间同一出手对每个目标寒冷+4层。触发激活的出手不提前获得激活加成，持续期间不续时、不预蓄能。
- 寒冷所有来源每层减速5%，20层触发冻结并消耗10层；冻结期间拒绝新层。来源原有持续时间、刷新或累加方式保留。

## 公共源码和共享接入

独立符文组件、模块外观、挂饰动力学、流血表现、寒冷常量、最终目录和原创制作配方保存到原路径。共享文件中其他任务的内容保持原状，未整体加入提交。

1. [modification-integration.patch](modification-integration.patch) 是从具名 Git 基线重建的本轮共享增量，包含数值求值、显示、命中快照、流血／寒冷与模块挂接；[integration-baseline.json](integration-baseline.json) 记录基线提交、候选及本机文本 SHA-256。补丁采用零上下文，只有在核对基线后才可用 `git apply --unidiff-zero`；它不能替代下述完整宿主绑定。
2. [host-bindings.cpp.inc](host-bindings.cpp.inc) 保存依赖完整本机动作／复制框架的接口、服务器动作编号函数、调用点和数值绑定摘录；[host-binding-baselines.json](host-binding-baselines.json) 标识对应本机版本。摘录不是独立编译单元，也不是可直接重复粘贴的完整函数。重击、上挑、旋风和副手接入仍需同版本基础动作的声明与生命周期。
3. [catalog-integration.json](catalog-integration.json) 保存共享物品／技能／状态目录中本轮字段的精确值，避免发布这些文件里的其他未提交内容。数组位置适用于记录时目录版本，移植前按相应选项身份匹配。
4. 新增的 `KukriRuneAuditCases.cpp` 扩展现有 `UKukriNetworkAuditCommandlet`；需同时恢复该独立维护的夹具、服务器影子档案与动作回执框架。其声明／调用点见接入摘录。

公共仓库仍是源码切片，不能把干净检出当作完整可运行工程。补丁需要同版本基础弯刀、武技、装备复制、服务器命中回执与天气武器枚举前置；本机完整工程已经应用这些改动，**不要在本机重复套补丁**。公开切片未重新构建。

## 制作与资产恢复

活动模型、PBR／法线、图标与 UE 包保留在本机，清单见 [local-assets.json](local-assets.json)。基础刀模型和第三方合法素材需要单独恢复，公开作者脚本不包含原资产许可，也不保证从空目录重建全部资产。

| 内容 | `SourceAssets/` 下当前配方及依赖 |
|---|---|
| 原装模块、三款刀身与其余常规组件 | `KukriModules20261026`、`KukriBladeVariants20261026`、`KukriComponentVariants20261026` |
| 钢材、握柄法线与标准图标、挂饰 | `KukriBladeSurfaceV220261026`、`KukriGripSurfaceV220261027`、`KukriRefinement20261027`；保留原材质供体与制作宿主 |
| 猎手与犬牙 | `KukriHunterBlade20261027`、`KukriCanineBlade20261027`；保留对应可编辑母版、图标与导出网格 |
| 流血喷发与落地血迹 | `BleedingFixBurst20261027`；血迹复用已有 GunplayFX 材质 |
| 普通符文比例修复 | `KukriRuneNatural20261027`；每刀独立拟合并保留源图比例 |
| 狂战士符文、能量条、手臂与武器发光 | `KukriBerserker20261028` 根目录、`ActiveFX`、`WolfHeadComposite`；`VolumeRefine` 的刀面投射仍为活动依赖 |
| 霜鸦 | `KukriFrostRaven20261028/ProductionV1`；依赖狂战士的投射与源刀面供体，停止使用已退役的 `prepare_runtime.py` |
| 平衡及 UI | 各 `*Balance20261027`、`KukriAttackSpeedBaseline20261027`、`KukriAttackSpeedCard20261027`；最终数值始终以正式目录为准 |

恢复次序为合法源素材／基础弯刀 → 常规模块与材质 → 法线、图标和挂饰修订 → 特殊刀身 → 普通／传说符文及最终 HUD → 正式目录 → 完整战斗源码与打包目录。旧初始化脚本可能写入当时方案，不能把所有脚本按目录顺序无差别重跑。机器路径、Blender、UE 和制作宿主路径需要按实际环境调整。

`Content` 为指向 `F:/FPSGAMEData/Content` 的活动联接；本次没有移动任何正式 UE 资产，也没有改变原图标或法线。

## 归档与技能

317个文件、288.44 MiB 已移至 `trash/kukri-mods-retired-20261028`，逐项移动后 SHA-256 一致，没有永久删除。范围为被否定的整柱能量条、旧线稿浮雕、退役生成器、被替换的 Before 快照和作者备份／缓存。源路径、目标、原因与替代物见 [归档清单](archive-manifest.json) 和 [完成记录](archive-receipt.json)。原始日志、失败证据、活动供体、当前图标源和制作宿主均保留。

个人技能与工程镜像同步更新：

- [改造结算合同](../../../skills/ue5-weapon-workflow/references/attachment-effect-contracts.md)、[符文表面与局部拼接](../../../skills/ue5-weapon-workflow/references/rune-surfaces.md)。
- [装备符文与攻击回执](../../../skills/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)、[寒冷状态统一](../../../skills/ue5-skill-magic-workflow/references/status-effects-buff-migration.md)。
- [百分比显示](../../../skills/ue5-ui-umg-slate/references/percentage-display.md)、[浮窗字段](../../../skills/ue5-ui-umg-slate/references/weapon-tooltip-schema.md)、[改造详情](../../../skills/ue5-weapon-workflow/references/attachment-detail-presentation.md)。

## 既有证据与交付边界

最近一次霜鸦／寒冷定向回查已修复观察者冰光与粒子缺失、范围攻击可用客机编号重复蓄能、霜鸦缺少 AlwaysCook 目录的问题。完整本机 Editor 构建成功，57项隔离检查通过，其中23项为本轮符文／复制检查；18个霜鸦声明资产存在。详见 [历史证据](validation-evidence.json) 与 [回查记录](../../../SourceAssets/KukriFrostRaven20261028/NetworkReview20261028/review.md)。

这些是先前授权回查的结果，不能外推成整套改造已通过真实联机验收。本次仅整理、归档、检查提交范围和发布，没有启动 UE、游戏或重新运行玩法测试。真实主机／客机、延迟／丢包、重连、视觉和实际打包仍由用户测试。
