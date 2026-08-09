extends Control
## 命令面板（shadcn command 简化版）：Ctrl+K 开/关，搜索过滤命令列表。

signal command_selected(id: String)

const Style := preload("res://ui/style.gd")

var _commands: Array[Dictionary] = []
var _search: LineEdit
var _list: VBoxContainer
var _panel: PanelContainer
var _overlay: ColorRect
var _built := false

func _ready() -> void:
	_ensure_built()

func _ensure_built() -> void:
	if _built:
		return
	_built = true
	visible = false
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	_overlay = ColorRect.new()
	_overlay.color = Color(0, 0, 0, 0.55)
	_overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	_overlay.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(_overlay)
	_panel = PanelContainer.new()
	_panel.add_theme_stylebox_override("panel", Style.make_panel_style())
	_panel.custom_minimum_size = Vector2(460, 0)
	_panel.set_anchors_preset(Control.PRESET_CENTER)
	add_child(_panel)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", Style.spacing("element_gap"))
	_panel.add_child(v)
	_search = LineEdit.new()
	_search.placeholder_text = "输入命令… (Esc 关闭)"
	_search.custom_minimum_size = Vector2(0, 34)
	_search.add_theme_stylebox_override("normal",
		Style.make_style(Style.THEME_BG, Style.THEME_GOLD, Style.RADIUS_SM, 1))
	_search.add_theme_stylebox_override("focus",
		Style.make_style(Style.THEME_BG, Style.THEME_GOLD, Style.RADIUS_SM, 1))
	_search.add_theme_color_override("font_color", Style.THEME_WHITE)
	_search.add_theme_color_override("font_placeholder_color", Style.THEME_GRAY_LIGHT)
	_search.add_theme_font_size_override("font_size", Style.font_size("body"))
	_search.text_changed.connect(func(_t: String) -> void: _refresh())
	v.add_child(_search)
	_list = VBoxContainer.new()
	_list.add_theme_constant_override("separation", 2)
	v.add_child(_list)
	set_process_unhandled_input(true)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_K and event.ctrl_pressed:
			toggle()
			get_viewport().set_input_as_handled()
		elif event.keycode == KEY_ESCAPE and visible:
			close()
			get_viewport().set_input_as_handled()

func register(id: String, label: String) -> void:
	_ensure_built()
	_commands.append({"id": id, "label": label})
	_refresh()

func clear_commands() -> void:
	_ensure_built()
	_commands.clear()
	_refresh()

func toggle() -> void:
	if visible:
		close()
	else:
		open()

func open() -> void:
	_ensure_built()
	visible = true
	_search.clear()
	_refresh()
	_search.grab_focus()

func close() -> void:
	_ensure_built()
	visible = false

func _refresh() -> void:
	for c in _list.get_children():
		_list.remove_child(c)
		c.free()
	var q := _search.text.strip_edges().to_lower()
	for cmd in _commands:
		if not q.is_empty() and not str(cmd.label).to_lower().contains(q):
			continue
		var b := Button.new()
		b.text = str(cmd.label)
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.custom_minimum_size = Vector2(0, 30)
		Style.style_button(b, "body")
		b.add_theme_font_size_override("font_size", Style.font_size("body"))
		b.pressed.connect(func() -> void:
			close()
			command_selected.emit(str(cmd.id)))
		_list.add_child(b)
