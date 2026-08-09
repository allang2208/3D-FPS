extends CanvasLayer
## NPC 栏（UI 迁移线）：旧 2D 版 hud-panels-npc.js + npc-dialogue.js 的对话框部分迁移。
## 立绘 + 名称 + 逐字对话文本 + 按 npc_type 变化的操作按钮；只消费 ui/style.gd Token。
## 数据源由外部传入 Dictionary（对齐旧版 NPC 配置）：
##   { "id", "name", "npc_type", "portrait"(res://), "greetings": [String] }
## 调试入口：运行时按 F8 打开内置演示 NPC（小鼠侍从 / quest）。

const Style := preload("res://ui/style.gd")

signal option_pressed(id: String)
signal close_requested

const DEMO_NPC := {
	"id": "mouse_attendant",
	"name": "小鼠侍从",
	"npc_type": "quest",
	"portrait": "res://assets/ui/npc/mouse_attendant.png",
	"greetings": [
		"你好，冒险者！欢迎来到无尽轮回。",
		"出任务遭遇意外是很正常的，我们找你就是为了应对这种情况。",
		"时空裂隙的出现频率越来越高，请务必小心。",
	],
}

const OPTION_SETS := {
	"altar": [["expedition", "献祭出征"], ["fusion", "祭品合成"], ["close", "退出"]],
	"blacksmith": [["shop", "商店"], ["enhance", "强化"], ["enchant", "附魔"], ["craft", "改造"], ["close", "再见"]],
	"quest": [["quest", "开始任务"], ["teleport", "传送至任务地点"], ["info", "了解信息"], ["help", "获取帮助"], ["close", "再见"]],
}
const DEFAULT_OPTIONS := [
	["shop", "打开商店"], ["enhance", "强化装备"],
	["craft", "改造装备"], ["enchant", "附魔装备"], ["close", "再见"],
]

var _panel: Panel
var _portrait_frame: Panel
var _portrait: TextureRect
var _name_label: Label
var _text_label: Label
var _options: HBoxContainer
var _theme: Theme
var _font_regular: Font
var _font_bold: Font

var _open := false
var _npc := {}
var _last_npc := {}
var _option_ids: Array[String] = []
var _typing := false
var _full_text := ""
var _type_acc := 0.0
var _was_captured := false

func _ready() -> void:
	layer = int(Style.npc("layer_bar", 50))
	_theme = Style.make_theme()
	_font_regular = Style.make_font(Style.font_weight("regular"))
	_font_bold = Style.make_font(Style.font_weight("bold"))
	_build()
	hide()
	var vp := get_viewport()
	if vp != null and not vp.is_connected("size_changed", _reposition):
		vp.size_changed.connect(_reposition)

func _process(delta: float) -> void:
	if not _open or not _typing:
		return
	_type_acc += delta * float(Style.npc("type_speed", 42.0))
	var n := int(_type_acc)
	if n >= _full_text.length():
		_text_label.text = _full_text
		_typing = false
	else:
		_text_label.text = _full_text.substr(0, n)

func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode == KEY_F8:
		if is_open():
			close()
		else:
			open_demo()

func _build() -> void:
	_panel = Panel.new()
	_panel.name = "Panel"
	_panel.add_theme_stylebox_override("panel", Style.make_panel_style())
	add_child(_panel)

	var row := HBoxContainer.new()
	row.name = "Row"
	row.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	row.add_theme_constant_override("separation", Style.spacing("element_gap"))
	_panel.add_child(row)

	# 立绘区：无 portrait 的 NPC（祭坛/仓库等）隐藏整块
	_portrait_frame = Panel.new()
	_portrait_frame.name = "PortraitFrame"
	var ps := float(Style.npc("portrait_s", 132.0))
	_portrait_frame.custom_minimum_size = Vector2(ps, ps)
	_portrait_frame.add_theme_stylebox_override("panel",
		Style.make_slot_style(Style.THEME_GRAY_MID, Style.THEME_GRAY_MID, "sm", 1))
	row.add_child(_portrait_frame)
	_portrait = TextureRect.new()
	_portrait.name = "Portrait"
	_portrait.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_portrait.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_portrait_frame.add_child(_portrait)

	var info := VBoxContainer.new()
	info.name = "Info"
	info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	info.add_theme_constant_override("separation", Style.spacing("grid"))
	row.add_child(info)

	_name_label = Label.new()
	_name_label.name = "NpcName"
	_name_label.theme = _theme
	_name_label.add_theme_font_override("font", _font_bold)
	_name_label.add_theme_color_override("font_color", Style.THEME_GOLD)
	_name_label.add_theme_font_size_override("font_size", Style.font_size("label"))
	info.add_child(_name_label)

	_text_label = Label.new()
	_text_label.name = "NpcText"
	_text_label.theme = _theme
	_text_label.add_theme_font_override("font", _font_regular)
	_text_label.add_theme_color_override("font_color", Style.THEME_WHITE)
	_text_label.add_theme_font_size_override("font_size", Style.font_size("body"))
	_text_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_text_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_text_label.mouse_filter = Control.MOUSE_FILTER_STOP
	_text_label.gui_input.connect(_on_text_input)
	info.add_child(_text_label)

	_options = HBoxContainer.new()
	_options.name = "Options"
	_options.alignment = BoxContainer.ALIGNMENT_END
	_options.add_theme_constant_override("separation", Style.spacing("element_gap"))
	info.add_child(_options)

	_reposition()

func _reposition() -> void:
	if _panel == null:
		return
	var vp := get_viewport()
	if vp == null:
		return
	var vw: float = vp.get_visible_rect().size.x
	var w := minf(float(Style.npc("panel_w", 920.0)), vw * 0.72)
	_panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_panel.offset_left = -w * 0.5
	_panel.offset_top = -float(Style.npc("panel_h", 176.0)) - float(Style.npc("panel_bottom", 18.0))
	_panel.offset_right = w * 0.5
	_panel.offset_bottom = -float(Style.npc("panel_bottom", 18.0))

## ---- 公开接口 ----

func open(npc: Dictionary = {}) -> void:
	_npc = npc.duplicate(true) if not npc.is_empty() else DEMO_NPC.duplicate(true)
	_last_npc = _npc.duplicate(true)
	_open = true
	visible = true

	var p := str(_npc.get("portrait", ""))
	if p.is_empty() or not ResourceLoader.exists(p):
		_portrait.texture = null
		_portrait_frame.visible = false
	else:
		var tex: Texture2D = load(p)
		_portrait.texture = tex
		_portrait_frame.visible = tex != null
	_name_label.text = str(_npc.get("name", "NPC"))

	var greetings: Array = _npc.get("greetings", [])
	var text := "你好，冒险者！"
	if not greetings.is_empty():
		text = str(greetings[randi() % greetings.size()])
	set_text(text)
	_build_options()
	_set_mouse_released(true)

func open_demo() -> void:
	open(DEMO_NPC)

## 子面板关闭后回到对话框（旧版 exitCompactMode）
func reopen() -> void:
	if _last_npc.is_empty():
		open_demo()
		return
	open(_last_npc)

func close() -> void:
	_open = false
	visible = false
	_typing = false
	_portrait.texture = null
	_set_mouse_released(false)

func is_open() -> bool:
	return _open

func set_text(text: String) -> void:
	_full_text = text
	_type_acc = 0.0
	_typing = true
	_text_label.text = ""

func skip() -> void:
	if _typing:
		_text_label.text = _full_text
		_typing = false

func get_option_ids() -> Array:
	return _option_ids.duplicate()

## ---- 内部 ----

func _build_options() -> void:
	for child in _options.get_children():
		child.queue_free()
	_option_ids.clear()
	var npc_type := str(_npc.get("npc_type", "shop"))
	var set_list: Array = OPTION_SETS.get(npc_type, DEFAULT_OPTIONS)
	for entry in set_list:
		var id := str(entry[0])
		var label := str(entry[1])
		_option_ids.append(id)
		var btn := Button.new()
		btn.text = label
		btn.focus_mode = Control.FOCUS_NONE
		btn.custom_minimum_size = Vector2(0, 32)
		btn.set_meta("option_id", id)
		Style.style_button(btn, "body")
		btn.pressed.connect(_on_option.bind(id))
		_options.add_child(btn)

func _on_option(id: String) -> void:
	if id == "close":
		close()
		close_requested.emit()
		return
	option_pressed.emit(id)

func _on_text_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		skip()

func _set_mouse_released(open_bar: bool) -> void:
	if open_bar:
		_was_captured = Input.mouse_mode == Input.MOUSE_MODE_CAPTURED
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif _was_captured:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		_was_captured = false
