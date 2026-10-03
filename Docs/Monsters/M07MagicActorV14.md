# M-07 V14 三元素释放执行组件

生产入口为 `Source/FPSGAME/Monsters/M07MagicAttack.h/.cpp`。本组件从当前掌心位置接收释放参数，不选择 AI 目标，不扣玩家资源，不提交玩家施法修炼；积蓄、释放动画和冷却由 M-07 怪物状态负责。

## 根组件调用接口

```cpp
// 首选延迟生成，使初始化快照在 BeginPlay 前就绪。
const FTransform ReleaseTransform(AimDirection.Rotation(), PalmPosition);
auto* Spell = GetWorld()->SpawnActorDeferred<AM07MagicAttack>(
    AM07MagicAttack::StaticClass(), ReleaseTransform, this, this,
    ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
if (Spell)
{
    Spell->Initialize(this, AimPoint, Element, Damage, RangeCm, SpeedCmS, RadiusCm);
    Spell->FinishSpawning(ReleaseTransform);
}
```

也支持 `SpawnActor` 后立即 `Initialize`。初始化只接受一次，真正起动在快照已就绪且 `BeginPlay` 已发生之后执行。每次怪物只在释放接触点生成一次。

积蓄组件使用 `AM07MagicAttack::ChargeSystem(Element)` 取已被 CDO 保留的资产，再用 `AM07MagicAttack::ConfigureCharge(FX, Element, Fraction)` 设置对应 Niagara 的输入契约。火球返回慢燃核心，冰柱返回冰晶，闪电返回雷枪既有掌心积蓄系统。闪电积蓄没有误用需要样条输入的释放电弧。

## 默认执行参数

| 元素 | 初始魔攻 | 释放伤害 | 射程 | 飞行速度 | 范围 |
| --- | ---: | ---: | ---: | ---: | --- |
| 火球 | 40 | 64 | 1400 cm | 1500 cm/s | 140 cm 爆炸半径 |
| 冰柱 | 40 | 56 | 1500 cm | 2000 cm/s | 24 cm 单次直击扫掠半径 |
| 闪电 | 40 | 60 | 1200 cm | 瞬时 | 单次遮挡射线 |

参数由怪物传入，执行 Actor 不反复从玩家面板取数。火球、冰柱朝释放瞬间传入的瞄准点直线发射，不在途中追踪玩家；闪电从同一个掌心位置检查第一个有效遮挡与玩家胶囊。

## 实际表现依赖

- 火球：`/Game/Skills/Fireball/NS_FireballSlowBurnCore`、`NS_FireballVelocityTrail`；爆炸、热浪和音效使用 `ImpactRealistic20260914` 的玩家正式资产。热浪沿用 `AFireballShockwave`。
- 冰柱：`/Game/Skills/IceSpike/FrostV2/SM_IceSpike_01`、`M_IceShell`、`M_IceHeart`、`NS_FrostCrystals`、`NS_ColdMist`。将玩家冰锥沿飞行轴放大 1.55 倍，保留双层材质，以网格真实 bounds 中心对齐扫掠体。命中沿用 `P_IceSpikeImpact`、`SM_IceShard`、`S_IceImpact` 和既有 `AFPSIceSpikeFragments`；无接触地飞完射程则静默消失。
- 闪电：`/Game/Skills/Lightning/NS_LightningChain` 和 `AFPSLightningArc`，保持样条 DI 的宿主关系；0.24 秒保持、0.17 秒淡出、10 段固定折线。掌心积蓄用 `/Game/Skills/ElectricMagic/NS_ThunderCharge`，命中用 `NS_ElectricImpact`，释放音效用 `S_LightningCast1`。

没有修改玩家现有 Niagara、材质、技能参数或完整源模型。资源由一次构造的硬引用保留，不在攻击 Tick 或每次释放中执行同步加载。飞行特效没有阴影网格；仅激活当前元素的组件。寒雾每 0.1 秒接入已有流体细节/风预算，DedicatedServer 不启用表现和命中特效。

## 伤害与生命周期

- 只伤害带存活玩家血量组件的玩家 Pawn；`Friendly` 或 `Summoned` 施法者不伤玩家，其他怪物与场景对象只承担遮挡。
- 实际项目玩家胶囊忽略 Visibility，因此按对象类型取得扫掠接触，再筛选玩家根胶囊或对 Visibility 阻挡的真实场景组件；重叠触发器/雾体不会截掉弹体。没有仅用 Visibility 射线而漏掉玩家。
- 使用 `UFireballDamage`、`UIceSpikeDamage`、`ULightningDamage`，保留 `CombatFormulaRuntime::IsMagic`、玩家魔防与现有状态/格挡链。以 `ApplyPointDamage` 标明远程命中，使现有闪避远程攻击判定适用；没有绕过防御的 DirectDamage 类型，没有新增逐帧伤害。
- 同一次事件对同一个玩家最多结算一份伤害；火球直击后加入去重集合，再按玩家控制器做一次爆炸范围和遮挡过滤，避免直击叠两份爆炸伤害。冰柱仅第一个碰撞结算；闪电仅释放瞬间结算一次，不连锁，也不持续扣血。
- 采用现有怪物毒液弹体惯例：施法者死亡、销毁、离开世界会取消尚未命中的已释放弹体。死亡不撤回已经命中/结算的伤害，已提交的短命中表现自然结束。没有玩家资源退款和修炼副作用。
- 伤害/飞行在 authority 执行；释放快照、弹体位移与命中表现状态复制给客户端。客户端只演表现，不自行结算伤害。

三元素执行器制作后已由主制作流程完成最终 Editor／Game 构建，M-07 的四段战斗动作、魔攻与技能倍率以及现有 AI/F6 蓝图已实际导入保存。实际保存回执为 `SourceAssets/BlindSupplicantM07Meshy20261001/CombatMagicV14/ue_combat_magic_delivery_v14.json`，完整制作记录见 `BlindSupplicantM07CombatMagicV14.md`。没有启动 UE 图形编辑器、PIE 或游戏，没有截图、渲染或测试；运行表现交由用户测试。
