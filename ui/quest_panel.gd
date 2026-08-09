extends "res://ui/npc_panel.gd"
## 任务日志面板（quest-system.js 迁移）：任务列表 + 详情 + 接受/传送。
## 进度存于本组件（explore_rift_1 对齐旧版）；传送通过 teleport_requested 交给 main 处理。

const NpcConfig := preload("res://ui/npc_config.gd")

signal teleport_requested(quest_id: String)

var _quests := {}
var _selected := "explore_rift_1"

var _list_box: VBoxContainer
var _detail_label: RichTextLabel
var _accept_btn: Button
var _teleport_btn: Button

func setup(_db: RefCounted, _backpack: RefCounted, _equipment: RefCounted, _economy: RefCounted) -> void:
	_quests = NpcConfig.QUESTS.duplicate(true)

func _build_body() -> void:
	var h := HBoxContainer.new()
	h.size_flags_vertical = Control.SIZE_EXPAND_FILL
	h.add_theme_constant_override("separation", Style.spacing("element_gap"))
	body.add_child(h)

	var list_col := VBoxContainer.new()
	list_col.custom_minimum_size = Vector2(240, 0)
	list_col.add_theme_constant_override("separation", Style.spacing("grid"))
	h.add_child(list_col)
	list_col.add_child(_make_section_title("📜 任务列表"))
	var list_scroll := ScrollContainer.new()
	list_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	list_col.add_child(list_scroll)
	_list_box = VBoxContainer.new()
	_list_box.add_theme_constant_override("separation", Style.spacing("grid"))
	list_scroll.add_child(_list_box)

	var detail_col := VBoxContainer.new()
	detail_col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	detail_col.add_theme_constant_override("separation", Style.spacing("element_gap"))
	h.add_child(detail_col)
	_detail_label = RichTextLabel.new()
	_detail_label.bbcode_enabled = true
	_detail_label.fit_content = false
	_detail_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_detail_label.custom_minimum_size = Vector2(500, 300)
	_detail_label.theme = Style.make_theme()
	_detail_label.add_theme_font_override("normal_font", Style.make_font(Style.font_weight("regular")))
	_detail_label.add_theme_color_override("default_color", Style.THEME_WHITE)
	_detail_label.add_theme_font_size_override("normal_font_size", Style.font_size("body"))
	detail_col.add_child(_detail_label)

	var actions := HBoxContainer.new()
	actions.add_theme_constant_override("separation", Style.spacing("element_gap"))
	detail_col.add_child(actions)
	_accept_btn = _make_button("接受任务")
	_accept_btn.pressed.connect(_accept)
	actions.add_child(_accept_btn)
	_teleport_btn = _make_button("传送至任务地点")
	_teleport_btn.pressed.connect(func() -> void: teleport_requested.emit(_selected))
	actions.add_child(_teleport_btn)

func _refresh() -> void:
	_rebuild_list()
	_render_detail()

func _rebuild_list() -> void:
	for c in _list_box.get_children():
		c.queue_free()
	for qid in _quests:
		var q: Dictionary = _quests[qid]
		var b := _make_button("%s（%s）" % [String(q.get("name", "?")), String(q.get("type", ""))], "body")
		b.custom_minimum_size = Vector2(220, 40)
		if String(qid) == _selected:
			b.add_theme_color_override("font_color", Style.THEME_GOLD)
		b.pressed.connect(_select.bind(String(qid)))
		_list_box.add_child(b)

func _render_detail() -> void:
	var q: Dictionary = _quests.get(_selected, {})
	if q.is_empty():
		_detail_label.text = "暂无任务"
		return
	var lines := "[b]%s[/b]\n%s\n\n" % [String(q.get("name", "")), String(q.get("desc", ""))]
	lines += "具体目标：\n"
	for obj in q.get("objectives", []):
		lines += "  • %s (%d/%d)\n" % [String(obj["text"]), int(obj["current"]), int(obj["target"])]
	lines += "\n任务奖励：\n"
	for r in q.get("rewards", []):
		lines += "  – %s\n" % String(r["text"])
	var status := "未接受"
	if bool(q.get("completed", false)):
		status = "已完成"
	elif bool(q.get("accepted", false)):
		status = "进行中"
	lines += "\n状态：%s" % status
	_detail_label.text = lines
	_accept_btn.visible = not bool(q.get("accepted", false)) and not bool(q.get("completed", false))
	_teleport_btn.visible = bool(q.get("accepted", false)) and not bool(q.get("completed", false))

func _select(qid: String) -> void:
	_selected = qid
	_refresh()

func _accept() -> void:
	var q: Dictionary = _quests.get(_selected, {})
	if q.is_empty():
		return
	q["accepted"] = true
	show_message("已接受任务：%s" % String(q.get("name", "")))
	_refresh()
