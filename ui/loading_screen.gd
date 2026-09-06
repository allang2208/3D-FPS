extends CanvasLayer
## Keep the overlay alive until scene initialization and rendering finish.
const Style := preload("res://ui/style.gd")
static var instance: CanvasLayer = null
var _root: Control
var _bar: ProgressBar
var _pct_label: Label
var _msg_label: Label
var _loading := false
var _was_paused := false

func _ready() -> void:
	if is_instance_valid(instance) and instance != self:
		queue_free()
		return
	layer = 200
	process_mode = Node.PROCESS_MODE_ALWAYS

	instance = self
	_build()
	_root.visible = false


func _exit_tree() -> void:
	if instance == self:
		instance = null


## 切到新场景；标题留空时使用通用载入文案。
static func load_scene(path: String, title := "") -> void:
	if is_instance_valid(instance):
		instance._start_load(path, title)
	else:
		var tree := Engine.get_main_loop() as SceneTree
		if tree != null:
			var overlay = load("res://ui/loading_screen.gd").new()
			tree.root.add_child(overlay)
			overlay._start_load(path, title)


## 重载当前场景。
static func reload_scene() -> void:
	if not is_instance_valid(instance):
		return
	var cur := instance.get_tree().current_scene
	if cur != null:
		instance._start_load(String(cur.scene_file_path), "")


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

func _start_load(path: String, title: String) -> void:
	if path.is_empty() or _loading:
		return
	_loading = true
	var tree := get_tree()
	if get_parent() != tree.root:
		reparent(tree.root)
	_was_paused = tree.paused
	tree.paused = true
	_msg_label.text = title if not title.is_empty() else "正在加载"
	_set_progress(0.0)
	_root.visible = true
	# Draw the overlay before resource requests or synchronous scene construction.
	await tree.process_frame
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw

	var err := ResourceLoader.load_threaded_request(path)
	if err != OK:
		_show_failure("载入失败")
		push_error("LoadingScreen: cannot start threaded load for %s (%s)" % [path, error_string(err)])
		return
	_await_load(path)


func _await_load(path: String) -> void:
	var progress: Array = []
	while true:
		var status := ResourceLoader.load_threaded_get_status(path, progress)
		if status == ResourceLoader.THREAD_LOAD_LOADED:
			break
		if status == ResourceLoader.THREAD_LOAD_FAILED or status == ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
			_show_failure("载入失败")
			push_error("LoadingScreen: threaded load failed for %s" % path)
			return
		var ratio := 0.0
		if not progress.is_empty() and (progress[0] is float or progress[0] is int):
			ratio = float(progress[0])
		_set_progress(clampf(ratio, 0.0, 1.0) * 75.0)
		await get_tree().process_frame

	var packed := ResourceLoader.load_threaded_get(path) as PackedScene
	if packed == null:
		_show_failure("载入失败")
		push_error("LoadingScreen: %s did not resolve to PackedScene" % path)
		return
	var tree := get_tree()
	_set_progress(75.0)
	_msg_label.text = "正在创建场景..."
	await tree.process_frame
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
	var error := tree.change_scene_to_packed(packed)
	if error != OK:
		_show_failure("场景创建失败")
		return
	await tree.scene_changed
	_set_progress(90.0)
	_msg_label.text = "正在初始化玩家与界面..."
	var scene := tree.current_scene
	while is_instance_valid(scene) and scene.has_method("is_loading_ready") and not scene.is_loading_ready():
		await tree.process_frame
	if not is_instance_valid(scene):
		_show_failure("场景初始化失败")
		return
	_set_progress(95.0)
	_msg_label.text = "正在准备画面..."
	# Deferred setup and actual rendering stay covered, with gameplay paused.
	for frame in 2:
		await tree.process_frame
		if DisplayServer.get_name() != "headless":
			await RenderingServer.frame_post_draw
	_set_progress(100.0)
	_msg_label.text = "加载完成"
	await tree.process_frame
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
	_root.visible = false
	_loading = false
	tree.paused = _was_paused


func _set_progress(value: float) -> void:
	var safe_value := clampf(value, 0.0, 100.0)
	_bar.value = safe_value
	_pct_label.text = "%d%%" % int(floor(safe_value))


func _show_failure(message: String) -> void:
	_loading = false
	get_tree().paused = _was_paused
	_msg_label.text = message
	_pct_label.text = "请重试"
	_bar.value = 0.0
