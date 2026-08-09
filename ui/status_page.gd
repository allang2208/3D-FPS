extends Control
## 角色状态页（复刻旧版 status-page / UI_DATA_CONFIG / StatusTooltipHelper）
## 结构：角色头（名/职业/Lv/属性点）+ 状态条（生命/魔法/体力/经验）+
## 基础属性（六维两列）+ 战斗属性 + 详细信息 + 轮回信息；悬停显示旧版公式浮窗。

const Style := preload("res://ui/style.gd")
const PlayerStatusScript := preload("res://ui/player_status.gd")

var status: PlayerStatusScript

var _name_label: Label
var _class_label: Label
var _lv_label: Label
var _attr_label: Label
var _bars := {}
var _rows := {}
var _attr_plus := {}
var _tooltip: PanelContainer
var _tooltip_title: Label
var _tooltip_desc: Label
var _tooltip_body: VBoxContainer

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE

func setup(s: PlayerStatusScript) -> void:
	status = s
	status.changed.connect(_refresh)
	_build()
	_refresh()

func _build() -> void:
	_build_tooltip()
	var scroll := Style.make_scroll_container()
	scroll.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(scroll)
	var margin := MarginContainer.new()
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_theme_constant_override("margin_left", 14)
	margin.add_theme_constant_override("margin_right", 14)
	margin.add_theme_constant_override("margin_top", 4)
	margin.add_theme_constant_override("margin_bottom", 4)
	margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(margin)
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 8)
	margin.add_child(vbox)

	# 角色卡：金色强调条 + 名称/职业/等级/属性点
	var header_card := _make_card(vbox, 10)
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 10)
	header_card.add_child(header)
	var accent := ColorRect.new()
	accent.custom_minimum_size = Vector2(3, 20)
	accent.color = Style.THEME_GOLD
	header.add_child(accent)
	_name_label = _make_label(header, "轮回者", 20, Style.COLOR_TITLE_TEXT)
	_name_label.add_theme_font_override("font", Style.make_font(700))
	_class_label = _make_label(header, "初心者", 13, Style.COLOR_DIM_TEXT)
	_class_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_lv_label = _make_label(header, "Lv.1", 14, Style.COLOR_TEXT)
	_lv_label.add_theme_font_override("font", Style.make_font(600))
	_attr_label = _make_label(header, "属性点: 0", 13, Style.THEME_GOLD)
	_attr_label.add_theme_font_override("font", Style.make_font(600))

	# 状态卡
	var status_card := _make_card(vbox)
	_add_section_title(status_card, "状态")
	_add_bar(status_card, "生命", "hp", Style.COLOR_HP_HIGH)
	_add_bar(status_card, "魔法", "mp", Style.COLOR_MP_FILL)
	_add_bar(status_card, "体力", "stamina", Style.COLOR_STAMINA_FILL)
	_add_bar(status_card, "经验", "exp", Style.COLOR_EXP_FILL)

	# 基础属性卡（两列）
	var attr_card := _make_card(vbox)
	_add_section_title(attr_card, "基础属性")
	var attr_grid := GridContainer.new()
	attr_grid.columns = 2
	attr_grid.add_theme_constant_override("h_separation", 40)
	attr_grid.add_theme_constant_override("v_separation", 4)
	attr_card.add_child(attr_grid)
	for pair in [["力量", "str"], ["敏捷", "dex"], ["智力", "intt"]]:
		attr_grid.add_child(_make_row(pair[0], pair[1], "attr"))
	for pair in [["体质", "con"], ["精神", "wis"], ["幸运", "luck"]]:
		attr_grid.add_child(_make_row(pair[0], pair[1], "attr"))

	# 战斗属性卡
	var combat_card := _make_card(vbox)
	_add_section_title(combat_card, "战斗属性")
	for row in [
		["物理攻击", "atk"], ["物理防御", "def"], ["魔法攻击", "matk"], ["魔法防御", "mdef"],
		["暴击率", "crit"], ["暴击抵抗", "critRes"], ["攻击间隔", "aspd"], ["移动速度", "moveSpeed"],
	]:
		combat_card.add_child(_make_row(row[0], row[1], "combat"))

	# 详细信息卡
	var detail_card := _make_card(vbox)
	_add_section_title(detail_card, "详细信息")
	for row in [
		["体力恢复", "staminaRegen"], ["生命恢复", "hpRegen"], ["魔法恢复", "mpRegen"],
		["碰撞体积", "collisionRadius"], ["移动速度", "moveSpeedDetail"], ["闪避冷却", "dodgeCooldown"],
		["攻击距离", "attackRange"], ["击退距离", "knockback"], ["视野宽度", "viewRange"],
	]:
		detail_card.add_child(_make_row(row[0], row[1], "detail"))

	# 轮回信息卡
	var loop_card := _make_card(vbox)
	_add_section_title(loop_card, "轮回信息")
	for row in [
		["轮回次数", "loopCount"], ["存活天数", "surviveDays"], ["击杀数", "kills"],
		["完成任务", "quests"], ["基因锁", "geneLock"], ["主神评价", "rank"],
	]:
		loop_card.add_child(_make_row(row[0], row[1], "loop"))

func _make_card(parent: Node, pad := 12) -> VBoxContainer:
	var card := PanelContainer.new()
	# 原项目 status-section：半透明暗卡 + 8px 圆角 + 14px 内边距
	card.add_theme_stylebox_override("panel",
		Style.make_style(Style.COLOR_STATUS_CARD_BG, Style.COLOR_TRANSPARENT, 8, 0))
	parent.add_child(card)
	var m := MarginContainer.new()
	m.add_theme_constant_override("margin_left", 14)
	m.add_theme_constant_override("margin_right", 14)
	m.add_theme_constant_override("margin_top", pad)
	m.add_theme_constant_override("margin_bottom", pad)
	m.mouse_filter = Control.MOUSE_FILTER_IGNORE
	card.add_child(m)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	m.add_child(v)
	return v

func _refresh() -> void:
	if status == null:
		return
	_name_label.text = String(status.character_name)
	_class_label.text = String(status.character_class)
	_lv_label.text = "Lv.%d" % int(status.level)
	_attr_label.text = "属性点: %d" % int(status.attr_points)
	_set_bar("hp", int(status.hp), status.max_hp(), Style.COLOR_HP_HIGH, Style.COLOR_HP_MID, Style.COLOR_HP_LOW)
	_set_bar("mp", int(status.mp), status.max_mp(), Style.COLOR_MP_FILL, Style.COLOR_MP_FILL, Style.COLOR_MP_FILL)
	_set_bar("stamina", int(status.stamina), status.max_stamina(), Style.COLOR_STAMINA_FILL, Style.COLOR_STAMINA_FILL, Style.COLOR_STAMINA_FILL)
	_set_bar("exp", int(status.exp), status.max_exp(), Style.COLOR_EXP_FILL, Style.COLOR_EXP_FILL, Style.COLOR_EXP_FILL, true)
	_rows["str"].text = str(status.str)
	_rows["dex"].text = str(status.dex)
	_rows["intt"].text = str(status.intt)
	_rows["con"].text = str(status.con)
	_rows["wis"].text = str(status.wis)
	_rows["luck"].text = str(status.luck)
	for key in _attr_plus:
		_attr_plus[key].visible = status.attr_points > 0
	_rows["atk"].text = str(status.atk())
	_rows["def"].text = str(status.def())
	_rows["matk"].text = str(status.matk())
	_rows["mdef"].text = str(status.mdef())
	_rows["crit"].text = "%d%%" % status.crit()
	_rows["critRes"].text = "%d%%" % status.crit_res()
	_rows["aspd"].text = "%.2fx" % status.aspd()
	_rows["moveSpeed"].text = "%.0f m/s" % status.move_speed
	_rows["staminaRegen"].text = "%.2fx" % status.stamina_regen()
	_rows["hpRegen"].text = "%d/秒" % int(status.hp_regen)
	_rows["mpRegen"].text = "%d/3秒" % int(status.mp_regen)
	_rows["collisionRadius"].text = "%.2f" % status.collision_radius
	_rows["moveSpeedDetail"].text = "%.1f m/s" % status.move_speed
	_rows["dodgeCooldown"].text = "%dms" % int(status.dodge_cooldown_ms)
	_rows["attackRange"].text = "%.0fm" % status.attack_range
	_rows["knockback"].text = "%.0f" % status.knockback
	_rows["viewRange"].text = "%.0f°" % status.view_width
	_rows["loopCount"].text = str(status.loop_count)
	_rows["surviveDays"].text = str(status.survive_days)
	_rows["kills"].text = str(status.kills)
	_rows["quests"].text = str(status.quests)
	_rows["geneLock"].text = String(status.gene_lock)
	_rows["rank"].text = String(status.rank)

## ---------- 构建辅助 ----------

func _add_section_title(parent: Node, text: String) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	parent.add_child(row)
	var bar := ColorRect.new()
	bar.custom_minimum_size = Vector2(3, 14)
	bar.color = Style.THEME_GOLD
	row.add_child(bar)
	var lbl := _make_label(row, text, 14, Style.COLOR_TEXT)
	lbl.add_theme_font_override("font", Style.make_font(600))
	var line := HSeparator.new()
	line.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	line.add_theme_stylebox_override("separator",
		Style.make_style(Color(Style.THEME_GOLD, 0.30), Color(Style.THEME_GOLD, 0.30), 0, 0))
	row.add_child(line)

func _add_bar(parent: Node, label: String, key: String, fill_color: Color) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	parent.add_child(row)
	var lbl := _make_label(row, label, 13, Style.COLOR_DIM_TEXT)
	lbl.custom_minimum_size = Vector2(56, 0)
	var track := Panel.new()
	track.custom_minimum_size = Vector2(220, 14)
	track.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	track.add_theme_stylebox_override("panel",
		Style.make_style(Style.COLOR_BAR_TRACK, Style.COLOR_BAR_BORDER, 4, 1))
	row.add_child(track)
	var fill := Panel.new()
	fill.anchor_left = 0.0
	fill.anchor_top = 0.0
	fill.anchor_right = 0.0
	fill.anchor_bottom = 1.0
	fill.offset_top = 2
	fill.offset_bottom = -2
	fill.offset_left = 2
	fill.offset_right = -2
	fill.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var fsb := Style.make_style(fill_color, fill_color, 3, 0)
	fill.add_theme_stylebox_override("panel", fsb)
	track.add_child(fill)
	var value := _make_label(row, "", 13, Style.COLOR_TEXT)
	value.custom_minimum_size = Vector2(90, 0)
	value.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_bars[key] = {"fill": fill, "style": fsb, "value": value}
	_bind_tooltip(row, key)

func _make_row(label: String, key: String, _group: String) -> PanelContainer:
	var card := PanelContainer.new()
	# 原项目 attr-item：暖灰半透明底 + 4px 圆角 + hover 加深
	var sb := Style.make_style(Style.COLOR_ATTR_ROW_BG, Style.COLOR_TRANSPARENT, 4, 0)
	card.add_theme_stylebox_override("panel", sb)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	card.add_child(row)
	var name_lbl := _make_label(row, label, 13, Style.COLOR_DIM_TEXT)
	name_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var val_lbl := _make_label(row, "", 13, Style.COLOR_TEXT)
	val_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_rows[key] = val_lbl
	if _group == "attr":
		# 原项目属性点 + 分配按钮（有属性点时显示）
		var plus := Button.new()
		plus.text = "+"
		plus.custom_minimum_size = Vector2(20, 20)
		plus.visible = false
		plus.add_theme_font_size_override("font_size", 14)
		plus.add_theme_font_override("font", Style.make_font(700))
		plus.add_theme_stylebox_override("normal",
			Style.make_style(Style.COLOR_WHITE, Style.THEME_GOLD, 4, 2))
		plus.add_theme_stylebox_override("hover",
			Style.make_style(Style.COLOR_BADGE_GOLD_BG, Style.THEME_GOLD, 4, 2))
		plus.add_theme_stylebox_override("pressed",
			Style.make_style(Style.COLOR_BADGE_GOLD_BG, Style.THEME_GOLD, 4, 2))
		plus.add_theme_color_override("font_color", Style.COLOR_BLACK)
		plus.add_theme_color_override("font_hover_color", Style.COLOR_BLACK)
		plus.pressed.connect(func() -> void: _allocate(key))
		row.add_child(plus)
		_attr_plus[key] = plus
	card.mouse_filter = Control.MOUSE_FILTER_STOP
	var hover_sb := Style.make_style(Style.COLOR_ATTR_ROW_HOVER, Style.COLOR_TRANSPARENT, 4, 0)
	card.mouse_entered.connect(func() -> void:
		card.add_theme_stylebox_override("panel", hover_sb)
		_show_tooltip(key, get_viewport().get_mouse_position()))
	card.mouse_exited.connect(func() -> void:
		card.add_theme_stylebox_override("panel", sb)
		hide_tooltip())
	return card

func _allocate(key: String) -> void:
	if status == null or status.attr_points <= 0:
		return
	match key:
		"str": status.str += 1
		"dex": status.dex += 1
		"intt": status.intt += 1
		"con": status.con += 1
		"wis": status.wis += 1
		"luck": status.luck += 1
		_:
			return
	status.attr_points -= 1
	_refresh()

func _make_label(parent: Node, text: String, size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(l)
	return l

func _set_bar(key: String, value: int, max_v: int, c_high: Color, c_mid: Color, c_low: Color, pct_only := false) -> void:
	var bar: Dictionary = _bars.get(key, {})
	if bar.is_empty():
		return
	var m := maxi(1, max_v)
	var pct := clampf(float(value) / float(m), 0.0, 1.0)
	var fill := bar["fill"] as Panel
	fill.anchor_right = pct
	var col := c_high
	if pct <= 0.5 and pct > 0.25:
		col = c_mid
	elif pct <= 0.25:
		col = c_low
	var fsb: StyleBoxFlat = bar["style"]
	fsb.bg_color = col
	fsb.border_color = col
	var v_lbl := bar["value"] as Label
	v_lbl.text = ("%d%%" % int(pct * 100.0)) if pct_only else ("%d/%d" % [maxi(0, value), m])

## ---------- 悬停公式浮窗（复刻旧版 StatusTooltipHelper） ----------

func _build_tooltip() -> void:
	_tooltip = PanelContainer.new()
	_tooltip.name = "StatusTooltip"
	_tooltip.visible = false
	_tooltip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_tooltip.add_theme_stylebox_override("panel", Style.make_style(Style.COLOR_TT_BG, Style.COLOR_TT_BORDER, 8, 2))
	add_child(_tooltip)
	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_top", 8)
	margin.add_theme_constant_override("margin_bottom", 8)
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_tooltip.add_child(margin)
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 4)
	margin.add_child(vbox)
	_tooltip_title = Label.new()
	_tooltip_title.add_theme_font_size_override("font_size", Style.tt_size_title())
	_tooltip_title.add_theme_font_override("font", Style.tt_font_title())
	_tooltip_title.add_theme_color_override("font_color", Style.COLOR_TT_NAME)
	vbox.add_child(_tooltip_title)
	_tooltip_desc = Label.new()
	_tooltip_desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_tooltip_desc.custom_minimum_size = Vector2(240, 0)
	_tooltip_desc.add_theme_font_size_override("font_size", Style.tt_size_body())
	_tooltip_desc.add_theme_font_override("font", Style.tt_font_body())
	_tooltip_desc.add_theme_color_override("font_color", Style.COLOR_TT_DESC)
	vbox.add_child(_tooltip_desc)
	_tooltip_body = VBoxContainer.new()
	_tooltip_body.add_theme_constant_override("separation", 2)
	vbox.add_child(_tooltip_body)

func _bind_tooltip(row: Control, key: String) -> void:
	row.mouse_filter = Control.MOUSE_FILTER_STOP
	row.mouse_entered.connect(func() -> void: _show_tooltip(key, get_viewport().get_mouse_position()))
	row.mouse_exited.connect(func() -> void: hide_tooltip())

func _show_tooltip(key: String, at: Vector2) -> void:
	if status == null:
		return
	_tooltip_title.text = _title(key)
	_tooltip_desc.text = _desc(key)
	for child in _tooltip_body.get_children():
		child.queue_free()
	for line in _lines(key):
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 12)
		var name_lbl := Label.new()
		name_lbl.text = String(line[0])
		name_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		name_lbl.add_theme_font_size_override("font_size", Style.tt_size_body())
		name_lbl.add_theme_font_override("font", Style.tt_font_body())
		name_lbl.add_theme_color_override("font_color", Style.COLOR_TT_TYPE)
		row.add_child(name_lbl)
		var val_lbl := Label.new()
		val_lbl.text = String(line[1])
		val_lbl.add_theme_font_size_override("font_size", Style.tt_size_value())
		val_lbl.add_theme_font_override("font", Style.tt_font_value())
		val_lbl.add_theme_color_override("font_color", Style.COLOR_TT_VAL)
		row.add_child(val_lbl)
		_tooltip_body.add_child(row)
	_tooltip.visible = true
	_place_tooltip(at)

func hide_tooltip() -> void:
	if _tooltip != null:
		_tooltip.visible = false

func _process(_delta: float) -> void:
	if _tooltip != null and _tooltip.visible:
		_place_tooltip(get_viewport().get_mouse_position())

func _place_tooltip(at: Vector2) -> void:
	var ts := _tooltip.get_combined_minimum_size()
	var vp := get_viewport_rect().size
	var pos := at + Vector2(16, 14)
	if pos.x + ts.x > vp.x - 8:
		pos.x = at.x - ts.x - 12
	if pos.y + ts.y > vp.y - 8:
		pos.y = at.y - ts.y - 12
	pos.x = clampf(pos.x, 8, maxf(8, vp.x - ts.x - 8))
	pos.y = clampf(pos.y, 8, maxf(8, vp.y - ts.y - 8))
	_tooltip.position = pos

func _title(key: String) -> String:
	return {
		"hp": "生命值", "mp": "魔法值", "stamina": "体力值", "exp": "经验值",
		"str": "力量", "dex": "敏捷", "intt": "智力", "con": "体质", "wis": "精神", "luck": "幸运",
		"atk": "物理攻击", "def": "物理防御", "matk": "魔法攻击", "mdef": "魔法防御",
		"crit": "暴击率", "critRes": "暴击抵抗", "aspd": "攻击间隔", "moveSpeed": "移动速度",
		"staminaRegen": "体力恢复", "hpRegen": "生命恢复", "mpRegen": "魔法恢复",
		"collisionRadius": "碰撞体积", "moveSpeedDetail": "移动速度", "dodgeCooldown": "闪避冷却",
		"attackRange": "攻击距离", "knockback": "击退距离", "viewRange": "视野宽度",
		"loopCount": "轮回次数", "surviveDays": "存活天数", "kills": "击杀数", "quests": "完成任务",
		"geneLock": "基因锁", "rank": "主神评价",
	}.get(key, key)

func _desc(key: String) -> String:
	return {
		"hp": "体质决定生命上限。", "mp": "精神智力共同决定魔法上限。",
		"stamina": "冲刺、闪避、攻击消耗体力，停止消耗后自动恢复。",
		"exp": "击杀怪物、完成任务获得经验，满额后升级。",
		"str": "提升物理攻击与少量物理防御。", "dex": "提升移动速度、命中、暴击伤害基础与体力恢复倍率。",
		"intt": "提升魔法攻击、魔法上限与少量魔法防御。",
		"con": "提升生命值、物理防御与暴击抵抗。", "wis": "提升魔法防御、魔法上限与少量魔法攻击。",
		"luck": "提升暴击率。", "atk": "角色基础物攻 + 力量敏捷加成。", "def": "减免受到的物理伤害。",
		"matk": "影响魔法类技能与普攻伤害。", "mdef": "减免受到的魔法伤害。",
		"crit": "攻击时触发暴击的概率。", "critRes": "降低被敌人暴击的概率。",
		"aspd": "当前武器两次攻击之间的冷却时间。", "moveSpeed": "角色正常移动时的最大速度。",
		"staminaRegen": "停止消耗体力后的每秒恢复量倍率。", "hpRegen": "每秒自动恢复的生命值。",
		"mpRegen": "每 3 秒自动恢复的魔法值。", "collisionRadius": "角色与怪物、障碍物碰撞的有效半径。",
		"moveSpeedDetail": "受敏捷、地形 buff、祭品影响的实时移动速度。",
		"dodgeCooldown": "使用闪避后再一次可用所需时间。", "attackRange": "当前武器攻击可命中敌人的最远距离。",
		"knockback": "攻击命中后推开敌人的距离。", "viewRange": "摄像机渲染的游戏画面宽度。",
		"loopCount": "已完成的主神空间轮回次数。", "surviveDays": "本轮游戏已存活的天数。",
		"kills": "本轮游戏累计击杀的敌人数量。", "quests": "本轮游戏已完成的主神任务数量。",
		"geneLock": "基因锁开启等级，影响额外成长。", "rank": "根据本轮表现给出的综合评价。",
	}.get(key, "暂无说明")

func _lines(key: String) -> Array:
	var s := status
	match key:
		"hp":
			return [["基础生命", "100"], ["体质加成", str(s.con * 10)], ["当前上限", str(s.max_hp())], ["当前生命", "%d/%d" % [s.hp, s.max_hp()]]]
		"mp":
			return [["基础魔法", "100"], ["精神加成", str(s.wis * 10)], ["智力加成", str(s.intt * 5)], ["当前上限", str(s.max_mp())]]
		"stamina":
			return [["当前体力", "%d/%d" % [s.stamina, s.max_stamina()]]]
		"exp":
			return [["当前", "%d/%d" % [s.exp, s.max_exp()]]]
		"str":
			return [["物攻加成", "%.2f" % (s.str * 0.05)], ["当前物攻", str(s.atk())], ["每点力量 ≈ +0.05 物攻", ""]]
		"dex":
			return [["移速加成", "%.2f" % (s.dex * 0.05)], ["体力恢复倍率", "%.2fx" % s.stamina_regen()]]
		"intt":
			return [["魔攻加成", "%.1f" % (s.intt * 1.5)], ["当前魔攻", str(s.matk())]]
		"con":
			return [["生命加成", str(s.con * 10)], ["物防加成", "%.1f" % (s.con * 1.2)], ["暴击抵抗", "%d%%" % s.crit_res()]]
		"wis":
			return [["魔防加成", "%.1f" % (s.wis * 1.2)], ["当前魔防", str(s.mdef())]]
		"luck":
			return [["暴击加成", "%d%%" % s.luck], ["当前暴击", "%d%%" % s.crit()]]
		"atk":
			return [["基础物攻", "10"], ["当前物攻", str(s.atk())], ["公式", "10 + 力量×0.05 + 敏捷×0.1"]]
		"def":
			return [["当前物防", str(s.def())], ["公式", "体质×1.2 + 力量×0.3"]]
		"matk":
			return [["当前魔攻", str(s.matk())], ["公式", "智力×1.5 + 精神×0.5"]]
		"mdef":
			return [["当前魔防", str(s.mdef())], ["公式", "精神×1.2 + 智力×0.3"]]
		"crit":
			return [["基础暴击", "2%"], ["幸运加成", "%d%%" % s.luck], ["合计", "%d%%" % s.crit()]]
		"critRes":
			return [["当前暴击抵抗", "%d%%" % s.crit_res()], ["每点体质 +1% 暴击抵抗", ""]]
		"aspd":
			return [["当前攻速倍率", "%.2fx" % s.aspd()]]
		"moveSpeed":
			return [["当前速度", "%.1f m/s" % s.move_speed], ["敏捷加成", "%.2f" % s.speed_mult()]]
		"staminaRegen":
			return [["基础倍率", "1.00x"], ["敏捷加成", "%.2f" % (s.dex * 0.01)], ["当前倍率", "%.2fx" % s.stamina_regen()]]
		"hpRegen":
			return [["当前恢复", "%d/秒" % int(s.hp_regen)]]
		"mpRegen":
			return [["当前恢复", "%d/3秒" % int(s.mp_regen)]]
		"collisionRadius":
			return [["碰撞半径", "%.2f" % s.collision_radius]]
		"moveSpeedDetail":
			return [["当前速度", "%.1f m/s" % s.move_speed], ["敏捷加成", "%.2f" % s.speed_mult()]]
		"dodgeCooldown":
			return [["冷却时间", "%dms" % int(s.dodge_cooldown_ms)]]
		"attackRange":
			return [["当前距离", "%.0fm" % s.attack_range]]
		"knockback":
			return [["当前击退", "%.0f" % s.knockback]]
		"viewRange":
			return [["视野宽度", "%.0f°" % s.view_width]]
		_:
			return [["当前", ""]]
