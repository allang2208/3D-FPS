extends RefCounted
## Shared game shell material; mount once per panel, never per grid cell.
const Style = preload("res://ui/style.gd")
const GlassShader = preload("res://assets/ui/shaders/liquid_glass.gdshader")
static var tokens: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://ui/apple-glass-tokens.json"))

static func surface(alpha := 0.16, radius := 16) -> StyleBoxFlat:
	var box := StyleBoxFlat.new()
	box.bg_color = Color(Color(tokens.colors.accent_blue), alpha)
	box.border_color = Color(Color(tokens.colors.border), tokens.glass.border_opacity)
	box.set_border_width_all(1)
	box.set_corner_radius_all(radius)
	box.shadow_color = Color(0.015, 0.025, 0.065, 0.16)
	box.shadow_size = 4
	box.shadow_offset = Vector2(0, 3)
	return box

static func restyle_tree(node: Node) -> void:
	if node is PanelContainer or node is Panel:
		var previous: StyleBox = node.get_theme_stylebox("panel")
		var box := surface()
		for edge in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
			box.set_content_margin(edge, previous.get_content_margin(edge))
		node.add_theme_stylebox_override("panel", box)
	if node is Button:
		for state in ["normal", "hover", "pressed", "disabled"]:
			var previous: StyleBox = node.get_theme_stylebox(state)
			var box := surface(0.28 if state == "hover" else 0.36 if state == "pressed" else 0.12, 14)
			for edge in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
				box.set_content_margin(edge, previous.get_content_margin(edge))
			node.add_theme_stylebox_override(state, box)
	if node is Label and node.name != "Fallback":
		# Retain symbols and numeric roles; reduce heavy empty-slot typography.
		if node.name == "SlotTitle":
			node.add_theme_font_override("font", Style.make_font())
			node.add_theme_color_override("font_color", Color("#e0e8f5"))
	for child in node.get_children():
		restyle_tree(child)

static func mount(panel: Control) -> ColorRect:
	var glass := panel.get_node_or_null("LiquidGlass") as ColorRect
	if glass != null:
		glass.visible = true
		return glass
	glass = ColorRect.new()
	glass.name = "LiquidGlass"
	glass.mouse_filter = Control.MOUSE_FILTER_IGNORE
	glass.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var mat := ShaderMaterial.new()
	mat.shader = GlassShader
	mat.set_shader_parameter("tint", Color(tokens.colors.glass_tint))
	mat.set_shader_parameter("tint_strength", tokens.glass.tint_strength)
	mat.set_shader_parameter("corner_radius", tokens.glass.corner_radius)
	mat.set_shader_parameter("blur_lod", tokens.glass.blur_lod)
	mat.set_shader_parameter("refraction_px", tokens.glass.refraction_px)
	mat.set_shader_parameter("surface_alpha", tokens.glass.alpha)
	glass.material = mat
	panel.add_child(glass)
	panel.move_child(glass, 0)
	# Containers otherwise inset the material by the content margins, creating
	# a second frame through the title. Keep layout margins but cover the shell.
	if panel is PanelContainer or panel is Panel:
		var previous := panel.get_theme_stylebox("panel")
		var empty := StyleBoxEmpty.new()
		for side in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
			empty.set_content_margin(side, previous.get_content_margin(side))
		panel.add_theme_stylebox_override("panel", empty)
	var fit := _fit_shell.bind(weakref(panel), weakref(glass))
	panel.resized.connect(func(): fit.call_deferred())
	if panel is Container:
		panel.sort_children.connect(func(): fit.call_deferred())
	fit.call_deferred()
	glass.resized.connect(func(): mat.set_shader_parameter("node_size", glass.size))
	mat.set_shader_parameter("node_size", panel.size)
	return glass

static func _fit_shell(panel_ref: WeakRef, glass_ref: WeakRef) -> void:
	var panel = panel_ref.get_ref()
	var glass = glass_ref.get_ref()
	if panel == null or glass == null:
		return
	glass.position = Vector2.ZERO
	glass.size = panel.size

static func apply_backpack(ui: Control) -> void:
	ui._panel.add_theme_stylebox_override("panel", StyleBoxEmpty.new())
	var content: Control = ui._panel.get_node("Content")
	content.get_node("Blur").visible = false
	content.get_node("GlassTex").visible = false
	mount(content)
	# Keep the world legible around the drawer; glass does its own local sampling.
	ui._panel_root.get_node("Dim").material.set_shader_parameter("tint_amount", 0.18)
	ui._panel_root.get_node("Dim").material.set_shader_parameter("radius", 1.0)
	ui._s_equip_empty = surface(0.08, 12)
	ui._s_equip_equipped = surface(0.20, 12)
	ui._s_equip_hover = surface(0.30, 12)
	ui._s_equip_locked = surface(0.04, 12)
	ui._s_cell_empty = surface(0.035, 0)
	ui._s_cell_item = surface(0.13, 2)
	ui._s_cell_item_tile = surface(0.13, 0)
	ui._s_cell_empty_hover = surface(0.16, 0)
	ui._s_cell_item_hover = surface(0.24, 8)
	for box in [ui._s_cell_empty, ui._s_cell_item, ui._s_cell_item_tile, ui._s_cell_empty_hover, ui._s_cell_item_hover]:
		box.shadow_size = 0
		box.border_color = Color(0.8, 0.88, 1.0, 0.10)
	for cell in ui._equip_cells.values():
		cell.get_node("Content/SlotTitle").add_theme_font_override("font", Style.make_font())
