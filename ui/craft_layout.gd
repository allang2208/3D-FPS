extends Control
## 改造布局编辑器（craft-system.js 迁移）：按 craft-config.json 的 slots 坐标摆放格子，
## 绘制 slot→lineTarget 连线；编辑模式下拖格子/拖端点，保存/重置由 craft_panel 落盘。

const Style := preload("res://ui/style.gd")
const NpcConfig := preload("res://ui/npc_config.gd")

signal slot_clicked(slot_id: String)
signal layout_changed

var cfg := {}
var mods := {}
var editing := false

var _slots := {}    # slot_id -> Button
var _targets := {}  # slot_id -> Control
var _drag_slot := ""
var _drag_target := false
var _drag_offset := Vector2.ZERO

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	custom_minimum_size = Vector2(
		float(Style.npc("layout_w", 420.0)),
		float(Style.npc("layout_h", 300.0)))

func setup(config: Dictionary, item_mods: Dictionary) -> void:
	cfg = config
	mods = item_mods
	_rebuild()

func set_editing(v: bool) -> void:
	editing = v
	_rebuild()

func collect_slots() -> Array:
	return cfg.get("slots", [])

func _rebuild() -> void:
	for c in get_children():
		c.queue_free()
	_slots.clear()
	_targets.clear()
	queue_redraw()
	if cfg.is_empty():
		return
	var slots: Array = cfg.get("slots", [])
	for slot in slots:
		var sid := String(slot["id"])
		var current := String(mods.get(sid, ""))
		var opt := _find_opt(sid, current)
		var label := String(slot["name"])
		if current != "":
			label = String(opt.get("name", current))
		var btn := Button.new()
		btn.text = label
		btn.focus_mode = Control.FOCUS_NONE
		Style.style_button(btn, "caption")
		btn.custom_minimum_size = Vector2(76, 46)
		btn.position = _slot_pos(slot) - Vector2(38, 23)
		if current != "":
			btn.add_theme_color_override("font_color", Style.THEME_GOLD)
			var icon_path := NpcConfig.map_icon_path(String(opt.get("icon", "")))
			if icon_path != "":
				btn.icon = load(icon_path)
		btn.pressed.connect(slot_clicked.emit.bind(sid))
		btn.mouse_filter = Control.MOUSE_FILTER_STOP if editing else Control.MOUSE_FILTER_IGNORE
		if editing:
			btn.gui_input.connect(func(ev, id := sid): _on_drag_slot(ev, id))
		add_child(btn)
		_slots[sid] = btn
		var t := Control.new()
		t.custom_minimum_size = Vector2(14, 14)
		t.position = _target_pos(slot) - Vector2(7, 7)
		t.mouse_filter = Control.MOUSE_FILTER_STOP if editing else Control.MOUSE_FILTER_IGNORE
		if editing:
			t.gui_input.connect(func(ev, id := sid): _on_drag_target(ev, id))
		add_child(t)
		_targets[sid] = t

func _find_opt(slot_id: String, mod_id: String) -> Dictionary:
	var opts: Array = cfg.get("options", {}).get(slot_id, [])
	for o in opts:
		if String(o.get("id", "")) == mod_id:
			return o
	return {}

func _slot_pos(slot: Dictionary) -> Vector2:
	return Vector2(float(slot.get("x", 0.5)) * size.x, float(slot.get("y", 0.5)) * size.y)

func _target_pos(slot: Dictionary) -> Vector2:
	var lt: Dictionary = slot.get("lineTarget", {})
	return Vector2(float(lt.get("x", 0.5)) * size.x, float(lt.get("y", 0.5)) * size.y)

func _on_drag_slot(event: InputEvent, sid: String) -> void:
	if not editing:
		return
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		_drag_slot = sid
		_drag_target = false
		_drag_offset = event.position
	elif event is InputEventMouseMotion and _drag_slot == sid and not _drag_target:
		var slot := _find_slot(sid)
		if slot.is_empty():
			return
		var new_x := clampf((event.position.x - _drag_offset.x + _slot_pos(slot).x) / size.x, 0.0, 1.0)
		var new_y := clampf((event.position.y - _drag_offset.y + _slot_pos(slot).y) / size.y, 0.0, 1.0)
		slot["x"] = new_x
		slot["y"] = new_y
		if _slots.has(sid):
			_slots[sid].position = Vector2(new_x * size.x, new_y * size.y) - Vector2(38, 23)
		queue_redraw()
	elif event is InputEventMouseButton and not event.pressed:
		_drag_slot = ""
		if event.button_index == MOUSE_BUTTON_LEFT:
			layout_changed.emit()

func _on_drag_target(event: InputEvent, sid: String) -> void:
	if not editing:
		return
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		_drag_slot = sid
		_drag_target = true
		_drag_offset = event.position
	elif event is InputEventMouseMotion and _drag_slot == sid and _drag_target:
		var slot := _find_slot(sid)
		if slot.is_empty():
			return
		var lt: Dictionary = slot.get("lineTarget", {})
		var cur := _target_pos(slot)
		var new_x := clampf((event.position.x - _drag_offset.x + cur.x) / size.x, 0.0, 1.0)
		var new_y := clampf((event.position.y - _drag_offset.y + cur.y) / size.y, 0.0, 1.0)
		lt["x"] = new_x
		lt["y"] = new_y
		if _targets.has(sid):
			_targets[sid].position = Vector2(new_x * size.x, new_y * size.y) - Vector2(7, 7)
		queue_redraw()
	elif event is InputEventMouseButton and not event.pressed:
		_drag_slot = ""
		if event.button_index == MOUSE_BUTTON_LEFT:
			layout_changed.emit()

func _find_slot(sid: String) -> Dictionary:
	for slot in cfg.get("slots", []):
		if String(slot.get("id", "")) == sid:
			return slot
	return {}

func _draw() -> void:
	if cfg.is_empty():
		return
	var line_color := Style.THEME_GRAY_LIGHT
	line_color.a = 0.55
	for slot in cfg.get("slots", []):
		var a := _slot_pos(slot)
		var b := _target_pos(slot)
		draw_dashed_line(a, b, line_color, 2.0, 4.0)
		if editing:
			draw_circle(b, 6.0, Style.THEME_GOLD)
			draw_arc(b, 9.0, 0.0, TAU, 20, Style.THEME_GOLD, 1.5)
