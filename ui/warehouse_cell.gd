extends "res://ui/item_cell.gd"
signal activated(cell: Panel)

func _ready() -> void:
	super._ready()
	focus_mode = Control.FOCUS_ALL
	var reference := preload("res://ui/backpack_reference_style.gd")
	var normal := Style.make_surface(0.78 if not item.is_empty() else 0.40, 12, 0, 0)
	add_theme_stylebox_override("panel", normal)
	mouse_entered.connect(func(): add_theme_stylebox_override("panel", Style.make_style(Style.COLOR_HUD_SLOT_HOVER, Style.COLOR_DRAG_OVER_BORDER, 12, 1)))
	mouse_exited.connect(func(): add_theme_stylebox_override("panel", normal))
	if item.is_empty():
		return
	_badges.hide()
	preload("res://ui/backpack_reference_style.gd").update_item_badges(self, item)
	_name_lbl.offset_top = -38
	_name_lbl.offset_bottom = -16
	# 原仓库 flex 居中：图标和名称作为一组，而非 NPC 格子的左上固定坐标。
	var row := HBoxContainer.new()
	row.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	row.offset_left = 34 if int(item.get("enhanceLevel", 0)) > 0 else 20
	row.offset_right = -reference.name_right_inset(self)
	row.clip_contents = true
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 0)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(row)
	for child in [_icon, _icon_fallback, _name_lbl]:
		child.reparent(row)
		child.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
		child.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_icon.visible = _icon.texture != null
	_icon.custom_minimum_size = Vector2(32, 32)
	_name_lbl.custom_minimum_size.x = minf(108, _name_lbl.get_theme_font("font").get_string_size(_name_lbl.text, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x)
	_name_lbl.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	reference.item_shadow(_name_lbl)
	if _stack_lbl != null:
		_stack_lbl.text = str(item.get("stack", 1))
		_stack_lbl.add_theme_font_size_override("font_size", 12)
		_stack_lbl.add_theme_color_override("font_color", Style.COLOR_TEXT)
		reference.item_shadow(_stack_lbl, true)

func _on_gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_RIGHT or (event.button_index == MOUSE_BUTTON_LEFT and event.double_click):
			_pressed = false
			if not item.is_empty():
				activated.emit(self)
			accept_event()
			return
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_ENTER:
		if not item.is_empty():
			activated.emit(self)
		accept_event()
		return
	super._on_gui_input(event)

func _can_drop_data(_at_position: Vector2, data) -> bool:
	return data is Dictionary and data.get("type", "") in ["equip", "npc_item", "backpack"] and data.get("source", "backpack") in ["warehouse", "backpack"]

func _get_drag_data(_at_position: Vector2) -> Variant:
	_pressed = false
	if item.is_empty():
		return null
	set_drag_preview(preload("res://ui/item_drag_preview.gd").make(item))
	modulate.a = 0.3
	return {"type": "npc_item", "source": "warehouse", "slot": int(get_meta("inventory_slot", -1)), "item": item.duplicate(true)}

func _notification(what: int) -> void:
	if what == NOTIFICATION_DRAG_END:
		modulate.a = 1.0
