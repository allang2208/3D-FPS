extends PanelContainer
## 装备/物品浮窗（复刻旧版 equip-tooltip 三段式）
## 左侧：附魔面板（tt-enchant，有附魔才显示）+ 改造面板（tt-craft，有改造才显示）
## 右侧主信息（tt-main）：图标+名称(+已强化)+类型|稀有度|Lv、属性行、
##   分组额外信息（分类/武器参数/枪械参数/武器特效/防御/套装/特殊攻击/消耗品）、斜体描述
## 行为由 backpack_hud 驱动：悬停跟随、点击固定、贴边翻转、关闭按钮。

const Style := preload("res://ui/style.gd")

signal close_requested

var _pinned := false
var _icon: TextureRect
var _name_label: Label
var _name_row: HBoxContainer
var _badge: Label
var _type_row: HBoxContainer
var _stats_box: VBoxContainer
var _extra_box: VBoxContainer
var _desc_label: Label
var _close_btn: Button
var _craft_col: VBoxContainer
var _enchant_col: VBoxContainer
var _main_col: VBoxContainer
var _font_title: SystemFont
var _font_value: SystemFont

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	theme = Style.make_theme()
	_font_title = Style.make_font(700)
	_font_value = Style.make_font(600)
	var panel_sb := Style.make_style(Style.COLOR_TT_BG, Style.COLOR_TT_BORDER, 8, 2)
	panel_sb.shadow_color = Style.COLOR_TT_SHADOW
	panel_sb.shadow_size = 12
	panel_sb.shadow_offset = Vector2(0, 4)
	add_theme_stylebox_override("panel", panel_sb)
	_build()

func _build() -> void:
	var margin := MarginContainer.new()
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_theme_constant_override("margin_left", 18)
	margin.add_theme_constant_override("margin_right", 18)
	margin.add_theme_constant_override("margin_top", 14)
	margin.add_theme_constant_override("margin_bottom", 14)
	add_child(margin)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	margin.add_child(row)
	# 附魔列（左）
	_enchant_col = VBoxContainer.new()
	_enchant_col.custom_minimum_size = Vector2(180, 0)
	_enchant_col.add_theme_constant_override("separation", 4)
	_enchant_col.visible = false
	row.add_child(_enchant_col)
	# 改造列（左）
	_craft_col = VBoxContainer.new()
	_craft_col.custom_minimum_size = Vector2(300, 0)
	_craft_col.add_theme_constant_override("separation", 4)
	_craft_col.visible = false
	row.add_child(_craft_col)
	# 主信息列（右）
	_main_col = VBoxContainer.new()
	_main_col.custom_minimum_size = Vector2(360, 0)
	_main_col.add_theme_constant_override("separation", 6)
	row.add_child(_main_col)
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 10)
	_main_col.add_child(header)
	_icon = TextureRect.new()
	_icon.custom_minimum_size = Vector2(34, 34)
	_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	header.add_child(_icon)
	var title_box := VBoxContainer.new()
	title_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title_box.add_theme_constant_override("separation", 2)
	header.add_child(title_box)
	_name_row = HBoxContainer.new()
	_name_row.add_theme_constant_override("separation", 6)
	title_box.add_child(_name_row)
	_name_label = Label.new()
	_name_label.add_theme_font_size_override("font_size", 18)
	_name_label.add_theme_font_override("font", _font_title)
	_name_label.add_theme_color_override("font_color", Style.COLOR_TT_NAME)
	_name_row.add_child(_name_label)
	_type_row = HBoxContainer.new()
	_type_row.add_theme_constant_override("separation", 4)
	title_box.add_child(_type_row)
	_close_btn = Button.new()
	_close_btn.text = "✕"
	_close_btn.custom_minimum_size = Vector2(24, 24)
	_close_btn.add_theme_stylebox_override("normal", Style.make_style(Style.COLOR_TT_CLOSE_BG, Color(0, 0, 0, 0.0), 12, 0))
	_close_btn.add_theme_stylebox_override("hover", Style.make_style(Style.COLOR_TT_CLOSE_HOVER, Color(0, 0, 0, 0.0), 12, 0))
	_close_btn.add_theme_stylebox_override("pressed", Style.make_style(Style.COLOR_TT_CLOSE_HOVER, Color(0, 0, 0, 0.0), 12, 0))
	_close_btn.add_theme_color_override("font_color", Color.WHITE)
	_close_btn.add_theme_font_size_override("font_size", 13)
	_close_btn.pressed.connect(func() -> void: close_requested.emit())
	header.add_child(_close_btn)
	_stats_box = VBoxContainer.new()
	_stats_box.add_theme_constant_override("separation", 3)
	_main_col.add_child(_stats_box)
	_extra_box = VBoxContainer.new()
	_extra_box.add_theme_constant_override("separation", 3)
	_main_col.add_child(_extra_box)
	_desc_label = Label.new()
	_desc_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_desc_label.add_theme_font_size_override("font_size", 12)
	_desc_label.add_theme_color_override("font_color", Style.COLOR_TT_DESC)
	_main_col.add_child(_desc_label)

func render(item: Dictionary) -> void:
	if item.is_empty():
		return
	_render_main(item)
	_render_craft(item)
	_render_enchant(item)

## ---------- 主信息 ----------

func _render_main(item: Dictionary) -> void:
	var icon_path := String(item.get("icon", ""))
	var tex := load(icon_path) if icon_path != "" else null
	_icon.texture = tex if tex is Texture2D else null
	_name_label.text = String(item.get("name", ""))
	if _badge != null:
		_badge.queue_free()
		_badge = null
	var enhance: int = item.get("enhanceLevel", 0)
	if enhance > 0:
		_badge = Label.new()
		_badge.text = "已强化 +%d" % enhance
		_badge.add_theme_font_size_override("font_size", 12)
		_badge.add_theme_font_override("font", _font_value)
		_badge.add_theme_color_override("font_color", Style.COLOR_BADGE_GOLD_TEXT)
		_badge.add_theme_stylebox_override("normal", Style.make_style(Style.COLOR_BADGE_GOLD_BG, Color(0, 0, 0, 0), 4, 0))
		_badge.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		_badge.custom_minimum_size = Vector2(74, 18)
		_name_row.add_child(_badge)
	# 类型 | 稀有度 | Lv
	_clear(_type_row)
	var type_lbl := Label.new()
	type_lbl.text = String(item.get("type", "物品"))
	type_lbl.add_theme_font_size_override("font_size", 12)
	type_lbl.add_theme_color_override("font_color", Style.COLOR_TT_TYPE)
	_type_row.add_child(type_lbl)
	var rarity_key := String(item.get("rarity", "common"))
	var rarity_lbl := Label.new()
	rarity_lbl.text = "| " + Style.rarity_label(rarity_key)
	rarity_lbl.add_theme_font_size_override("font_size", 12)
	var ls := LabelSettings.new()
	ls.font_size = 12
	ls.font_color = Style.rarity_color(rarity_key)
	ls.outline_size = 2
	ls.outline_color = Color.BLACK
	rarity_lbl.label_settings = ls
	_type_row.add_child(rarity_lbl)
	var level: int = item.get("level", 0)
	if level > 0:
		var lv_lbl := Label.new()
		lv_lbl.text = "| Lv.%d" % level
		lv_lbl.add_theme_font_size_override("font_size", 12)
		lv_lbl.add_theme_color_override("font_color", Style.COLOR_TT_TYPE)
		_type_row.add_child(lv_lbl)
	# 属性行
	_clear(_stats_box)
	var stats: Array = item.get("stats", [])
	for s in stats:
		var name := String(s.get("name", ""))
		if name == "":
			continue
		_add_row(_stats_box, name, String(s.get("value", "")), bool(s.get("pos", false)))
	# 分组额外信息
	_clear(_extra_box)
	_render_extra(item)
	# 描述
	_desc_label.text = String(item.get("desc", ""))

func _render_extra(item: Dictionary) -> void:
	var category := String(item.get("category", ""))
	_add_row(_extra_box, "分类", category, false)
	var weapon_type_tag := String(item.get("weaponTypeTag", ""))
	if weapon_type_tag != "":
		_add_row(_extra_box, "武器类型", weapon_type_tag, false)
	elif item.has("weaponType"):
		_add_row(_extra_box, "武器类型", String(item.get("weaponType", "")), false)
	var equip_slot := String(item.get("equipSlot", ""))
	if equip_slot != "":
		_add_row(_extra_box, "装备槽位", equip_slot, false)
	if item.has("weaponId"):
		_add_row(_extra_box, "武器ID", String(item.get("weaponId", "")), false)
	if item.has("weaponCategory"):
		_add_row(_extra_box, "武器分类", String(item.get("weaponCategory", "")), false)
	var is_weapon := item.has("weaponId") or category.begins_with("weapon") or item.has("weaponType")
	if is_weapon:
		_render_weapon_extra(item, category)
	if category == "armor" or category == "accessory":
		_render_defense_extra(item)
	if item.has("specialAttack"):
		_render_special_attack(item)
	if category == "consumable":
		_render_consumable_extra(item)
	var stack: int = item.get("stack", 1)
	if stack > 1:
		_add_row(_extra_box, "堆叠数量", str(stack), false)

func _render_weapon_extra(item: Dictionary, category: String) -> void:
	var attack: Dictionary = item.get("attack", {})
	var shield := String(item.get("weaponType", "")) == "shield"
	if shield:
		_add_group_title(_extra_box, "🛡 防御参数")
		var defense: Dictionary = item.get("defense", {})
		if not defense.is_empty():
			var base: int = defense.get("base", 0)
			var per: int = defense.get("perEnhance", 0)
			_add_row(_extra_box, "防御力", "%d（基础 %d + 强化等级 × %d）" % [base + (item.get("enhanceLevel", 0) as int) * per, base, per], false)
			if defense.has("damageReduction"):
				_add_row(_extra_box, "防御减伤", "%d%%" % int(float(defense["damageReduction"]) * 100), false)
			if defense.has("staminaCost"):
				_add_row(_extra_box, "防御受击体力", str(defense["staminaCost"]), false)
		return
	_add_group_title(_extra_box, "⚔ 攻击参数")
	if attack.is_empty():
		return
	var range_v: int = attack.get("range", 0)
	if range_v > 0:
		_add_row(_extra_box, "攻击距离", "%dpx" % range_v, false)
	var speed_v = attack.get("bulletSpeed", attack.get("projectileSpeed", 0))
	if int(speed_v) > 0:
		_add_row(_extra_box, "子弹速度", "%dpx/s" % int(speed_v), false)
	if attack.has("attackInterval"):
		_add_row(_extra_box, "攻击间隔", "%dms" % int(attack["attackInterval"]), false)
	if attack.has("hitType"):
		_add_row(_extra_box, "命中类型", String(attack["hitType"]), false)
	if attack.has("damageType"):
		_add_row(_extra_box, "伤害类型", String(attack["damageType"]), false)
	if attack.has("knockback"):
		_add_row(_extra_box, "击退距离", "%dpx" % int(attack["knockback"]), false)
	# 枪械参数
	if item.has("ammoConfig") and category == "weapon_ranged":
		_add_group_title(_extra_box, "🔫 武器参数")
		var ammo: Dictionary = item.get("ammoConfig", {})
		var ammo_max: int = ammo.get("max", 0)
		if ammo.has("max") and ammo_max > 0:
			_add_row(_extra_box, "子弹数量", "%d发" % ammo_max, false)
		if ammo.has("reloadTime"):
			_add_row(_extra_box, "换弹时间", "%dms" % int(ammo["reloadTime"]), false)
		if range_v > 0:
			_add_row(_extra_box, "射程", "%dpx" % range_v, false)
		if item.has("spreadParams"):
			var sp: Dictionary = item["spreadParams"]
			_add_row(_extra_box, "最大散布角度", "±%d°" % int(sp.get("maxAngle", 0)), false)
	# 武器特效（旧版：机枪减速 / 过热）
	var effects := []
	if bool(item.get("isTwoHanded", false)) and String(item.get("weaponType", "")).contains("machine"):
		effects.append(["移动速度", "-50%", false, true])
	var heat: Dictionary = item.get("heatParams", {})
	if not heat.is_empty() and heat.has("overheatTime"):
		effects.append(["过热时间", "%.1f秒" % (float(heat["overheatTime"]) / 1000.0), false, false])
	if not effects.is_empty():
		_add_group_title(_extra_box, "⚡ 武器特效")
		for e in effects:
			_add_row(_extra_box, String(e[0]), String(e[1]), bool(e[2]), bool(e[3]))

func _render_defense_extra(item: Dictionary) -> void:
	if item.has("armorSet"):
		var set_names := {
			"light": "疾风（轻甲）", "robe": "秘法（法袍）", "heavy": "壁垒（重甲）",
			"flowing": "流云（稀有轻甲）", "eclipse": "蚀月（稀有法袍）", "zhenyue": "镇岳（稀有重甲）",
			"stellar": "星穹（史诗轻甲）", "lunar": "苍月（史诗法袍）", "tiangang": "天罡（史诗重甲）",
			"oracle": "神域（神话重甲）", "oracle_robe": "神谕（神话法袍）", "holy": "圣辉（神话轻甲）",
		}
		var set_key := String(item["armorSet"])
		var bonus := String(item.get("setBonusDesc", ""))
		if bonus == "":
			bonus = String(item.get("setBonuses", {}).get(set_key, ""))
		_add_group_title(_extra_box, "🛡 套装：" + String(set_names.get(set_key, set_key)))
		if bonus != "":
			_add_row(_extra_box, "效果", bonus, false)
	var defense: Dictionary = item.get("defense", {})
	if not defense.is_empty():
		var base: int = defense.get("base", 0)
		var per: int = defense.get("perEnhance", 0)
		_add_row(_extra_box, "防御力", "%d（基础 %d + 强化等级 × %d）" % [base + (item.get("enhanceLevel", 0) as int) * per, base, per], false)
	var bs: Dictionary = item.get("bonusStats", {})
	if not bs.is_empty():
		_add_group_title(_extra_box, "✓ 属性加成")
		var attr_names := {
			"str": "力量", "dex": "敏捷", "int": "智力", "con": "体质", "wis": "精神", "luck": "幸运",
			"atk": "物理攻击", "matk": "魔法攻击", "crit": "暴击率", "maxHp": "最大生命", "maxMp": "最大魔法",
		}
		for k in bs.keys():
			var v: int = int(bs[k])
			if v == 0:
				continue
			var suffix := "%" if k == "crit" else ""
			_add_row(_extra_box, String(attr_names.get(k, k)), "+%d%s" % [v, suffix], true)

func _render_special_attack(item: Dictionary) -> void:
	var sa: Dictionary = item["specialAttack"]
	_add_group_title(_extra_box, "⚔ 特殊攻击")
	if sa.has("damageType"):
		_add_row(_extra_box, "伤害类型", String(sa["damageType"]), false)
	if sa.has("damageFormula"):
		_add_row(_extra_box, "伤害公式", String(sa["damageFormula"]), false)
	if sa.has("duration"):
		_add_row(_extra_box, "持续时间", "%d秒" % int(sa["duration"]), false)
	if sa.has("cooldown"):
		_add_row(_extra_box, "冷却时间", "%d秒" % int(sa["cooldown"]), false)

func _render_consumable_extra(item: Dictionary) -> void:
	_add_group_title(_extra_box, "✓ 使用效果")
	var effect: Dictionary = item.get("useEffect", {})
	if effect.has("hp"):
		_add_row(_extra_box, "恢复类型", "生命值", false)
		_add_row(_extra_box, "恢复量", "+%d" % int(effect["hp"]), true)
	if effect.has("mp"):
		_add_row(_extra_box, "恢复类型", "魔法值", false)
		_add_row(_extra_box, "恢复量", "+%d" % int(effect["mp"]), true)
	if float(item.get("useCooldown", 0.0)) > 0:
		_add_row(_extra_box, "冷却时间", "%.1f秒" % float(item["useCooldown"]), false)
	_add_row(_extra_box, "使用方式", "右键点击 / 拖入快捷栏", false)

## ---------- 改造面板（tt-craft） ----------

func _render_craft(item: Dictionary) -> void:
	_clear(_craft_col)
	var craft_data: Dictionary = item.get("_craftData", {})
	var has_craft := not craft_data.is_empty()
	if not has_craft:
		_craft_col.visible = false
		return
	_craft_col.visible = true
	_add_panel_title(_craft_col, "🔧 改造项目", Style.COLOR_TT_CRAFT_POS)
	for slot_id in craft_data.keys():
		var mod := String(craft_data[slot_id])
		_add_row(_craft_col, String(slot_id), mod, false)
	var effects: Dictionary = item.get("_craftEffects", {})
	if not effects.is_empty():
		_add_panel_title(_craft_col, "📊 合计改造数值", Style.COLOR_TT_NAME)
		for k in effects.keys():
			var v = effects[k]
			if v == null or v == false or int(v) == 0:
				continue
			_add_row(_craft_col, String(k), str(v), false, typeof(v) == TYPE_FLOAT and float(v) < 0.0)

## ---------- 附魔面板（tt-enchant） ----------

func _render_enchant(item: Dictionary) -> void:
	_clear(_enchant_col)
	if not bool(item.get("_isEnchanted", false)) or not item.has("_enchantData"):
		_enchant_col.visible = false
		return
	_enchant_col.visible = true
	_add_panel_title(_enchant_col, "✨ 附魔效果", Style.COLOR_TT_ENCHANT_NAME)
	var ed: Dictionary = item["_enchantData"]
	var name_html := ""
	if ed.has("prefix"):
		name_html += String(ed["prefix"].get("name", "")) + " "
	name_html += String(item.get("name", ""))
	if ed.has("suffix"):
		name_html += " " + String(ed["suffix"].get("name", ""))
	var name_lbl := Label.new()
	name_lbl.text = name_html
	name_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	name_lbl.add_theme_font_size_override("font_size", 13)
	name_lbl.add_theme_color_override("font_color", Style.COLOR_TT_ENCHANT_NAME)
	_enchant_col.add_child(name_lbl)
	var ee: Dictionary = item.get("_enchantEffects", {})
	var effect_map := [
		["damagePercent", "攻击力", func(v): return "+%d%%" % int(float(v) * 100)],
		["attackIntervalMul", "攻击间隔", func(v): return "×%.2f" % float(v)],
		["critRate", "暴击率", func(v): return "+%d%%" % int(float(v) * 100)],
		["poisonOnHit", "特殊效果", func(_v): return "攻击叠中毒"],
		["piercingBonus", "穿透目标", func(v): return "+%d" % int(v)],
	]
	for row in effect_map:
		if ee.has(row[0]):
			var v = ee[row[0]]
			if v == null or v == false:
				continue
			var f: Callable = row[2]
			var lbl := Label.new()
			lbl.text = "%s: %s" % [String(row[1]), str(f.call(v))]
			lbl.add_theme_font_size_override("font_size", 12)
			lbl.add_theme_color_override("font_color", Style.COLOR_TT_VAL)
			_enchant_col.add_child(lbl)

## ---------- 工具 ----------

func is_pinned() -> bool:
	return _pinned

func set_pinned(v: bool) -> void:
	_pinned = v
	mouse_filter = Control.MOUSE_FILTER_STOP if v else Control.MOUSE_FILTER_IGNORE

func _add_group_title(parent: Node, text: String) -> void:
	var sep := HSeparator.new()
	sep.modulate = Style.COLOR_TT_SECTION_BORDER
	parent.add_child(sep)
	var lbl := Label.new()
	lbl.text = text
	lbl.add_theme_font_size_override("font_size", 12)
	lbl.add_theme_font_override("font", _font_value)
	lbl.add_theme_color_override("font_color", Style.COLOR_TT_NAME)
	parent.add_child(lbl)

func _add_panel_title(parent: Node, text: String, color: Color) -> void:
	var sep := HSeparator.new()
	sep.modulate = Style.COLOR_TT_SECTION_BORDER
	parent.add_child(sep)
	var lbl := Label.new()
	lbl.text = text
	lbl.add_theme_font_size_override("font_size", 12)
	lbl.add_theme_font_override("font", _font_title)
	lbl.add_theme_color_override("font_color", color)
	parent.add_child(lbl)

func _add_row(parent: Node, name: String, value: String, pos := false, neg := false) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	var name_lbl := Label.new()
	name_lbl.text = name
	name_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	name_lbl.add_theme_font_size_override("font_size", 12)
	name_lbl.add_theme_color_override("font_color", Style.COLOR_TT_TYPE)
	row.add_child(name_lbl)
	var val_lbl := Label.new()
	val_lbl.text = value
	val_lbl.add_theme_font_size_override("font_size", 13)
	val_lbl.add_theme_font_override("font", _font_value)
	var c := Style.COLOR_TT_VAL
	if neg:
		c = Style.COLOR_TT_CRAFT_NEG
	elif pos:
		c = Style.COLOR_TT_POS
	val_lbl.add_theme_color_override("font_color", c)
	row.add_child(val_lbl)
	parent.add_child(row)

func _clear(box: Node) -> void:
	for child in box.get_children():
		child.queue_free()
