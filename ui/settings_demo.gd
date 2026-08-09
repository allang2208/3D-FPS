extends Control
## 设置面板 Demo（通用组件 + 金白主题展示；独立场景，Godot F6 运行测试）
## 入口：scenes/ui/settings_demo.tscn
## 覆盖：tabs / switch / checkbox / slider / input / select / context-menu / nav / command-palette

const Style := preload("res://ui/style.gd")
const Icons := preload("res://ui/icons.gd")
const Tabs := preload("res://ui/tabs.gd")
const Switch := preload("res://ui/switch.gd")
const Checkbox := preload("res://ui/checkbox.gd")
const SliderC := preload("res://ui/slider.gd")
const InputC := preload("res://ui/input.gd")
const SelectC := preload("res://ui/select.gd")
const ContextMenu := preload("res://ui/context_menu.gd")
const CommandPalette := preload("res://ui/command_palette.gd")

var _content: VBoxContainer
var _hint: Label

func _ready() -> void:
	call_deferred("_build")

func _build() -> void:
	var bg := ColorRect.new()
	bg.color = Style.THEME_BG
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)

	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel", Style.make_panel_style())
	panel.custom_minimum_size = Vector2(620, 0)
	center.add_child(panel)

	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", Style.spacing("element_gap"))
	panel.add_child(root)

	# 标题行（图标 + 标题 + 主题标记）
	var title_row := HBoxContainer.new()
	title_row.add_theme_constant_override("separation", Style.spacing("element_gap"))
	root.add_child(title_row)
	var icon := TextureRect.new()
	icon.custom_minimum_size = Vector2(28, 28)
	icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	Icons.apply_icon(icon, "settings", Style.THEME_GOLD)
	title_row.add_child(icon)
	var title := Label.new()
	title.text = "设置"
	title.add_theme_font_size_override("font_size", Style.font_size("h2"))
	title.add_theme_color_override("font_color", Style.THEME_WHITE)
	title_row.add_child(title)
	_hint = Label.new()
	_hint.text = "金白深灰主题 · Ctrl+K 命令面板"
	_hint.add_theme_font_size_override("font_size", Style.font_size("caption"))
	_hint.add_theme_color_override("font_color", Style.THEME_GOLD)
	_hint.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	title_row.add_child(_hint)

	# 分页签
	var tabs := Tabs.new()
	root.add_child(tabs)
	tabs.add_tab("画面")
	tabs.add_tab("音频")
	tabs.add_tab("游戏")

	# 内容区
	_content = VBoxContainer.new()
	_content.add_theme_constant_override("separation", Style.spacing("element_gap"))
	root.add_child(_content)
	_build_video()

	# 分隔线 + 底部按钮
	var sep := HSeparator.new()
	sep.add_theme_stylebox_override("separator",
		Style.make_style(Color(Style.THEME_GRAY_MID, 1.0), Color(Style.THEME_GRAY_MID, 1.0), 0, 0))
	root.add_child(sep)
	var bottom := HBoxContainer.new()
	bottom.add_theme_constant_override("separation", Style.spacing("element_gap"))
	bottom.alignment = BoxContainer.ALIGNMENT_END
	root.add_child(bottom)
	var reset_btn := Button.new()
	reset_btn.text = "恢复默认"
	Style.style_button(reset_btn)
	reset_btn.pressed.connect(func() -> void: _hint.text = "已恢复默认（演示）")
	bottom.add_child(reset_btn)
	var apply_btn := Button.new()
	apply_btn.text = "应用"
	apply_btn.add_theme_stylebox_override("normal", Style.make_style(Style.THEME_GOLD, Style.THEME_GOLD, 6, 1))
	apply_btn.add_theme_color_override("font_color", Color(Style.THEME_BG, 1.0))
	apply_btn.add_theme_color_override("font_hover_color", Color(Style.THEME_BG, 1.0))
	apply_btn.pressed.connect(func() -> void: _hint.text = "已应用（演示）")
	bottom.add_child(apply_btn)

	tabs.tab_changed.connect(_on_tab)

	# 右键菜单（"游戏"页里的演示按钮触发）
	var cm := ContextMenu.new()
	cm.id_pressed.connect(func(id: int) -> void: _hint.text = "菜单选择：%d" % id)
	add_child(cm)
	_cm = cm

	# 命令面板
	var cp := CommandPalette.new()
	cp.command_selected.connect(func(id: String) -> void: _hint.text = "命令：" + id)
	add_child(cp)
	cp.register("open_settings", "打开设置")
	cp.register("switch_theme", "切换主题")
	cp.register("quit_game", "退出游戏")

var _cm: ContextMenu

func _on_tab(idx: int) -> void:
	for c in _content.get_children():
		_content.remove_child(c)
		c.free()
	match idx:
		0: _build_video()
		1: _build_audio()
		2: _build_game()

func _row(label_text: String) -> Label:
	var l := Label.new()
	l.text = label_text
	l.custom_minimum_size = Vector2(150, 0)
	l.add_theme_font_size_override("font_size", Style.font_size("body"))
	l.add_theme_color_override("font_color", Style.THEME_GRAY_LIGHT)
	return l

func _build_video() -> void:
	var res := SelectC.new()
	_content.add_child(res)
	res.setup("分辨率")
	res.add_item("1920×1080", 0)
	res.add_item("2560×1440", 1)
	res.select(0)
	var preset := SelectC.new()
	_content.add_child(preset)
	preset.setup("画质预设")
	preset.add_item("低", 0)
	preset.add_item("中", 1)
	preset.add_item("高", 2)
	preset.add_item("极高", 3)
	preset.select(2)
	_content.add_child(_switch_row("垂直同步", true))
	_content.add_child(_switch_row("动态模糊", false))
	var fov := SliderC.new()
	fov.value_changed.connect(func(v: float) -> void: _hint.text = "视野 %.0f°" % v)
	# 滑杆带标签行
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", Style.spacing("element_gap"))
	row.add_child(_row("视野 (FOV)"))
	row.add_child(fov)
	_content.add_child(row)
	fov.setup(50.0, 120.0, 1.0, 90.0)

func _build_audio() -> void:
	for spec in [["主音量", 70.0], ["音乐", 50.0], ["音效", 80.0]]:
		var sl := SliderC.new()
		sl.value_changed.connect(func(v: float) -> void: _hint.text = "%s %.0f%%" % [spec[0], v])
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", Style.spacing("element_gap"))
		row.add_child(_row(spec[0]))
		row.add_child(sl)
		_content.add_child(row)
		sl.setup(0.0, 100.0, 1.0, spec[1])
	_content.add_child(_switch_row("立体声", true))

func _build_game() -> void:
	var name_in := InputC.new()
	_content.add_child(name_in)
	name_in.setup("玩家名", "输入名称")
	name_in.text_submitted.connect(func(t: String) -> void: _hint.text = "玩家名：" + t)
	_content.add_child(_check_row("显示伤害数字", true))
	_content.add_child(_check_row("显示帧数", false))
	_content.add_child(_switch_row("自动拾取", true))
	# 右键菜单演示
	var cm_btn := Button.new()
	cm_btn.text = "右键点击弹出菜单"
	Style.style_button(cm_btn)
	cm_btn.custom_minimum_size = Vector2(0, 32)
	cm_btn.gui_input.connect(func(event: InputEvent) -> void:
		if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_RIGHT:
			_cm.open_at(get_viewport().get_mouse_position(),
				[{"label": "使用", "id": 1}, {"separator": true}, {"label": "丢弃", "id": 2}]))
	_content.add_child(cm_btn)

func _switch_row(text: String, on: bool) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", Style.spacing("element_gap"))
	row.add_child(_row(text))
	var sw := Switch.new()
	row.add_child(sw)
	sw.set_on(on)
	sw.toggled.connect(func(v: bool) -> void: _hint.text = "%s：%s" % [text, "开" if v else "关"])
	return row

func _check_row(text: String, on: bool) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", Style.spacing("element_gap"))
	var cb := Checkbox.new()
	row.add_child(cb)
	cb.setup(text)
	cb.set_on(on)
	cb.toggled.connect(func(v: bool) -> void: _hint.text = "%s：%s" % [text, "开" if v else "关"])
	return row
