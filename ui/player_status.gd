extends RefCounted
## 角色属性数据模型（从旧版 data/combat-formulas.json + system-ui UI_DATA_CONFIG 迁移）
## 六维决定战斗属性/上限，公式与旧版一致；hp/击杀由 main.gd 从 player/enemy 信号同步。

signal changed

var character_name := "轮回者"
var character_class := "初心者"
var level := 1
var attr_points := 0
var exp := 0
var hp := 100
var mp := 100
var stamina := 100
var str := 10
var dex := 10
var intt := 10
var con := 10
var wis := 10
var luck := 10
var hp_regen := 1
var mp_regen := 1
var loop_count := 0
var survive_days := 1
var kills := 0
var quests := 0
var gene_lock := "未开启"
var rank := "F"
var collision_radius := 0.35
var move_speed := 5.0
var dodge_cooldown_ms := 800
var attack_range := 30.0
var knockback := 0.0
var view_width := 75.0

## ---- 旧版 combat-formulas.json ----
const ATK_BASE := 10.0
const ATK_STR := 0.05
const ATK_DEX := 0.1
const DEF_CON := 1.2
const DEF_STR := 0.3
const MATK_INT := 1.5
const MATK_WIS := 0.5
const MDEF_WIS := 1.2
const MDEF_INT := 0.3
const CRIT_BASE := 2.0
const CRIT_LUCK := 1.0
const ASPD_DEX := 0.02
const SPEED_DEX := 0.05
const STAMINA_REGEN_BASE := 1.0
const STAMINA_REGEN_DEX := 0.01

func max_hp() -> int:
	return 100 + con * 10

func max_mp() -> int:
	return 100 + wis * 10 + intt * 5

func max_stamina() -> int:
	return 100

func max_exp() -> int:
	# expPerLevel: base 20 + level*20 + level²*12，再 × final(2) × global(4)
	return int((20 + level * 20 + level * level * 12) * 2 * 4)

func atk() -> int:
	return roundi(ATK_BASE + str * ATK_STR + dex * ATK_DEX)

func def() -> int:
	return floori(con * DEF_CON + str * DEF_STR)

func matk() -> int:
	return floori(intt * MATK_INT + wis * MATK_WIS)

func mdef() -> int:
	return floori(wis * MDEF_WIS + intt * MDEF_INT)

func crit() -> int:
	return floori(CRIT_BASE + luck * CRIT_LUCK)

func crit_res() -> int:
	return floori(con * 1.0)

func aspd() -> float:
	return 1.0 + dex * ASPD_DEX

func speed_mult() -> float:
	return dex * SPEED_DEX

func stamina_regen() -> float:
	return STAMINA_REGEN_BASE + dex * STAMINA_REGEN_DEX

## ---- 同步入口（main.gd 从稳定信号调用） ----

func set_hp(v: int) -> void:
	hp = maxi(0, v)
	changed.emit()

func set_mp(v: int) -> void:
	mp = maxi(0, v)
	changed.emit()

func set_stamina(v: int) -> void:
	stamina = maxi(0, v)
	changed.emit()

func set_kills(v: int) -> void:
	kills = v
	changed.emit()
