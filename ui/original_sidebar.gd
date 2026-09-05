extends Control
## Original PNGs and CSS geometry: 74px hit area, 68px artwork, 25px spacing.
const Style := preload("res://ui/style.gd")
signal selected(tab: String)
const ITEMS := [
	["status", "Caps", "人物状态", "status"],
	["skills", "K", "技能栏", "skill"],
	["inventory", "Tab", "背包", "equip"],
	["codex", "U", "图鉴栏", "codex"],
	["quest", "L", "任务档案", "quest"],
	["world_switch", "O", "世界", "world"],
	["party", "P", "队员管理", "party"],
	["technology_tree", "Y", "科技树", "technology"]]
func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var menu := VBoxContainer.new()
	menu.name = "Menu"
	menu.mouse_filter = Control.MOUSE_FILTER_IGNORE
	menu.add_theme_constant_override("separation", 25)
	add_child(menu)
	for spec in ITEMS:
		var button := Button.new()
		button.name = spec[0]
		button.custom_minimum_size = Vector2(74, 74)
		button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		button.tooltip_text = "%s (%s)" % [spec[2], spec[1]]
		for state in ["normal", "hover", "pressed", "focus"]:
			button.add_theme_stylebox_override(state, StyleBoxEmpty.new())
		menu.add_child(button)
		var art := TextureRect.new()
		art.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
		art.texture = load("res://assets/original_ui/assets/ui/icons/%s.png" % spec[0])
		art.position = Vector2(3, 3)
		art.custom_minimum_size = Vector2(68, 68)
		art.pivot_offset = Vector2(34, 34)
		art.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		art.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		art.mouse_filter = Control.MOUSE_FILTER_IGNORE
		button.add_child(art)
		var key := Label.new()
		key.text = spec[1]
		key.add_theme_font_override("font", Style.make_mono_font(700))
		key.add_theme_font_size_override("font_size", 20)
		key.add_theme_color_override("font_color", Color("#c4d3da"))
		key.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.88))
		key.add_theme_constant_override("shadow_offset_y", 1)
		key.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
		key.grow_horizontal = Control.GROW_DIRECTION_BEGIN
		key.grow_vertical = Control.GROW_DIRECTION_BEGIN
		key.offset_right = -4
		key.offset_bottom = -2
		key.mouse_filter = Control.MOUSE_FILTER_IGNORE
		button.add_child(key)
		var label := Label.new()
		label.text = spec[2]
		label.add_theme_font_override("font", Style.make_font())
		label.add_theme_font_size_override("font_size", 11)
		label.add_theme_color_override("font_color", Color("#c4d3da"))
		label.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.88))
		label.add_theme_constant_override("shadow_offset_y", 1)
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.position = Vector2(-12, 78)
		label.size = Vector2(98, 16)
		label.mouse_filter = Control.MOUSE_FILTER_IGNORE
		button.add_child(label)
		if spec[3] == "world":
			key.visible = false
			art.modulate.a = 0.48
			var gray := ShaderMaterial.new()
			gray.shader = Shader.new()
			gray.shader.code = "shader_type canvas_item; void fragment() { vec4 c = texture(TEXTURE, UV) * COLOR; c.rgb = mix(c.rgb, vec3(dot(c.rgb, vec3(0.299, 0.587, 0.114))), 0.8); COLOR = c; }"
			art.material = gray
			var lock := Label.new()
			lock.text = "🔒"
			lock.material = gray
			lock.position = Vector2(61, 57)
			lock.add_theme_font_size_override("font_size", 16)
			lock.mouse_filter = Control.MOUSE_FILTER_IGNORE
			button.add_child(lock)
			button.tooltip_text = "世界功能尚未接入"
		button.pressed.connect(func(): selected.emit(spec[3]))
		button.mouse_entered.connect(func(): art.scale = Vector2.ONE * 1.25; art.modulate = Color(1.14, 1.14, 1.14))
		button.mouse_exited.connect(func(): art.scale = Vector2.ONE; art.modulate = Color(1, 1, 1, 0.48 if spec[3] == "world" else 1.0))
	get_viewport().size_changed.connect(_layout)
	_layout()
func _layout() -> void:
	var view := get_viewport_rect().size
	var menu := get_node("Menu") as VBoxContainer
	var factor := minf(1.0, (view.y - 32) / 787.0)
	menu.scale = Vector2.ONE * factor
	menu.position = Vector2(view.x - 12 - 74 * factor, (view.y - 767 * factor) / 2.0)
func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		var target: String = {KEY_U:"codex", KEY_L:"quest", KEY_O:"world", KEY_P:"party", KEY_Y:"technology"}.get(event.keycode, "")
		if not target.is_empty() and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
			get_viewport().set_input_as_handled()
			selected.emit(target)
