# 枪械射速与敏捷攻速解耦（2026-09-17）

用户要求取消"敏捷对攻速的加成"：装备浮窗里 AKM 的攻击间隔显示 70 ms，而目录基础是 100 ms，差值全部来自角色技能属性攻速倍率。

## 改动

| 位置 | 原 | 现 |
| --- | --- | --- |
| `ColdSteelWeaponStats::Interval` | `Base / max(1, 攻速倍率)` | **`Base`**（只保留附魔倍率与弓术冷却项） |
| `M4GunsmithOverview` 射击间隔 / 射速两行 | 除以 / 乘以角色攻速 | 直接取目录值 |
| `M4GunsmithSelectedDetails` 射击间隔行 | 除以角色攻速 | 直接取目录值 |
| 角色面板「攻速倍率」说明 | "实际射击间隔 = 基础间隔 / 倍率" | "只看近战攻击速度；枪械射击间隔取武器基础值" |
| `Docs/UI/ui-cold-steel-design-system.md` | "间隔包含攻速与附魔倍率" | "间隔取目录基础值，自 2026-09-17 起不再除以攻速" |

**未改动**：近战攻击速度仍按 `攻速倍率 = 1 + 敏捷×0.02`（`MeleeWeaponStats`）；附魔的攻击间隔倍率（目前仅双手剑「沉重」×1.35）与弓术冷却仍在 `Interval` 内生效；弹道、后坐力、伤害、换弹公式不变。

现在四处显示与实战同源且等于目录值：枪匠总览、配件详情、物品提示、角色面板与 `AFPSGAMECharacter::FireInterval`。AKM = 100 ms（600 发/分）、M4 = 80 ms（750 发/分）、QBZ-191 = 90 ms（667 发/分）；M1911 = 180 ms、715 = 320 ms。

## 影响量级（供平衡判断）

旧模型下攻速倍率直接乘进枪械射速，等于一个隐藏的巨型乘区：

| 敏捷 | 攻速倍率 | 100 ms 基础→实际 | 射速变化 |
| --- | --- | --- | --- |
| 10 | 1.20 | 83 ms | +20% |
| 20 | 1.40 | 71 ms | +40% |
| 40 | 1.80 | 56 ms | +80% |

解耦后高敏捷枪械流损失同样比例的 DPS（敏捷 20 约 −29%，敏捷 40 约 −44%）。

## 敏捷补偿（用户确认的第 1、2 项，已实施）

### 换弹速度 +0.3%/点，乘法叠加

```
最终换弹时间 = 基础耗时 ÷ ( 敏捷倍率 × 快手倍率 × 附魔倍率 × 改造倍率 )
敏捷倍率 = 1 + (基础敏捷 + 装备敏捷) × 0.003
快手倍率 = 1 + 巧手等级 × 0.01            （UColdSteelStatusModel::ReloadSpeedMultiplier）
附魔 / 改造 = Enhancement::Effect / CraftEffect("reloadSpeedPercent", 1)
```

- 实现位置：`ColdSteelWeaponStats::Reload(Item, Model, Base)`；调用方覆盖角色档案 `ApplyColdSteelProfile`、物品提示（`ColdSteelItemTooltipData` 两处）、概要提示（`ColdSteelItemTooltipSummary`）、枪匠总览与配件详情、双持手枪装载（`PistolDualWieldComponent::LoadHand`）。双持的 ×1.33 惩罚在之后另行相乘，同样是乘法关系。
- 各来源彼此独立、不相加：敏捷 1.06 × 快手 Lv10 1.10 × 附魔 1.10 ≈ 1.28 → 3.68 s 换弹变 2.87 s。
- 参考数值：敏捷 20 → 换弹 +6%；敏捷 40 → 换弹 +12%。
- 显示：物品提示与枪匠面板现在都给出**最终**换弹时间（面板此前只显示枪械/配件值），配件详情的百分比仍只表示该配件自身的边际影响。

### 体力恢复 0.01/点 → 0.015/点

`CoreCombatFormula::Player` 的 `StaminaRegen = 1 + 敏捷×0.015`（敏捷 20 从 ×1.20 → ×1.30，敏捷 40 → ×1.60）；角色面板的敏捷卡、体力恢复行与敏捷详情三处说明同步。

### 保留未做

物攻 +0.11/点、移速 0.15/点，以及"小额上限射速（+0.5%/点、上限 +8%）"方案均未实施。

## 状态

`WeaponStatEvaluation`（h/cpp）、`FPSGAMECharacterProfile`、`ColdSteelItemTooltipData`、`ColdSteelItemTooltipSummary`、`M4GunsmithOverview`、`M4GunsmithSelectedDetails`、`PistolDualWieldComponent`、`ColdSteelCharacterSheet`、`CoreCombatFormula.h` 全部编译通过，`Result: Succeeded`（日志 `Saved/BuildEditor/build-dex-reload-compile2.log`），DLL 已更新。按用户规则未启动游戏、未截图，实机射速/换弹数值与面板一致性由用户确认。
