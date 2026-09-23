# 武器浮窗内容审计（2026-09-23）

对每把枪/武器的物品浮窗（主卡、枪械/近战参数、合计改造数值、特殊性质 traits）做内容审计：
读端为 `ColdSteelItemTooltipData.cpp` + `ColdSteelItemTooltipSummary.cpp` +
`ColdSteelItemTooltipFormula.cpp`，数据源为 `items.json`、`gunsmith.json`、
`melee-gunsmith.json`、`ammo_types.json`、`combat-weapon-formulas.json`、`skills.json`
与武器 C++ 常量。所有修改为纯数据文案，`stats`/`base` 一个未动。

## 已修复（`Saved/tooltip_fixup_20260923.py`、`Saved/tooltip_fixup2_svd_20260923.py`）

1. **traits 槽位清单九枪有错** → 十枪重写为运行时实际槽集（`options`∪`allowed`∪common
   `barrel`），改用 UI 类别名：M1911 并无下挂槽、715 并无枪口槽、ASH-12 并无后握把槽；
   全部清单原先漏了弹匣/枪管，PKM 漏脚架；"下挂"改"前握把"（UI 类别名），补"扳机/装填装置"。
2. **SVD 缺 traits**（唯一没有「特殊性质」段的枪）→ 补 5 条，数字全部回 base：
   350 ms / 10 发 / 伤害 65 / 150 米 / 520 m/s / 开镜 260 ms（`ln20/ads_smooth`）。
3. **`items.json` M4 物理攻击 24 ≠ base.damage 30** → 改 30（面板对枪械跳过该行，属隐性漂移）。
4. **M16 trait"单发威力与后坐都偏低"**：34 伤高于 M4/QBZ，不成立 → 改"后坐偏低，30 发弹匣以点射消耗"
   （recoil 90 确为步枪最低）。

## 核对为正确（抽样全量）

- 十枪 traits 其余数字全部回目录：射击间隔（80/100/90/180/320/130/80·180/67/92 ms）、开镜
  （240/450/180 ms）、容量（30/7/20/100/10）、PKM 移速 −33% = `machineGunMastery.movementMultiplier 0.67`。
- 近战：寒晶自带侵蚀 智力10%+精神10% = items `innate_erosion_*`；精神迸发 `innate_erosion_mult=2.0`
  →"×2、合计 20%/20%" ✓；侵蚀→迸发转化在 `FrostSwordRunes.h::Upgrade` ✓；金色符文 +0.5 s
  与 `SwingCooldownReduceSeconds=.5f+Modifiers` 合成 1 s"每挥一次只结算一次" ✓；
  飞剑 4 把/30 s/15 s/×1.2 = `RuneOrbBladesComponent.h` 常量 ✓；`runeBlades` 技能描述与
  trait 逐字同口径（仅"逐把/随机一把"措辞差，行为=每按一次发一把，无碍）。
- a762"稳定性 1.25 倍"= `stability_mult 1.25` ✓；主卡各行动态取自 `Calculate` ✓；
  弹种 `ammo_item_id`→`ammo_types.json`→items 三方映射十枪全存在 ✓；
  面板对枪械跳过静态 物理攻击/弹匣容量 行，弹巢容量（715）静态值 6 = base ✓。

## 登记未改（非本次错误，属死代码/流程提示）

- `ColdSteelItemTooltipData.cpp` L235–238 旧 2D `attack/ammoConfig` 分支：当前 items 无使用者；
  若将来复用，`换弹时间` 直接拼 `ms` 而后端语义是秒，需先修单位再启用。
- `tooltip-reference.json` 的 `craft` 表全部为空对象 → L119–121 分支无输出，无漂移源。
- M4 回退分支（L230）仅在目录加载失败时生效，字段名取自 CDO，保留。
- 换弹显示值（715 为动画 clip 长）与 traits"6.8 秒"（目录值）在 clip 改节奏时会分叉：
  改 `EmptyReload`/clip 时记得同步 traits。

## 工具与验证

- `Tools/Weapons/check_attachment_consistency.py` 新增第 6 组断言：traits 必备、槽位清单 =
  实际槽集、禁"下挂"、traits 数字回 base（射速/组速/开镜/容量/射程/弹速）、items 静态
  物理攻击/容量 = `base.damage`/`mag_size`。**当前 PASS（0 问题）**。
- 未做：游戏内浮窗观感由用户自测（本轮无 C++ 改动，数据读盘即生效）。
