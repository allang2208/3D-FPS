# 火球直击要害与投射物魔法规则（2026-09-15）

用户要求：为有指向的投射物魔法添加命中要害触发暴击，并纳入未来魔法开发工作流。

## 当前行为

| 命中情形 | 暴击方式 |
| --- | --- |
| 火球实际直击头部要害 | 必定暴击，目标抗暴不抵消要害触发。 |
| 普通部位直击 | 自身暴击率扣除目标抗暴后随机判定。 |
| 爆炸波及其他目标 | 每个目标独立随机，不继承直击目标的要害结果。 |
| 撞墙／射程终点空爆 | 无直击要害标记，按各受伤目标随机判定。 |

要害和随机触发共用现有暴击伤害加成；同一目标只结算一次伤害、一次暴击加成及对应修炼。直击仍无距离衰减，波及保持当前半径、距离衰减和遮挡规则。

## 实现入口

- `FPSFireballProjectile::Explode` 把真实移动碰撞的完整 `FHitResult` 传给模型，保留 Actor 和 BoneName。没有碰撞的空爆传空指针。
- `ApplyFireballExplosion` 从实际 Hit 获得直击目标及要害结果，共用 `ColdSteelSkills::IsCriticalHit`（骨骼名包含 head 或等于 cranium，忽略大小写）。当前怪物的 Visibility 查询由骨骼网格返回命中部位。
- 每个目标独立设置 `MagicHit.bWeakpoint = Target == DirectTarget && DirectWeakpoint`。承伤侧使用 `bWeakpoint || 随机判定`，只执行一次 `CriticalDamage`，并通过 `CriticalResult` 回传实际结果。
- 原火球命中／击杀事务继续统计暴击修炼，保持目标去重，不另补一发要害伤害。
- 火球配置说明、默认说明与火球／暴击详情同步描述新机制。没有新增持久化字段，继续使用已有技能等级和冷却存档。

## 后续开发标准

已同步个人目录与工程镜像的 `ue5-skill-magic-workflow/SKILL.md`，详细接入规则位于 `references/projectile-magic-critical.md`。后续此类投射物保留完整命中部位、按目标构造魔法上下文、统一返回实际暴击结果，并说明波及范围。

必要原生构建完成：`Result: Succeeded`，模块 `UnrealEditor-FPSGAME-9150501.dll`，日志 `Saved/Fireball-Weakpoint-Build-20260915.log`。重启编辑器后加载本次 C++ 与技能定义。

本轮按用户规则不运行测试、游戏、截图或渲染；实机命中部位、伤害和修炼由用户测试。
