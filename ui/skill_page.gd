extends Control
## 技能体系页（新栏目，与背包/装备/状态完全独立）：
## Q/E/X/C 技能槽 + 特殊攻击位 + 全技能修炼列表（等级/经验，skill_progress 驱动）。

const Style := preload("res://ui/style.gd")
const SkillBarScript := preload("res://ui/skillbar.gd")

const SLOT_KEYS := ["Q", "E", "X", "C"]

var skillbar: SkillBarScript
var _progress
var _db

var _slot_names := {}
var _slot_cd := {}
var _slot_icons := {}
var _train_rows := {}  # skill_id -> {name:Label, lv:Label, bar:ProgressBar}
var _vbox: VBoxContainer
var _tex_cache := {}

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE

func setup(sb: SkillBarScript) -> void:
	skillbar = sb
	if skillbar != null:
		skillbar.changed.connect(_refresh)
	_build()
	_refresh()

func set_progress(p) -> void:
	_progress = p
	if _progress != null and not _progress.changed.is_connected(_refresh):
		_progress.changed.connect(_refresh)

func set_db(db) -> void:
	_db = db
	_build_train_list()
	_refresh()

func _build() -> void:
	var scroll := Style.make_scroll_container()
	scroll.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(scroll)
	var margin := MarginContainer.new()
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_theme_constant_override("margin_left", 20)
	margin.add_theme_constant_override("margin_right", 20)
	margin.add_theme_constant_override("margin_top", 12)
	margin.add_theme_constant_override("margin_bottom", 12)
	margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(margin)
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 12)
	margin.add_child(vbox)
	_vbox = vbox
	var note := Label.new()
	note.text = "按 Q / E / X / C 释放技能 · 二段式技能首次凝聚、再次投掷 · 冷却与法杖门槛自动判定"
	note.add_theme_font_size_override("font_size", Style.font_size("caption"))
	note.add_theme_color_override("font_color", Style.COLOR_DIM_TEXT)
	vbox.add_child(note)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	vbox.add_child(row)
	for i in SLOT_KEYS.size():
		var cell := PanelContainer.new()
		cell.custom_minimum_size = Vector2(120, 110)
		cell.add_theme_stylebox_override("panel", Style.make_style(Style.COLOR_SKILL_SLOT_BG, Style.COLOR_SKILL_SLOT_BORDER, Style.RADIUS_SM, 2))
		var content := VBoxContainer.new()
		content.alignment = BoxContainer.ALIGNMENT_CENTER
		content.add_theme_constant_override("separation", 6)
		cell.add_child(content)
		var icon := TextureRect.new()
		icon.name = "Icon"
		icon.custom_minimum_size = Vector2(44, 44)
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		content.add_child(icon)
		var key_lbl := Label.new()
		key_lbl.text = SLOT_KEYS[i]
		key_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		key_lbl.add_theme_font_size_override("font_size", Style.font_size("h2"))
		key_lbl.add_theme_font_override("font", Style.make_font(700))
		key_lbl.add_theme_color_override("font_color", Style.COLOR_KEY_HINT)
		content.add_child(key_lbl)
		var name_lbl := Label.new()
		name_lbl.name = "Name"
		name_lbl.text = "未移植"
		name_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		name_lbl.add_theme_font_size_override("font_size", Style.font_size("caption"))
		name_lbl.add_theme_color_override("font_color", Style.COLOR_DIM_TEXT)
		content.add_child(name_lbl)
		var cd_lbl := Label.new()
		cd_lbl.name = "CD"
		cd_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		cd_lbl.add_theme_font_size_override("font_size", Style.font_size("caption"))
		cd_lbl.add_theme_color_override("font_color", Style.COLOR_ZERO_TEXT)
		content.add_child(cd_lbl)
		row.add_child(cell)
		_slot_names[i] = name_lbl
		_slot_cd[i] = cd_lbl
		_slot_icons[i] = icon
	# 特殊攻击位（旧版右击，占用键位待定）
	var special := PanelContainer.new()
	special.custom_minimum_size = Vector2(120, 110)
	special.add_theme_stylebox_override("panel", Style.make_style(Style.COLOR_SKILL_SLOT_BG, Style.THEME_MP_BLUE, Style.RADIUS_SM, 2))
	var sp_content := VBoxContainer.new()
	sp_content.alignment = BoxContainer.ALIGNMENT_CENTER
	sp_content.add_theme_constant_override("separation", 6)
	special.add_child(sp_content)
	var sp_key := Label.new()
	sp_key.text = "右击"
	sp_key.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	sp_key.add_theme_font_size_override("font_size", Style.font_size("label"))
	sp_key.add_theme_color_override("font_color", Style.COLOR_KEY_HINT)
	sp_content.add_child(sp_key)
	var sp_name := Label.new()
	sp_name.text = "特殊攻击"
	sp_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	sp_name.add_theme_font_size_override("font_size", Style.font_size("caption"))
	sp_name.add_theme_color_override("font_color", Style.COLOR_DIM_TEXT)
	sp_content.add_child(sp_name)
	row.add_child(special)

## 修炼列表：全部 active 技能（旧版技能面板修炼入口）
func _build_train_list() -> void:
	if _db == null:
		return
	var list := ScrollContainer.new()
	list.custom_minimum_size = Vector2(0, 280)
	list.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var inner := VBoxContainer.new()
	inner.add_theme_constant_override("separation", 6)
	list.add_child(inner)
	_vbox.add_child(list)
	var title := Label.new()
	title.text = "技能修炼（命中/击杀获得经验，经验满自动升级）"
	title.add_theme_font_size_override("font_size", Style.font_size("label"))
	title.add_theme_color_override("font_color", Style.COLOR_TITLE_TEXT)
	inner.add_child(title)
	for id in _db.skills.keys():
		var def: Dictionary = _db.get_def(id)
		var tags: Array = def.get("tags", [])
		var is_active := false
		for tag in tags:
			if String(tag.get("type", "")) == "active":
				is_active = true
				break
		if not is_active:
			continue
		_train_rows[id] = _build_train_row(inner, String(def.get("name", id)))

func _build_train_row(parent: Node, name: String) -> Dictionary:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 2)
	parent.add_child(box)
	var top := HBoxContainer.new()
	box.add_child(top)
	var icon := TextureRect.new()
	icon.custom_minimum_size = Vector2(26, 26)
	icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	top.add_child(icon)
	var name_lbl := Label.new()
	name_lbl.text = name
	name_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	name_lbl.add_theme_font_size_override("font_size", Style.font_size("body"))
	name_lbl.add_theme_color_override("font_color", Style.COLOR_TEXT)
	top.add_child(name_lbl)
	var lv_lbl := Label.new()
	lv_lbl.text = "Lv.1"
	lv_lbl.add_theme_font_size_override("font_size", Style.font_size("caption"))
	lv_lbl.add_theme_color_override("font_color", Style.THEME_GOLD)
	top.add_child(lv_lbl)
	var bar := ProgressBar.new()
	bar.custom_minimum_size = Vector2(0, 12)
	bar.show_percentage = false
	bar.add_theme_stylebox_override("background", Style.make_style(Style.COLOR_SLOT_BG, Color.TRANSPARENT, Style.RADIUS_SM, 1))
	bar.add_theme_stylebox_override("fill", Style.make_style(Style.THEME_MP_BLUE, Color.TRANSPARENT, Style.RADIUS_SM, 1))
	box.add_child(bar)
	return {"name": name_lbl, "lv": lv_lbl, "bar": bar, "icon": icon}

func _refresh() -> void:
	if skillbar == null:
		return
	for i in SLOT_KEYS.size():
		var id := skillbar.resolve(i)
		var name_lbl: Label = _slot_names.get(i)
		var cd_lbl: Label = _slot_cd.get(i)
		var icon: TextureRect = _slot_icons.get(i)
		if id == "":
			name_lbl.text = "未移植"
			cd_lbl.text = ""
			icon.texture = null
		else:
			var def: Dictionary = skillbar.skills.get(id, {})
			name_lbl.text = String(def.get("name", id))
			icon.texture = _icon_tex(String(def.get("iconImage", "")))
			var cd := skillbar.get_cooldown(id)
			cd_lbl.text = "%.1f秒" % (cd / 1000.0) if cd > 0.0 else ""
	# 修炼列表刷新
	if _progress != null:
		for id in _train_rows.keys():
			var row: Dictionary = _train_rows[id]
			var def2: Dictionary = _db.get_def(id) if _db != null else {}
			(row.icon as TextureRect).texture = _icon_tex(String(def2.get("iconImage", "")))
			var lv: int = _progress.get_level(id)
			var exp: float = _progress.get_exp(id)
			var max_exp: float = _progress.get_max_exp(id)
			(row.lv as Label).text = "Lv.%d" % lv
			(row.bar as ProgressBar).max_value = maxf(1.0, max_exp)
			(row.bar as ProgressBar).value = clampf(exp, 0.0, max_exp)

func _icon_tex(path: String) -> Texture2D:
	if path == "":
		return null
	if not _tex_cache.has(path):
		var res := load(path)
		_tex_cache[path] = res if res is Texture2D else null
	return _tex_cache[path]
