extends Control
## 技能体系页（新栏目，与背包/装备/状态完全独立）：
## Q/E/X/C 技能槽 + 特殊攻击位，技能本体未移植，先占位显示键位与说明。

const Style := preload("res://ui/style.gd")
const SkillBarScript := preload("res://ui/skillbar.gd")

const SLOT_KEYS := ["Q", "E", "X", "C"]

var skillbar: SkillBarScript

var _slot_names := {}
var _slot_cd := {}

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE

func setup(sb: SkillBarScript) -> void:
	skillbar = sb
	if skillbar != null:
		skillbar.changed.connect(_refresh)
	_build()
	_refresh()

func _build() -> void:
	var margin := MarginContainer.new()
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_theme_constant_override("margin_left", 20)
	margin.add_theme_constant_override("margin_right", 20)
	margin.add_theme_constant_override("margin_top", 12)
	margin.add_theme_constant_override("margin_bottom", 12)
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(margin)
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 12)
	margin.add_child(vbox)
	var note := Label.new()
	note.text = "技能体系未移植——Q/E/X/C 槽位已就绪，技能数据后续接入"
	note.add_theme_font_size_override("font_size", Style.font_size("body"))
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

func _refresh() -> void:
	if skillbar == null:
		return
	for i in SLOT_KEYS.size():
		var id := skillbar.resolve(i)
		var name_lbl: Label = _slot_names.get(i)
		var cd_lbl: Label = _slot_cd.get(i)
		if id == "":
			name_lbl.text = "未移植"
			cd_lbl.text = ""
		else:
			var def: Dictionary = skillbar.skills.get(id, {})
			name_lbl.text = String(def.get("name", id))
			var cd := skillbar.get_cooldown(id)
			cd_lbl.text = "%.1f秒" % (cd / 1000.0) if cd > 0.0 else ""
