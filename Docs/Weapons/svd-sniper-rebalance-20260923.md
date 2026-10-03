# SVD 狙击化重调（2026-09-23）

用户指定：类别狙击枪、自带暴击伤害倍率 +0.5、伤害参照 715 再高 25%、有效射程 300 m、
基础腰射扩散调到现值 3 倍、准星同步。数据脚本 `Saved/svd_sniper_rebalance_20260923.py`。

## 数值

| 项 | 旧 | 新 | 依据 |
| --- | --- | --- | --- |
| `base.damage` | 65 | **85** | 715 的 68 × 1.25 |
| 攻击力公式（`combat-weapon-formulas.json`） | 15 + 0.48×(智力+精神)，enhanceFlat 1.05 | **32.5 + 1.00×智力 + 2.00×精神** | 量级照 715 全项 ×1.25（26/0.8/1.6→32.5/1.0/2.0，enhanceFlat 归 0 同 715）；2026-09-23 用户改口径：变量只留智力与精神，剔除敏捷 |
| 强化后公式 | — | 智力项 (1.00+0.125L)、精神项 (2.00+0.1875L) | 715 perEnhance 0.1/0.15 ×1.25 |
| `critDamageBonus`（items 新字段） | 无 | **0.5** | 结算点 `ColdSteelSkills::Snapshot`：与暴击技能倍率相加，`ColdSteelSkillModel` 命中处只乘一次（要害或随机暴击不叠乘） |
| `base.effective_range` | 150 | **300 m** | 距离衰减锚点同步（`WeaponDamageFalloff::Multiplier` 按 EffectiveRangeCM） |
| `base.spread_mult` | 1.6 | **4.8** | 现值 ×3 |
| 类别 | 无标签（浮窗显示 rifle） | `weaponTypeTag` **狙击步枪** | 机械 `weaponType` 保持 `rifle`：代码只认 rifle/pistol/machineGun/staff/sword/shield，改值会丢步枪精通的要害倍率与专精修炼挂接 |

## 显示与文案

- 浮窗「枪械参数」新增行「暴击伤害加成 +50%」（仅当 items 定义含该字段，读端
  `ColdSteelItemTooltipData.cpp`）。
- `traits` 重写 5 条（含"自带暴击伤害倍率 +50%，与暴击技能加成相加后单次结算"与
  "基础腰射散布明显偏大"代价行），数字全部回新 `base`；`desc` 重写 ≤200 字。
- `items.json` 静态 物理攻击 65→85（checker 断言 = base.damage）。

## 准星同步

无需也无法手调：`GetCrosshairHalfExtent()` 把 `GetHipSpread()`（含 spread_mult 与配件
hip_spread_mult 连乘）在 10 m 处投影到屏幕像素，无绝对钳制；`BallisticPresentationAudit`
已有"tracks full spread without clamp"断言。散布 ×3 → 准星张角自动 ×3。

## 状态

- `check_attachment_consistency.py` **PASS**（含第 6 组 traits/items 数字断言）。
- C++（Snapshot 暴伤项 + 浮窗行）**未编译**：编辑器占用，`Build-Editor.ps1` 拒绝
  （"Save your work and close the FPSGAME editor before building"），待构建窗口。
- 已知限制：`items.json` 是实例快照——旧存档里已持有的 SVD 不带 `critDamageBonus`/
  类别标签与 desc 更新，重新拾取/新获得即生效；若要旧实例自动刷新需扩展
  `ColdSteelProfileRuntime` 同步（参照 weaponType 同步的写法），未授权前不做。
- 角色面板「暴击倍率」行仍只显示技能部分（1+50%+5%×L）；武器自带 +50% 在武器浮窗与
  traits 呈现，实际命中为相加后单次乘算。

## 追加：公式整体 ×1.5（2026-09-25，用户指定）

用户要求把 SVD 的攻击公式与强化后公式调为现值 1.5 倍。只改
`Content/ColdSteelData/combat-weapon-formulas.json` 的 `ue_svd` 五个系数：

| 项 | 改前 | 改后 |
| --- | --- | --- |
| `base` | 32.5 | **48.75** |
| `enhanceFlat` | 0 | 0（×1.5 仍为 0） |
| 智力项 | 1.00 + 0.125L | **1.50 + 0.1875L** |
| 精神项 | 2.00 + 0.1875L | **3.00 + 0.28125L** |

公式 `round(base + L×enhanceFlat + Σ 属性×(系数 + L×强化系数))` 对全部系数线性，
所以取整前在**任意强化等级**上都精确 ×1.5；下表倍率列的 1.487–1.508 是既有最终取整造成，不是缩放误差。

| 智力/精神/强化 L | 改前公式值 | 改后 | 倍率 |
| --- | --- | --- | --- |
| 15 / 15 / 0 | 78 | 116 | 1.487 |
| 15 / 15 / 5 | 101 | 151 | 1.495 |
| 15 / 15 / 15 | 148 | 222 | 1.500 |
| 25 / 25 / 15 | 225 | 337 | 1.498 |

这是公式值，不是实测伤害：还要连乘配件比例、加角色物攻、计弹药倍率、要害与距离衰减。

### 为什么不动 `base.damage` 85 与 items 静态 85

`ColdSteelEnhancementSystem::ProcessedDamage`（`:91-94`）先算公式，再乘
`Base / W->Base.Damage`，其中 `Base = Calculate()` 从 `W->Base` 起连乘配件倍率，
`W->Base.Damage` 即 `gunsmith.json` 的 85 —— 85 在分子分母同时出现并**精确抵消**，
这一项只负责把公式值按当前配件比例缩放。所以：

- 只改公式 = 干净 1.5 倍，与配件、强化等级无关。
- 把 85 也乘 1.5 数学上无效（抵消），却会破坏 `check_attachment_consistency.py`
  第 6 组「items 静态物理攻击 == base.damage」断言。
- 实弹路径确认走公式：`FPSGAMECharacterProfile.cpp:128` 先写 `Stats.Damage+atk`，
  `:137` 又把 `atk` 减回去作为 `Base` 送进 `ColdSteelWeaponStats::Damage`。

本节口径与本文上方 09-23 重调一致：改 SVD 伤害只改公式文件，两个 85 占位保持不动。

### 状态

- 未运行 `check_attachment_consistency.py`，未进游戏实测（按用户默认不主动验收规则）。
- 纯 JSON 改动，无需编译；子系统在 `Initialize` 读盘，重启游戏即生效。
