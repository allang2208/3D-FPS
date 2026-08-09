extends SceneTree
## 无头冒烟：NPC 栏（立绘 + 名称 + 逐字文本 + 类型化选项 + 信号）
## 运行：$godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_npc_bar.gd

var _bar: Node
var _pressed: Array[String] = []
var _close_count := 0
var _fail := 0
var _frame := 0

func _check(name: String, ok: bool, detail := "") -> void:
	print("TEST ", name, "=", ok, "" if detail.is_empty() else "  " + detail)
	if not ok:
		_fail += 1

func _initialize() -> void:
	_bar = load("res://ui/npc_bar.gd").new()
	root.add_child(_bar)
	_bar.option_pressed.connect(_on_option)
	_bar.close_requested.connect(func() -> void: _close_count += 1)

func _process(_delta: float) -> bool:
	_frame += 1
	if _frame == 1:
		_run()
	return false

func _run() -> void:
	_check("hidden_initially", not _bar.is_open())
	_bar.open_demo()
	_check("open_demo", _bar.is_open())
	_check("demo_name", String(_bar.get("_name_label").text) == "小鼠侍从",
		"got=" + String(_bar.get("_name_label").text))
	var ids: Array = _bar.get_option_ids()
	var want: Array = ["quest", "teleport", "info", "help", "close"]
	_check("quest_options", ids == want, "got=" + str(ids))
	_check("portrait_visible",
		bool(_bar.get("_portrait").texture != null) and bool(_bar.get("_portrait_frame").visible))

	_bar.skip()
	var text_len := String(_bar.get("_text_label").text).length()
	_check("text_filled", text_len > 0, "len=" + str(text_len))

	# 逐个触发按钮，验证 option_pressed / close_requested
	for id in want:
		var hit := false
		for child in _bar.get("_options").get_children():
			if child is Button and child.has_meta("option_id") \
					and str(child.get_meta("option_id")) == id:
				(child as Button).emit_signal("pressed")
				hit = true
				break
		_check("button_" + id, hit)
	var want_pressed: Array = ["quest", "teleport", "info", "help"]
	_check("signal_ids", _pressed == want_pressed, "got=" + str(_pressed))
	_check("close_signal", _close_count == 1 and not _bar.is_open())

	# altar 选项集
	var altar := {
		"id": "altar", "name": "祭坛", "npc_type": "altar",
		"greetings": ["献上祭品，换取力量。"],
	}
	_bar.open(altar)
	var altar_want: Array = ["expedition", "fusion", "close"]
	_check("altar_options", _bar.get_option_ids() == altar_want,
		"got=" + str(_bar.get_option_ids()))

	# 无立绘 NPC（仓库）：隐藏立绘区
	var warehouse := {
		"id": "warehouse", "name": "仓库", "npc_type": "warehouse",
		"greetings": ["存放战利品。"],
	}
	_bar.open(warehouse)
	_check("no_portrait_hidden", not bool(_bar.get("_portrait_frame").visible))
	var shop_want: Array = ["shop", "enhance", "craft", "enchant", "close"]
	_check("default_options", _bar.get_option_ids() == shop_want,
		"got=" + str(_bar.get_option_ids()))
	_bar.close()

	quit(0 if _fail == 0 else 1)

func _on_option(id: String) -> void:
	_pressed.append(id)
