# 战锤改造与共用符文整理发布

2026-10-15。工程为 `D:/FPS3D/FPSGAME`，目标为 `allang2208/3D-FPS` 的 `main`。本轮整理金属／锻钢战锤组件、改造数值、共用符文及已完成的联机修复；没有重做战锤基础动作，也没有启动编辑器或游戏。

## 本机最终内容

原装模型拆成六个实体，菜单保留锤头、中央锤座、符文、握持包覆、柄尾配重五槽。金属长柄保留实体，退出改造菜单。普通锤头三款、中央锤座三款、包覆三款、配重三款，以及双棱尖头锤、陨星熔核、无配重均已落盘接入。最终数值以 [目录](../../../Content/ColdSteelData/warhammer-gunsmith.json) 及其四份通用库为准；[模块表](../../../Content/ColdSteelData/warhammer-modules.json) 保存装配路径与偏移。

- 双棱尖头锤：物理 +30%、攻速 +5%、攻击耗体 +15%、韧性伤害 −25%，物理防御穿透 15%。
- 陨星熔核：物理 +40%、攻速 −15%、攻击耗体 +25%、韧性伤害 +40%；熔岩发光，重击／冲刺冲击波半径 ×1.5。
- 无配重：攻速 +5%、普通耗体 −5%、重击蓄力速度 +10%，蓄满重击释放额外耗体 +10%。保留轻薄端盖，使用独立 `no_pommel` ID；不是恢复原厂配重。
- 力量符文为红色，物理伤害 +10%；共鸣为所有技能冷却 −15%。剑与锤引用同一符文目录，限定符文仍受兼容白名单约束。锤符文位于裸露柄部，按弧长及源图比例投射。

## 公共源码与接入前置

可独立分离的目录、枪匠求值、通用符文材质、模块装配、装备语义符文描述、魔法冷却计算和原创制作脚本直接发布到原路径。共享文件从 Git 基线重建本轮内容后暂存，未覆盖本机工作文件，也未夹带其他物品、货币、技能轮盘或场景工作。

完整本机的基础战锤战斗与共用档案协议还有未公开前置；不能把当前公共切片当作干净检出可运行的完整工程。以下保存本轮依赖这些前置的接入内容：

1. [hammer-modification-integration.patch](hammer-modification-integration.patch)：以记录的 Git 基线为参照，保留工具求值、改造详情、技能属性快照、冷却和模块挂接改动。部分新增分支引用完整战锤调度成员，需要先整合同版本基础战斗。不能只应用补丁后跳过前置声明。
2. [authority-receipts-and-audit.patch](authority-receipts-and-audit.patch)：基于具名本机 Before 快照，保留无配重权威扣费、普通攻击回执、旋风／升龙提交回执、传奇范围与原生审计源。这不是直接针对公共 HEAD 的统一补丁。
3. [combat-stat-bindings.cpp.inc](combat-stat-bindings.cpp.inc)：在完整战锤 `ApplyToolStats` 中替换蓄力时钟和冲击波半径赋值，保持既有动作与成员。其余模块挂接见第一份补丁。
4. [integration-baseline.json](integration-baseline.json)：记录每个文件的基线身份、LF 文本 SHA-256、候选与本机状态，以及缺少的前置。具名 Before 已归档，可按归档清单取回。本机完整代码已经应用全部修复，不要再次套补丁。

共用联机框架参考 [联机批次交接](../Multiplayer20261014/README.md)。恢复时统一整合 `ProductionToolComponent` 的声明、动作调度、权威实现，`WarhammerHeavyMotion`、`WarhammerShockwave`，以及 `ColdSteelProfileRecovery` 和武技冷却修订字段；不通过发布其他任务整个脏文件来补齐。

## 制作与资产恢复

| 内容 | 当前入口与保留依赖 |
|---|---|
| 六件原装模块 | `SourceAssets/SteelWarhammer20261014/ModulesV1`；依赖原战锤及已许可手臂源。AuthorHost 只公开原创源码和工程描述 |
| 普通锤头 | `CommonHammerHeads20261014/DesignBuildV2`；仍读取根目录 `author_heads.py`、`catalog.py`，导入还依赖初版钢材质 |
| 中央锤座 | `CommonHammerSeats20261014/BuildV1` |
| 三款包覆 | `CommonHammerGrips20261014/BuildV1`；最终网格为 UV1 包，先建立基础材质，再执行 `import_mesh_uv.py` |
| 三款配重／无配重 | `CommonHammerPommels20261014/BuildV1`、`BalanceV2`、`NoPommelV1`；端盖作者读取原装模块 Blend 和 BuildV1 钢材质 |
| 双棱尖头锤 | `CommonHammerSpecialHeads20261014/PointedHammer/ConceptV4`、`BuildV1`、`BalanceV2` |
| 陨星熔核 | `SteelWarhammerLegendaryHeads20261014/MeteorCore/BuildV1`、`BalanceV1`、`ShockwaveRangeV1` |
| 裸柄环绕符文 | `WarhammerCommonRunes20261014/ShaftWrapV2`；先恢复根目录符文材质供体，再复制并替换投射 |
| 统一图标／力量符文 | `WarhammerIconCorrection20261014`、`StrengthRune20261015`；遵守金属框、铆钉、内圈和灰白核心纹样标准 |

以上简写目录均位于 `SourceAssets`。作者脚本按本机布局编写；换机器先调整宿主、Blender、UE 及源资产路径。只在需要恢复时执行，不把各阶段安装器按名称无差别重跑。最终 JSON 已保存批准值，旧目录初始化器可能重置它们。恢复次序为合法原始源和供体 → 作者生成 → 基础材质／模块导入 → 最终网格／符文／图标 → 最终目录和数值 → 完整战斗源码构建。

模型、Blend／FBX、纹理、图标、音频、UE 包、密集几何输入和构建产物保留本机。本次只公开原创代码与配方，不授予任何第三方原资产再分发许可。缺少本地输入时，脚本公开不代表能够从零恢复同一模型；本地资产清单见 [local-assets.json](local-assets.json)。

## 归档与技能

86 个文件、11,097,260 字节（10.58 MiB）已移入 `trash/warhammer-mods-retired-20261015`，移动后逐项 SHA-256 一致，没有永久删除。范围为尖头锤未采用的 ConceptV1～V3、被最终值替换的两套旧平衡方案及本轮 Before 快照。原路径、目标、原因和保留替代物见 [archive-manifest.json](archive-manifest.json)。历史文档中的旧路径按此清单追溯，最终母版和活动供体保留。

个人技能维护源与仓库对应章节均更新：[近战模块化](../../../skills/ue5-weapon-workflow/references/modular-melee.md)、[符文表面](../../../skills/ue5-weapon-workflow/references/rune-surfaces.md)、[装备符文与攻击回执](../../../skills/ue5-save-load-replication/references/equipment-runes-and-attack-receipts.md)。

## 既有证据与未完成验收

此前用户授权的回查已修复三类遗漏：工具执行器漏算战锤被动、远端缺失符文 MID／叠层语义、客机缺少已提交耗体和武技冷却回执。

完整本机 47 项目录检查、103 项原生隔离回归通过，0 失败，Game／Editor 构建成功；此前力量符文另有 32 项源码和 58 项资产检查。证据摘要见 [validation-evidence.json](validation-evidence.json)，完整本机记录见 [回查说明](../../../SourceAssets/WarhammerIntegrationAudit20261015/README.md)。这些是完整本机的历史结果，不是公共源码切片重新构建的结果。

本次只做归档、脚本语法、链接、暂存范围和推送检查，没有重跑游戏测试。真实主机／客机传输、延迟／丢包、断线重连及最终画面仍待用户实机测试；隔离调用权威函数与结构序列化不等于双端验收。
