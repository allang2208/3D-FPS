# 枪械默认不造成怪物硬直（2026-09-17）

用户要求：无特殊说明时，枪械命中怪物不产生硬直；毒、流血（以及同类状态跳伤）同样不产生硬直。

## 规则

| 伤害来源 | 硬直 | 说明 |
| --- | --- | --- |
| 枪械（步枪/手枪/双持，走 `ColdSteelSkills::ApplyHit`） | **默认不硬直** | 只有目录显式声明才关闭这道闸门 |
| 近战武器（剑/斧等，`ApplyHitWithReactionScale`） | 保留 | 挥砍反应倍率、弹反倒放、击退逻辑不变 |
| 技能（火球/冰锥等自带伤害类型） | 保留 | 各自的命中与范围反馈不变 |
| 状态/持续伤害跳伤（毒 / 流血 / 灼烧） | **不硬直** | 在跳伤源头把反应倍率压到 0，伤害类型不变 |

## 实现

- 目录开关：`Content/ColdSteelData/gunsmith.json` 的武器条目可选 `"hit_stagger": true`，缺省 `false`。载入在 `UGunsmithSystem::Initialize`（`FGunsmithWeapon::bHitStagger`）。
- 采集：`FColdSteelSkillShot` 新增 `ItemDefinition`，由 `ColdSteelSkills::Snapshot` 在开火瞬间记录（双持按各自手部物品；未显式传物品时回落到当前装备）。飞行弹丸沿用开火时的快照，换枪不会改变已出膛子弹的行为。
- 施加：`UColdSteelStatusModel::ApplySkillWeaponHit` 在伤害前查询该枪的开关；关闭时用 `UMonsterCombatComponent::ApplyHitWithReactionScale(0.f, …)` 包住 `ApplyPointDamage`。
- 受击端：`UMonsterCombatComponent::ReceiveHit` 在闸门关闭时**只记住攻击者**（AI 仇恨照常），随后直接返回——不累加韧性、不触发眩晕、不切硬直状态、不停止移动、不播放受击表现。此前 0 倍率仍会以 0.01 s 进入 Stagger 状态并重播受击片段，属于需要一并修掉的细节。
- 状态跳伤：`UCombatStatusFormula::Apply`（流血与灼烧共用）与 `UColdSteelPoisonComponent::Pulse`（中毒）在结算外包一层 `ApplyHitWithReactionScale(0.f, …)`。**伤害类型保持原样**（流血/毒 `UCombatDirectDamage`、灼烧 `UFireballDamage`），以免改变 `IsMagic` 判定带来的减伤与增伤差异；目标不是怪物（没有该组件）时按原样调用。

## 影响

- 步枪连射不再反复打断怪物攻击/移动，怪物行为树表现更稳定；玩家不再能靠点射把怪物"钉住"。
- 韧性（`Poise`）与眩晕阈值现在只由近战与技能累积；枪械伤害不参与，因此同一韧性的眩晕触发频率相对降低。
- 硬直表现相关的怪物代码（`InterruptAttack` / `BeginReaction` / 专用 Stagger 片段 / 弹反倒放）保持原样，仅由闸门决定是否进入。

## 状态

`GunsmithSystem`、`ColdSteelSkillTypes.h`、`ColdSteelSkillRules`、`ColdSteelSkillModel`、`MonsterCombatComponent` 编译通过，`Tools/Build/Build-Editor.ps1` 返回 `Result: Succeeded`。按用户规则未启动游戏、未截图；实机需确认连射时怪物不再硬直、近战与技能仍能打断、以及再次进入战斗后 AI 行为正常。

## 待定（未实施）

- 新增的状态跳伤必须走同一条闸门（在跳伤源头套 `ApplyHitWithReactionScale(0.f, …)`），否则会重新出现"每秒打断怪物"的问题。
- 反过来，如果想让某把枪（例如未来的霰弹枪或大口径）保留硬直，只需在其目录条目加 `"hit_stagger": true`。
