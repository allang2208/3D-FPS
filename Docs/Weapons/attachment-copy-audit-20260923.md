# 改造件文字/说明/数值规则审计与口径修订（2026-09-23）

对 `Content/ColdSteelData/gunsmith.json`（10 枪全量配件）、读端代码与技能规则做了一遍三方互审，
按用户裁定落地修订：**激光以实际效果为准**（`ads_percent=-0.2` = 开镜耗时 −20%，旧"−200 ms 绝对值"
说法作废），其余按审计建议执行。技能正文口径见
[改造配件标准「配件数值与说明分工」](../../skills/ue5-weapon-workflow/references/attachment-standard.md)。

## 1 规则修订（skill）

- `attachment-standard.md` §1–§5 全节改写：
  - §1 数据路径改为 `weapons[].options[<slot>][].stats` 并登记 `common_options` 合并语义
    （`barrel` short/long 无条件并入全部武器含手枪，是否限定为待决项）；补 `shake_mult`、
    `empty_reload_mult` 键；激光口径定稿为百分比。
  - §2 描述数字拆两条：可推导数字禁写；静态规格数字（倍率、口径、"80 米"、原厂容量）允许但
    必须注明权威来源（`base.mag_size`、`TacticalDeviceComponent.cpp Range=8000.f`）；新增
    **行名与措辞统一表**（开镜耗时/普通换弹/后坐力降低/稳定性"提高、降低"），`effects` 一行只讲
    一个 stats key、同 id 跨枪逐字一致、换弹行禁数字。
  - §3 数值表更新为全目录快照：激光改 −20%，补 `ext_mag`(+5%)、`tactical_vertical_foregrip`
    (−25%)、`pso1_4x`(0)、`ash12_cheek_rest`(+5%)、`ash12_tactical_suppressor`(+10%)、
    `ash12_tactical_brake`(+5%)；作废"三把步枪"范围，注明以 `dump_attachment_values.py` 重生成
    （遵守 `publication.md` 脏检查）。
  - §5 收尾自检脚本化：`Tools/Weapons/check_attachment_consistency.py`（覆盖旧宽松版）。
- `SKILL.md` 第 42 行入口与执行主线第 8 条、`integration.md` 数据口径行、
  `weapon-formula-balancing.md` ADS 行同步改口径。

## 2 数据修订（gunsmith.json，纯文案，`stats` 一个未动）

- 速装器："普通与空仓换弹均为3.85秒（基础值）" → "统一为同一耗时"（3.85 唯一来源保留在
  `DanWesson715WeaponAssets.h::EmptyReload`）。
- ASH-12 `ext_mag`："装填耗时增加25%" → "装填耗时更长"（与其余六枪逐字一致）。
- 全息/红点 `effects` ×20："开镜时间不变" → "开镜耗时不变"。
- `common_options.barrel`：合并行"后坐力增加15%；枪械稳定性降低15%"等拆为逐 key 单行；
  "ADS瞄准耗时" → "开镜耗时"。
- 措辞并轨 60 处：`后坐力控制提高`→`后坐力降低`（24）、`后坐力减少`→`后坐力降低`（12）、
  `枪械稳定性增加`→`枪械稳定性提高`（24）。
- `description`/`traits` 并轨 30 处："ADS瞄准时间"、"提高后坐力控制"、"瞄准耗时 240/450 ms" 等
  改用统一行名。
- 17 处"。 "拼接残句修复（M16A2×13、A762×4→合并、PKM×4）；M16 棱镜"配窄导轨底座"与
  "提把专用座"同句矛盾去重；M16 五件前握把双"使用…动作"叠句合并。

## 3 读端（C++，4 处字符串标签）

- `ColdSteelItemTooltipData.cpp`：合计改造行与主属性行"瞄准耗时"→"开镜耗时"，"正常换弹"→
  "普通换弹"（M4 回退分支同改）。
- `ColdSteelItemTooltipSummary.cpp`：`ads` 标签"瞄准耗时"→"开镜耗时"，`reload` 标签
  "正常换弹"→"普通换弹"。
- `M4GunsmithOverview/SelectedDetails`、`GunsmithWorkbenchAudit` 原本就用"开镜耗时"，无需改。

## 4 验证与未验证

- `Tools/Weapons/check_attachment_consistency.py` → **PASS（0 问题）**；`gunsmith.json` `json.load` 通过。
- 全目录复核：同 `(slot,id)` 的 `stats`/`effects` 跨枪逐字一致；`effects` 全部数字可由 `stats`
  推导；`benefit` 方向全对；`description` 无手写可推导数字（静态规格数字均有权威来源锚点）；
  traits 的开镜/射速数字与 `base` 全部吻合。
- 审计中间产物：`Saved/gunsmith_fixup_20260923.py`、`Saved/gunsmith_fixup2/3_20260923.py`、
  `Saved/gunsmith_recheck_20260923.py`、`Saved/gunsmith_audit_dump.txt`。
- **未做**（按用户规则不主动测试）：游戏内界面观感、颜色与提示排版由用户自测；
  `Docs/Weapons/attachment-values-20260921.md` 快照本轮未重新生成（目录处于未提交脏状态，
  遵守 `publication.md` 生成前脏检查），提交后可重跑 `dump_attachment_values.py`。
