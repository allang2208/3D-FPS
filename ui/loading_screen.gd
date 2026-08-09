extends CanvasLayer
## 全局加载界面（风格与 UI 统一：金主色 + 深灰底 + 微软雅黑 + 圆角进度条）
## 用法：main.gd _ready 里 add_child(LoadingScreenScript.new()) 注册实例后，
## 任意处（传送门/重载/切场景）调用 LoadingScreen.load_scene(path) / reload_scene()，
## 内部用 load_threaded_request 异步加载并驱动进度条。

const Style := preload("res://ui/style.gd")

static var instance: CanvasLayer = null

var _root: Control
var _bar: ProgressBar
var _pct_label: Label
var _msg_label: Label

func _ready() -> void:
	layer = 200
	instance = self
	_build()
	_root.visible = false

## 切到新场景（带加载进度条）
static func load_scene(path: String) -> void:
	if instance != null:
		instance._start_load(path)
	else:
		var tree := Engine.get_main_loop() as SceneTree
		if tree != null:
			tree.change_scene_to_file(path)

## 重载当前场景
static func reload_scene() -> void:
	if instance == null:
		return
	var cur := instance.get_tree().current_scene
	if cur != null:
		instance._start_load(String(cur.scene_file_path))

func _build() -> void:
	_root = Control.new()
	_root.mouse_filter = Control.MOUSE_FILTER_STOP
	_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(_root)
	var dim := ColorRect.new()
	dim.color = Color(Style.THEME_BG, 0.94)  # 深灰底，遮住旧场景
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_root.add_child(dim)
	var center := VBoxContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	center.alignment = BoxContainer.ALIGNMENT_CENTER
	center.add_theme_constant_override("separation", 18)
	_root.add_child(center)
	_msg_label = Label.new()
	_msg_label.text = "正在加载"
	_msg_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_msg_label.add_theme_font_override("font", Style.make_font(700))
	_msg_label.add_theme_font_size_override("font_size", Style.font_size("h1"))
	_msg_label.add_theme_color_override("font_color", Style.THEME_GOLD)
	center.add_child(_msg_label)
	_bar = ProgressBar.new()
	_bar.custom_minimum_size = Vector2(440, 20)
	_bar.show_percentage = false
	_bar.add_theme_stylebox_override("background",
		Style.make_style(Color(Style.THEME_BG, 0.8), Style.THEME_GRAY_MID, Style.RADIUS_MD, 1))
	_bar.add_theme_stylebox_override("fill",
		Style.make_style(Style.THEME_GOLD, Color.TRANSPARENT, Style.RADIUS_MD, 1))
	center.add_child(_bar)
	_pct_label = Label.new()
	_pct_label.text = "0%"
	_pct_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_pct_label.add_theme_font_override("font", Style.make_font(400))
	_pct_label.add_theme_font_size_override("font_size", Style.font_size("body"))
	_pct_label.add_theme_color_override("font_color", Style.THEME_WHITE)
	center.add_child(_pct_label)

func _start_load(path: String) -> void:
	if path == "":
		return
	_root.visible = true
	_bar.value = 0.0
	_pct_label.text = "0%"
	var err := ResourceLoader.load_threaded_request(path)
	if err != OK:
		# 兜底：直接切换
		_root.visible = false
		var tree := get_tree()
		if tree != null:
			tree.change_scene_to_file(path)
		return
	_await_load(path)

func _await_load(path: String) -> void:
	var progress: Array = []
	while true:
		var st := ResourceLoader.load_threaded_get_status(path, progress)
		if st == ResourceLoader.THREAD_LOAD_LOADED:
			break
		var p := 0.0
		if progress.size() > 0 and progress[0] is float:
			p = progress[0]
		_bar.value = clampf(p, 0.0, 1.0) * 100.0
		_pct_label.text = "%d%%" % int(clampf(p, 0.0, 1.0) * 100.0)
		await get_tree().process_frame
	var packed: PackedScene = ResourceLoader.load_threaded_get(path)
	_bar.value = 100.0
	_pct_label.text = "100%"
	await get_tree().create_timer(0.12).timeout  # 短暂展示满进度，避免闪烁
	_root.visible = false
	var tree := get_tree()
	if tree != null:
		tree.change_scene_to_packed(packed)
