# 配重改造接入核对表（2026-09-15，只读核对）

本表由只读检查生成：逐项比对改造选项、模块目录、运行资产、图标与代码挂点，不修改任何共享文件，也不代表游戏运行验收。相关实现由模块化会话完成，本文只做交叉核对与测试清单。

## 一、选项 → 数值 → 模型 → 图标

| 选项 id | 名称 | 数值（melee-gunsmith.json） | 运行模型（frost-sword-modules.json） | 图标 |
| --- | --- | --- | --- | --- |
| `ballast_hardened` | 硬化配重 | `heavy_damage_add 0.15`、`knockback_mult 1.1`、`attack_speed_mult 0.9`、`stamina_mult 1.1` | `Pommels5080_20260915/ballast_hardened/SM_FrostPommel_ballast_hardened` | `ue_frost_crystal_sword_pommel_ballast_hardened` |
| `ballast_rune` | 符文配重 | `magic_cooldown_mult 0.85`、`magic_cost_mult 0.85` | `…/ballast_rune/SM_FrostPommel_ballast_rune` | `…_pommel_ballast_rune` |
| `ballast_magic_orb` | 魔力球配重 | `magic_damage_mult 1.1`、`magic_cost_mult 1.15` | `…/ballast_magic_orb/SM_FrostPommel_ballast_magic_orb` | `…_pommel_ballast_magic_orb` |

三款的安装位一致：`location_cm = [0, 0, -22.7]`，接口 `frost_hilt_v1`。原装为 `Modules20260915/SM_FrostSword_Pommel_factory`。

核对结果：

- 三项 id 在改造目录与模块目录中完全一致，无拼写差异。
- 四个模型资产在盘上均存在（原装 + 三款）。
- 三个图标 PNG/资产存在于 `Content/ColdSteelData/AttachmentIcons20260913/`，命名符合 `M4GunsmithLayout` 的目录约定（`<definition>_<slot>_<id>`）。

## 二、代码挂点

| 环节 | 位置 |
| --- | --- |
| 解析改造数值 | `Weapons/MeleeGunsmith.cpp` 的 `magic_cost_mult` / `heavy_damage_mult` / `heavy_damage_add` / `knockback_mult` |
| 数值合并 | `Weapons/GunsmithSystem.cpp` 连乘 `MagicCost`、`Knockback`，累加 `HeavyDamageAdd`；`GunsmithSystem.h` 的 `HeavyMultiplier(Base)=Base*HeavyDamage+HeavyDamageAdd` |
| 重击应用 | `Weapons/RuneSwordComponent.cpp` 出招时 `HeavyMultiplier(ChargedMultiplier)` |
| 击退距离 | `Weapons/MeleeWeaponStats.cpp` 的 `KnockbackCM=基础值(寒晶剑20cm)*Modifiers.Knockback`；命中后 `RuneSwordComponent` 调用 `MonsterCombatComponent::ReceiveMeleeKnockback`，实现在 `Monsters/MonsterMeleeKnockback.cpp` |
| 魔法消耗 | `Skills/ColdSteelFireballModel.cpp`、`Skills/ColdSteelIceSpikeModel.cpp` 各自应用一次 |
| 模型组装 | `Weapons/ModularSwordVisual.cpp` 按 `gunsmith_parts.pommel` 查表换子组件；未登记项回退 `factory` |
| 提示显示 | `UI/ColdSteelItemTooltipData.cpp`（重击倍率、重击加值、击退百分比、魔法值消耗）、`UI/ColdSteelItemTooltipSummary.cpp`（重击倍率、击退距离 cm、魔法值消耗倍率） |

一致性检查：`MagicCost` 在火球与冰锥各仅应用一次；`HeavyDamage` 仅经 `HeavyMultiplier` 应用一次；命中反应倍率只乘 `HitReaction`，击退走独立距离通道。未发现重复计算。

## 三、建议的测试清单（未执行，由用户执行）

1. 改造台：配重锤栏目切换三款，中央预览是否换件、确认应用与撤销是否正常、原装能否恢复。
2. 持剑与检视：柄尾是否为所选件，接缝与材质是否连续；魔力球重点看半透明表现。
3. 数值面板：重击倍率应由 2.50 变为 2.65；击退距离显示 22 cm；魔法值消耗显示 0.85×／1.15×。
4. 实际战斗：普通命中是否产生位移击退、碰撞阻挡是否停止推退、施法消耗与冷却是否按倍率变化。
5. 掉落物与图标：丢在地上、背包与仓库图标是否随选择变化。
6. 存档：切换后保存、退出、重进是否保持所选配重。

## 四、未核对与边界

- 本文全部为静态只读核对：没有启动游戏、PIE、截图或渲染，未验证实际显示与战斗表现。
- 握把与剑身Ⅰ目前只有数值，模型仍回退 `factory`；符文剑未纳入模块化。
- 旧 `SourceAssets/WeaponBallast20260915` 的候选模型不参与运行。
