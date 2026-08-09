extends Panel
## 拖放接收槽（旧版 drag-drop-manager 迁移）：接收 item_cell 拖出的 npc_item 数据。
## 用法：var s := load("res://ui/drop_slot.gd").new(); s.accepted_types = [...]; s.dropped.connect(...)

const Style := preload("res://ui/style.gd")

signal dropped(data: Dictionary)

var accepted_types: Array = ["npc_item"]
var _dragging := false

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP

func _notification(what: int) -> void:
	if what == NOTIFICATION_DRAG_BEGIN:
		_dragging = true
		queue_redraw()
	elif what == NOTIFICATION_DRAG_END:
		_dragging = false
		queue_redraw()

func _can_drop_data(_at_position: Vector2, data) -> bool:
	return data is Dictionary and accepted_types.has(String(data.get("type", "")))

func _drop_data(_at_position: Vector2, data) -> void:
	if _can_drop_data(_at_position, data):
		dropped.emit(data)

func _draw() -> void:
	if _dragging:
		draw_style_box(Style.make_style(
			Color(Style.THEME_GOLD, 0.12), Style.THEME_GOLD, Style.RADIUS_MD, 2), Rect2(Vector2.ZERO, size))
