extends SceneTree
## 无头验证：通用组件（tabs/switch/checkbox/slider/input/select/context-menu/nav/command-palette）
## 运行： $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_components.gd

const Tabs := preload("res://ui/tabs.gd")
const Switch := preload("res://ui/switch.gd")
const Checkbox := preload("res://ui/checkbox.gd")
const SliderC := preload("res://ui/slider.gd")
const InputC := preload("res://ui/input.gd")
const Select := preload("res://ui/select.gd")
const ContextMenu := preload("res://ui/context_menu.gd")
const NavigationMenu := preload("res://ui/navigation_menu.gd")
const CommandPalette := preload("res://ui/command_palette.gd")

var _fail := 0
var _tab_idx := -1
var _sw_on := false
var _cb_on := false
var _sl_v := -1.0
var _cp_cmd := ""

func _check(name: String, ok: bool, detail := "") -> void:
	print("TEST ", name, "=", ok, "" if detail.is_empty() else "  " + detail)
	if not ok:
		_fail += 1

func _initialize() -> void:
	var holder := Control.new()
	root.add_child(holder)
	await process_frame
	await process_frame

	# tabs
	var tabs := Tabs.new()
	holder.add_child(tabs)
	tabs.add_tab("A")
	tabs.add_tab("B")
	tabs.tab_changed.connect(func(i: int) -> void: _tab_idx = i)
	tabs.select(1)
	_check("tabs_signal", _tab_idx == 1)
	_check("tabs_buttons", tabs.get_child_count() >= 2)

	# switch
	var sw := Switch.new()
	holder.add_child(sw)
	sw.toggled.connect(func(v: bool) -> void: _sw_on = v)
	sw.set_on(true)
	_check("switch_toggle", sw.is_on() and _sw_on)

	# checkbox
	var cb := Checkbox.new()
	holder.add_child(cb)
	cb.setup("测试项")
	cb.toggled.connect(func(v: bool) -> void: _cb_on = v)
	cb.set_on(true)
	_check("checkbox_toggle", cb.is_on() and _cb_on)

	# slider
	var sl := SliderC.new()
	holder.add_child(sl)
	sl.value_changed.connect(func(v: float) -> void: _sl_v = v)
	sl.setup(0.0, 100.0, 1.0, 42.0)
	_check("slider_value", absf(sl.get_value() - 42.0) < 0.01)
	sl._slider.value = 60.0
	sl._slider.value_changed.emit(60.0)
	_check("slider_signal", absf(_sl_v - 60.0) < 0.01)

	# input
	var inp := InputC.new()
	holder.add_child(inp)
	inp.setup("玩家名", "请输入")
	inp.set_text("阿兰")
	_check("input_text", inp.get_text() == "阿兰")

	# select
	var sel := Select.new()
	holder.add_child(sel)
	sel.setup("分辨率")
	sel.add_item("1080p", 0)
	sel.add_item("1440p", 1)
	sel.select(1)
	_check("select_id", sel.get_selected_id() == 1)

	# context menu
	var cm := ContextMenu.new()
	holder.add_child(cm)
	_check("context_menu_ready", cm.get_theme_stylebox("panel") != null)

	# navigation menu
	var nav := NavigationMenu.new()
	holder.add_child(nav)
	nav.add_item("继续游戏", "play")
	nav.add_item("设置", "settings")
	_check("nav_items", nav.get_child_count() == 2)

	# command palette
	var cp := CommandPalette.new()
	holder.add_child(cp)
	cp.command_selected.connect(func(id: String) -> void: _cp_cmd = id)
	cp.register("open_settings", "打开设置")
	cp.register("quit_game", "退出游戏")
	cp.open()
	_check("cmd_open_visible", cp.visible)
	var had_settings := false
	for c in cp._list.get_children():
		if c is Button and c.text == "打开设置":
			had_settings = true
	_check("cmd_register_all", had_settings and cp._list.get_child_count() == 2)
	cp._search.text = "设置"
	cp._refresh()
	_check("cmd_filtered", cp._list.get_child_count() == 1)
	cp.close()
	_check("cmd_close", not cp.visible)

	quit(0 if _fail == 0 else 1)
