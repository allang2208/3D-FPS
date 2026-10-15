# 陨星熔核数值 V1

> 2026-10-15 整理：本文为制作阶段记录；Before 快照已带散列移入 trash。最终发布状态和恢复入口见[整理说明](../../../../Docs/Publication/WarhammerMods20261015/README.md)。

2026-10-15，按用户“设置数值属性”的要求配置重型传说锤头初版。定位为较高单次物理伤害和韧性伤害，代价是攻速与体力。

| 属性 | 改造值 | 字段倍率 |
| --- | --- | --- |
| 物理伤害 | +40% | `physical_damage_mult = 1.40` |
| 攻击速度 | −15% | `attack_speed_mult = 0.85` |
| 攻击体力消耗 | +25% | `stamina_mult = 1.25` |
| 韧性伤害 | +40% | `toughness_damage_mult = 1.40` |

已同步 `../BuildV1/catalog.py` 与 `Content/ColdSteelData/warhammer-gunsmith.json` 中锤头槽的 `meteor_core` 数值和直接属性文案。保持锻钢战锤专属传说身份，沿用现有四项倍率的计算与展示。外观说明不重复数值；熔岩发光继续作为已制作的材质效果。本轮记录四项直接属性，后续新增的重击／冲刺冲击波范围 +50% 见 [ShockwaveRangeV1](../ShockwaveRangeV1/README.md)。

`apply_balance.py` 只发布本选项数值和属性说明，执行记录为 `balance_receipt.json`。`Before/` 保留本轮修改前的作者目录及正式配置。此前 BuildV1 的导入、登记与交付回执记录的是首次建模时的中性数值，作为历史记录保留，当前数值以本目录和正式配置为准。

本次无需模型或图标重导，无需原生构建。现有武器目录加载时读取这些值，已运行的游戏实例需重新加载目录。未执行游戏测试，平衡性与表现由用户测试。
