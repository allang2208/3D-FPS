---
name: ue5-pcg-building
description: UE5.6-UE5.8 建筑与场景地编。适用于从场景设计图、组件三视图和模型到关卡搭建，也用于模块化建筑、灰盒、PCG 与 Shape Grammar 排布、按地块与种子生成、密度过滤，以及流式高度场地表材质。
---

## 执行约定

遵守用户全局规则：后台制作、不主动测试、不跨对话协调。涉及 UE 构建或资产操作时，按需读取[后台开发与接入规则](../ue5-auto-assistant/references/editor-open-development.md)；已读则复用。 原因：制作授权不包含额外运行或验收，交付应保留未测试的实际状态。

## FPSGAME 性能开发约束（2026-09-23）

扩展地牢、灯光或高密度模块时，读取 [性能开发约束](../ue5-performance-packaging/references/fpsgame-performance-development.md) 的灯光与几何部分。固定起始区与新增房间都接入灯光调度；模型资产和后续导入脚本同步保留 Nanite／LOD、材质用途与碰撞策略。 原因：渲染宿主需要对应材质编译变体，缺少用途标记会回落到默认材质。

# Quick Start

- 新建筑、地标或成组布景，按 [从设计图到关卡搭建](references/scene-development-standard.md#从设计图到关卡搭建) 执行。沿用已有设计和资产，从本次要制作的阶段接续。 原因：「从设计图到关卡搭建」记录该任务的专属入口和边界，按主题引用可避免另写一套相互冲突的步骤。

- 大厅门框漏空/闪动、告示牌、关闭出怪设施基础、双主题路线和门外街景，读取 [设施收口与静态布景](references/facility-reveals-and-static-fixtures.md)。区分活跃母版与废案、场景模型与刷怪玩法。

- 固定主题组合、错层坡道、路线预算及清房后开闸，读取 [主题路线与房间闸门](references/themed-routes-and-room-gates.md)。

- 新场景/房间开发、统一栏杆翻越、控制台直达预览及用户确认后的样板清理，先读 [场景开发标准流程](references/scene-development-standard.md)。默认不新增祭坛出征入口；正式接入收尾包含样板退役。 原因：移动状态需要真实支撑和碰撞条件，达到缓存坐标并不等于动作已经安全完成。

- 地牢墙面扫描、颗粒/视差、霉斑与渗水贴花，以及已认可样板向整站扩展、重复破损与固定机位对比，读取 [地牢表面制作](references/dungeon-surface-authoring.md)，先确定实际材质入口与污渍层，再调整密度和表现。

- 扩展已认可样板、随机房间池、门洞拼接、岔路和 Boss 终点时，读取 [保留设计语义的随机地牢](references/authored-dungeon-generation.md)。

- 特殊战斗房入池、玻璃门窗、随机家具/血迹/海报和临时测试退役，读取 [特殊地牢房间与室内接入](references/special-dungeon-interiors.md)。

- 工作台、维修墙、货架等含许多小件的室内布景，读取 [可复用室内组合件](references/reusable-interior-assemblies.md)：以配置和锚点维护组合件，受约束随机摆放，按依赖局部重建。

- For decorative fountain overflow, natural water variation and seamless spatial water loops, read [fountain water and audio](references/fountain-water-audio.md).
- For the accepted white-marble pavilion dome, real constellation inlays and finial authoring, read [pavilion roof decoration](references/pavilion-roof-decoration.md).

## 统一模型生成入口（2026-09-13）

制作建筑模块本体、建材和装饰网格时，先用 [通用模型生成工作流](../asset-model-workflow/SKILL.md)。生成外观后按明确尺寸、枢轴、拼接面和碰撞制作模块，再接续本文 PCG 排布；PCG 本身不是图生模型。默认不主动测试或验收。

- For the runtime heightfield **ground material** (layered families, height blending, parallax
  relief, vertex-colour contract, offline HLSL validation) read
  [ground surface material](references/ground-surface-material.md). The hills world has no
  Landscape actor, so none of the Landscape nodes apply there.
## PCG 排布与生命周期

- 明确生成对象、输入地块/样条/点、标签、样式、种子以及静态或运行时生成方式。原因：输入边界和随机来源决定同一配置能否重建同一布局。
- 复用现有图和模块，只添加所需的输入、过滤、变换、文法和输出节点；删除“每阶段至少两个核心节点”的要求。原因：节点数量不能衡量图是否完整，强制凑数会复制已有计算。
- 排布保持模块尺寸、局部轴、枢轴、可占用区域及连接面的约定。原因：合法的点集仍可能因模块朝向或拼接尺寸错误而出现重叠与断缝。
- 高频静态部件优先沿用实例化输出，独立交互或持久状态部件保留 Actor。原因：给每个装饰小件创建 Actor 会增加对象及更新成本，而合并交互对象会丢失其独立身份。
- 运行时生成沿用实际启用的触发、半径、调度与清理设置；只在任务需要时改这些字段。原因：一律强制覆盖调度类和半径会改变现有世界的生成时机及范围。
- 局部参数或边界变化只刷新受影响范围，清理时保留其他区域和未归属对象。原因：全局重生成会扩大一次局部修改的资源成本与可见变化。
- 随机分支使用既有种子和稳定输入顺序；持久对象继续沿用存档与权威入口。原因：同一个 seed 不能抵消不稳定排序，重新生成也不能重复创建已保存的交互实体。
- API 名称、文法字段和刷新入口以工程当前 PCG 插件头文件为准。原因：不同引擎版本的调度对象及废弃接口不同，旧版本对照表不能作为当前签名保证。
- 默认完成制作、保存和必要构建；节点探针、重放、导航、重叠与性能检查仅按用户明确要求执行。原因：制作图所需的输入资料不等于授权运行一套生成验收。

定位线索：`UPCGComponent` 的生成设置、`UPCGSubsystem` 的调度/清理入口、`UPCGStaticMeshSpawnerSettings` 和 `UPCGSpawnActorSettings` 的输出差异，以及工程实际采用的文法参数。原因：这些职责直接对应生成触发、范围和对象生命周期，定位时无需遍历无关引擎模块。

## Vibe3D 模块本体制作（2026-09-19）

楼梯、梁柱、栏杆、管件等明确尺寸的规则模块，优先考虑 [Vibe3D 制作分支](../asset-model-workflow/references/vibe3d-workflow.md) 在 UE 内直接制作；参考与尺寸充分时无需先跑图生模型。生成资产或已有资产可按需做局部几何、UV、碰撞和 LOD。保持本项目尺寸、枢轴、拼接面与建筑放置合同，完成模块后再由 PCG 排布。Vibe3D 是编辑器制作工具，不替代运行时地貌破坏或 20 cm 玩家建造系统；不自动执行本技能或插件文档中的测试与预览。 原因：制作授权不包含额外运行或验收，交付应保留未测试的实际状态。

## 已生成构件的批量优化

制作局部 Nanite/ISM 分组及后台关卡保存时，读取 [静态构件实例化](references/static-mesh-instance-production.md)，保留碰撞、变换及独立玩法对象语义。 原因：合并静态显示可减少对象成本，但交互、碰撞和独立身份仍需保留所属语义。

## 冶炼点击存档（2026-09-24）

熔炉的开始、加燃料、收取、升级、拆除与档案意图、立即刷盘和读档对账，读取 [冶炼点击意图](references/smelting-click-intents.md)。连续挖掘仍用约 2 秒合并存档。

## 场景光源与最低照明

制作或调整室内灯具、吊灯方向、廊下和暗角照明时，读取 [灯具与照明层次标准](references/fixture-lighting-standard.md)。向下灯不得向上直射天花板；保留已认可主灯，按实际楼层补光。 原因：用户认可的是具体母版和观感，换成另一版本会改变已有接触或外观基线。

## 固定观景点的城市远景与栏杆

公寓海湾建筑分层、办公条形窗灯、动态广告/水面反射、侧挡板替换玻璃栏杆及增量重建，读取 [远景与栏杆制作](references/layered-harbor-and-balcony.md)。保留当前天气和共享资产，版本编号不作为退役依据。

## 城市街区与室内接触

围绕公寓生成街道、楼群、沿岸绿化，修复道路衔接、停车穿插及实例成本时，读取 [城市分区制作](references/city-district-production.md)。灯具厚度、厨房接触和自然电线走线读 [公寓接触与线材](references/apartment-contact-and-cables.md)。

## 流送场景入口与多人室内适应

换图后碰撞晚到、按控制器安全重试和逐视图室内亮度，读取 [安全出生与室内视图](references/streamed-entry-and-interior-view.md)。

## 丘陵雨林植被与水坑

修改雨林专属草、联机生态参数或扩大水坑选址时，读 [雨林植被与局部积水](references/hills-vegetation-and-pools.md)。 原因：「雨林植被与局部积水」记录该任务的专属入口和边界，按主题引用可避免另写一套相互冲突的步骤。

丘陵道路保护、河湖高度连续、树簇与林床关联、扫描岩壁补面，读取 [丘陵道路保护、河湖高度连续、树簇与林床关联、扫描岩壁补面](references/hills-scenery-continuity.md)。
