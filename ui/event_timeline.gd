extends Control
## Source timeline UI, owned by the persistent HUD. Only interactive children consume input.
const Model := preload("res://ui/event_timeline_model.gd")
const Look := preload("res://ui/event_timeline_style.gd")
var model := Model.new()
var compact := true
var filter_type := "all"
var current_events: Array = []
var display_events: Array = []
var invasion := {"text":"暂无入侵情报","detail":"","active":false,"can_support":false}
var support_action: Callable
var _stack: VBoxContainer
var _panel: PanelContainer
var _expanded: VBoxContainer
var _filters: HFlowContainer
var _window: Label
var _invasion_text: Label
var _invasion_detail: Label
var _support: Button
var _track: Control
var _track_margin: MarginContainer
var _toggle: Button
var _popover: PanelContainer
var _popover_title: Label
var _popover_content: VBoxContainer
var _popover_id := ""
var _popover_event: Dictionary = {}
var _signature := ""
var _filter_signature := ""
var _markers: Array[Button] = []
var _lines: Array[ColorRect] = []
var _cursor: ColorRect
var _now: Label
var _timer := 0.0
var _scene: Node
var _weather: Node
var _world_name := "当前区域"
var _motion: Tween
var _animated_width := -1.0
var _severity := ""
var _pulse := 0.0
var reduced_motion := false

func _ready() -> void:
	name = "EventTimeline"
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_stack = VBoxContainer.new()
	_stack.add_theme_constant_override("separation",0)
	_stack.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_stack)
	_panel = PanelContainer.new()
	_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel.add_theme_stylebox_override("panel",Look.Style.make_hud_surface(8,3))
	_stack.add_child(_panel)
	var column := VBoxContainer.new()
	column.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_theme_constant_override("separation",0)
	_panel.add_child(column)
	_expanded = VBoxContainer.new()
	_expanded.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_expanded.custom_minimum_size.y = 66
	column.add_child(_expanded)
	var heading := HBoxContainer.new()
	_expanded.add_child(heading)
	var title := Look.label("时间进度栏",12,true)
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	heading.add_child(title)
	_window = Look.label("未来5日",11)
	_window.add_theme_color_override("font_color",Look.MUTED)
	heading.add_child(_window)
	_expanded.add_child(HSeparator.new())
	_filters = HFlowContainer.new()
	_filters.alignment = FlowContainer.ALIGNMENT_CENTER
	_filters.add_theme_constant_override("h_separation",4)
	_expanded.add_child(_filters)
	_invasion_text = Look.label("⚔ 暂无入侵情报",12)
	_invasion_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_expanded.add_child(_invasion_text)
	_invasion_detail = Look.label("",11)
	_invasion_detail.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_invasion_detail.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_expanded.add_child(_invasion_detail)
	_support = Look.button("⚔ 前往支援",12)
	_support.pressed.connect(func():
		if support_action.is_valid() and invasion.get("can_support",false): support_action.call())
	_expanded.add_child(_support)
	_track = Control.new()
	_track.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_track_margin = MarginContainer.new()
	_track_margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_child(_track_margin)
	_track_margin.add_child(_track)
	_track.resized.connect(_layout_markers)
	var background := Panel.new()
	background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	background.add_theme_stylebox_override("panel",Look.box(Look.TRACK,Look.LINE,3))
	_track.add_child(background)
	var gradient := Gradient.new()
	gradient.offsets = PackedFloat32Array([0,0.33,0.66,1])
	gradient.colors = PackedColorArray([Color("e5413e"),Color("f1c13f"),Color("418be7"),Color("3dc45b")])
	var texture := GradientTexture2D.new()
	texture.gradient = gradient
	texture.fill_from = Vector2.ZERO
	texture.fill_to = Vector2.RIGHT
	var bar := TextureRect.new()
	bar.name = "ProgressGradient"
	bar.texture = texture
	bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bar.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	bar.offset_top = -3
	bar.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_track.add_child(bar)
	_cursor = ColorRect.new()
	_cursor.color = Look.TEXT
	_cursor.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_cursor.z_index = 3
	_track.add_child(_cursor)
	_now = Look.label("现在",9)
	_track.add_child(_now)
	_toggle = Look.button("⌄",15)
	_toggle.custom_minimum_size = Vector2(46,16)
	_toggle.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	_toggle.pressed.connect(func(): set_compact(not compact))
	for state in ["normal","hover","pressed"]:
		_toggle.add_theme_stylebox_override(state,Look.box(Look.TRACK,Look.LINE,4,0))
	column.add_child(_toggle)
	_build_popover()
	get_viewport().size_changed.connect(_resize)
	set_compact(true,false)
	refresh()

func _build_popover() -> void:
	_popover = PanelContainer.new()
	# Existing quickbar is z=150; forecast details must remain readable above it.
	_popover.z_index = 170
	_popover.add_theme_stylebox_override("panel",Look.Style.make_hud_surface(9,7))
	add_child(_popover)
	var column := VBoxContainer.new()
	_popover.add_child(column)
	var heading := HBoxContainer.new()
	column.add_child(heading)
	_popover_title = Look.label("事件详情",12,true)
	_popover_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	heading.add_child(_popover_title)
	var close := Look.button("×",18)
	close.custom_minimum_size = Vector2(24,24)
	close.pressed.connect(close_popover)
	heading.add_child(close)
	column.add_child(HSeparator.new())
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size.y = 125
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(scroll)
	_popover_content = VBoxContainer.new()
	_popover_content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(_popover_content)
	_popover.hide()

func _resize() -> void:
	var viewport := get_viewport_rect().size
	var width := minf(_animated_width if _animated_width>0 else 360 if compact else 560,viewport.x-24)
	_stack.size = Vector2(width,0)
	_panel.custom_minimum_size.x = width
	size = Vector2(width,_stack.get_combined_minimum_size().y)
	var top := 76.0
	# Keep original top-center placement unless the existing clock actually overlaps.
	var clock := get_parent().get_node_or_null("GameClock") as Control
	if clock!=null and clock.visible:
		var proposed := Rect2(Vector2((viewport.x-width)*0.5,top),size)
		if proposed.intersects(clock.get_global_rect()): top = clock.get_global_rect().end.y+8
	position = Vector2((viewport.x-width)*0.5,top)
	_popover.size.x = minf(410,viewport.x-24)
	_popover.position = Vector2((width-_popover.size.x)*0.5,_stack.size.y+8)
	_popover.custom_minimum_size.y = 0
	_popover.size.y = 0
	_layout_markers()

func set_compact(value: bool, animate := true) -> void:
	var old_width := size.x
	compact = value
	_panel.add_theme_stylebox_override("panel",Look.surface(compact,_severity))
	for side in ["left","right"]: _track_margin.add_theme_constant_override("margin_"+side,3 if compact else 5)
	_track_margin.add_theme_constant_override("margin_top",1 if compact else 7)
	_track_margin.add_theme_constant_override("margin_bottom",0 if compact else 7)
	_expanded.visible = not compact
	_track.custom_minimum_size.y = 30 if compact else 44
	_now.visible = not compact
	_track.get_node("ProgressGradient").offset_top = -3 if compact else -5
	_toggle.text = "⌄" if compact else "⌃"
	_toggle.tooltip_text = "展开详细时间进度栏" if compact else "收起为简化时间进度栏"
	if compact: close_popover()
	_signature = ""
	if is_instance_valid(_motion): _motion.kill()
	_animated_width = -1
	if animate and not reduced_motion and old_width>0:
		_animated_width = old_width
		_motion = create_tween()
		_motion.tween_method(func(width):
			_animated_width = width
			_resize(),old_width,minf(360 if compact else 560,get_viewport_rect().size.x-24),0.16).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		_motion.tween_callback(func():
			_animated_width = -1
			_resize())
	_resize()
	refresh()
	_resize.call_deferred()

func set_filter(value: String) -> void:
	filter_type = value
	_signature = ""
	close_popover()
	refresh()

func set_invasion_model(value: Dictionary, action := Callable()) -> void:
	invasion = value.duplicate(true)
	support_action = action
	refresh()

func _process(delta: float) -> void:
	_timer += delta
	if _timer>=0.25:
		_timer = 0
		refresh()
	_pulse += delta
	for index in _lines.size():
		var event: Dictionary = display_events[index]
		var duration := 0.8 if event.get("status","")=="active" else 1.15 if event.get("warning_level","")=="critical" else 1.4 if event.type=="invasion" else 2.0
		_lines[index].modulate.a = 0.75 if reduced_motion else 0.68+0.28*(sin(_pulse*TAU/duration)*0.5+0.5)
		_markers[index].get_child(0).get_child(0).modulate.a = 1.0 if reduced_motion else 0.82+0.18*(sin(_pulse*TAU/duration)*0.5+0.5)

func refresh() -> void:
	if not is_node_ready(): return
	var hud := get_node_or_null("/root/HUD")
	if hud==null: return
	var scene := get_tree().current_scene
	if scene!=_scene:
		_scene = scene
		_weather = null
		close_popover()
		model.unregister_provider("scene")
		invasion = {"text":"暂无入侵情报","active":false,"can_support":false}
		support_action = Callable()
		_world_name = "当前区域" if scene==null else "天空基地" if "sky_base" in scene.scene_file_path else str(scene.get_meta("world_name",scene.name))
		if scene!=null and scene.has_method("get_timeline_events"):
			model.register_provider("scene",scene.get_timeline_events)
	if not is_instance_valid(_weather) and scene!=null:
		for env in scene.find_children("*","WorldEnvironment",true,false):
			if "weather" in env and is_instance_valid(env.weather):
				_weather = env.weather
				break
	if scene!=null and scene.has_method("get_timeline_invasion_model"):
		invasion = scene.get_timeline_invasion_model()
		support_action = Callable(scene,"support_active_invasion")
	var snapshot := model.get_hud_model(hud.game_clock,_weather,_world_name)
	current_events = snapshot.events
	var types := {"all":{"label":"全部","count":current_events.size()}}
	for event in current_events:
		if not types.has(event.type): types[event.type] = {"label":event.type_label,"count":0}
		types[event.type].count += 1
	if not types.has(filter_type): filter_type = "all"
	var filter_sig := JSON.stringify(types)+filter_type
	if filter_sig!=_filter_signature:
		_filter_signature = filter_sig
		_clear_children(_filters)
		for key in types:
			var button := Look.button("%s %d" % [types[key].label,types[key].count])
			button.toggle_mode = true
			button.button_pressed = key==filter_type
			button.pressed.connect(set_filter.bind(key))
			_filters.add_child(button)
	var visible_events: Array = current_events.filter(func(e): return filter_type=="all" or e.type==filter_type)
	display_events = Model.cluster_events(visible_events)
	_window.text = "未来5日 · %d个事件" % current_events.size() if filter_type=="all" else "未来5日 · 显示%d/%d个事件" % [visible_events.size(),current_events.size()]
	_invasion_text.text = "⚔ "+str(invasion.get("text","暂无入侵情报"))
	_invasion_detail.text = invasion.get("detail","")
	_invasion_detail.visible = not _invasion_detail.text.is_empty()
	_support.visible = invasion.get("active",false) and invasion.get("can_support",false)
	_support.disabled = not support_action.is_valid()
	var severity: String = invasion.get("severity","")
	if severity.is_empty() and invasion.get("active",false): severity = "active"
	if severity!=_severity:
		_severity = severity
		_panel.add_theme_stylebox_override("panel",Look.surface(compact,_severity))
	var signature := str(compact)+str(display_events.map(func(e): return [e.id,e.label,e.time_label,e.get("status",""),e.get("warning_level","")]))
	if signature!=_signature:
		_signature = signature
		_rebuild_markers()
		_resize.call_deferred()
	_layout_markers()
	if _popover.visible and not _popover_id.is_empty():
		var found := false
		var candidates: Array = current_events+display_events
		for event in candidates:
			if event.id==_popover_id:
				found = true
				# Positions move every refresh; do not rebuild the list or reset its scroll.
				if _detail_signature(event)!=_detail_signature(_popover_event): _show_event(event,false)
				break
		if not found: close_popover()

func _rebuild_markers() -> void:
	for marker in _markers:
		_track.remove_child(marker)
		marker.queue_free()
	for line in _lines:
		_track.remove_child(line)
		line.queue_free()
	_markers.clear()
	_lines.clear()
	for event in display_events:
		var line := ColorRect.new()
		line.mouse_filter = Control.MOUSE_FILTER_IGNORE
		line.color = Look.color(event)
		_track.add_child(line)
		_lines.append(line)
		var marker := Look.button("",9,preload("res://ui/event_timeline_marker.gd").new())
		marker.add_theme_stylebox_override("normal",StyleBoxEmpty.new())
		marker.z_index = 2
		marker.tooltip_text = Look.hover_copy(event)
		var row := HBoxContainer.new()
		row.mouse_filter = Control.MOUSE_FILTER_IGNORE
		row.add_theme_constant_override("separation",0 if compact else 2)
		marker.add_child(row)
		if event.has("cluster_events"):
			var badge := PanelContainer.new()
			badge.mouse_filter = Control.MOUSE_FILTER_IGNORE
			badge.add_theme_stylebox_override("panel",Look.box(Look.TRACK,Look.color(event),9,2))
			badge.add_child(Look.label("+%d" % event.cluster_events.size(),9 if compact else 10,true))
			row.add_child(badge)
		else: row.add_child(Look.icon(event,14 if compact else 18))
		if not compact: row.add_child(Look.label(event.time_label,9))
		marker.custom_minimum_size = row.get_combined_minimum_size()
		if event.has("cluster_events") or event.type=="weather": marker.pressed.connect(_show_event.bind(event))
		_track.add_child(marker)
		_markers.append(marker)

func _layout_markers() -> void:
	if not is_instance_valid(_track): return
	var lanes := Model.assign_lanes(display_events)
	for index in mini(_markers.size(),display_events.size()):
		var fraction: float = display_events[index].position
		var marker := _markers[index]
		var x := fraction*_track.size.x
		marker.size = marker.get_combined_minimum_size()
		var alignment := 0.08 if fraction<=0.08 else 0.92 if fraction>=0.92 else 0.5
		marker.position = Vector2(clampf(x-marker.size.x*alignment,0,maxf(0,_track.size.x-marker.size.x)),(1 if compact else 2)+lanes[index]*(12 if compact else 18))
		_lines[index].position = Vector2(x-1,-1)
		_lines[index].size = Vector2(2,_track.size.y+2)
	_cursor.position = Vector2(_track.size.x*0.04-1,-3)
	_cursor.size = Vector2(2,_track.size.y+5)
	_now.position = Vector2(_cursor.position.x-9,_track.size.y+1)
	if is_instance_valid(_popover): _popover.position.y = _stack.size.y+8

func _show_event(event: Dictionary, toggle := true) -> void:
	if toggle and _popover.visible and _popover_id==event.id:
		close_popover()
		return
	_popover_id = event.id
	_popover_event = event.duplicate(true)
	_clear_children(_popover_content)
	_popover_title.text = event.label if event.has("cluster_events") else "天气预报详情"
	var scroll := _popover_content.get_parent() as ScrollContainer
	scroll.custom_minimum_size.y = minf(240 if event.has("cluster_events") or event.get("stages",[]).size()>1 else 160,maxf(100,get_viewport_rect().size.y-global_position.y-_stack.size.y-75))
	if event.has("cluster_events"):
		for child in event.cluster_events:
			var button := Look.button("",12)
			var row := HBoxContainer.new()
			row.mouse_filter = Control.MOUSE_FILTER_IGNORE
			row.add_child(Look.icon(child,28))
			var text := VBoxContainer.new()
			text.mouse_filter = Control.MOUSE_FILTER_IGNORE
			text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			var entry_title := Look.label(child.label,12,true)
			entry_title.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
			text.add_child(entry_title)
			var entry_time := Look.label(child.type_label+" · "+child.time_label,11)
			entry_time.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
			text.add_child(entry_time)
			row.add_child(text)
			button.add_child(row)
			button.custom_minimum_size.y = row.get_combined_minimum_size().y+6
			row.position = Vector2(7,3)
			button.resized.connect(func(): row.size.x = maxf(0,button.size.x-14))
			button.tooltip_text = Look.hover_copy(child)
			if child.type=="weather": button.pressed.connect(_show_event.bind(child))
			_popover_content.add_child(button)
	else:
		var summary := HBoxContainer.new()
		summary.add_child(Look.icon(event,28))
		var name_label := Look.label(event.label,12,true)
		name_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		name_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		summary.add_child(name_label)
		_popover_content.add_child(summary)
		if event.get("stages",[]).size()>1:
			var names: Array[String] = []
			for stage in event.stages: names.append(Model.WEATHER_NAMES[stage.mode])
			var sequence := Look.label("依次变化："+" → ".join(names),12)
			sequence.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			_popover_content.add_child(sequence)
		var grid := GridContainer.new()
		grid.columns = 1 if get_viewport_rect().size.x<=520 else 2
		grid.add_theme_constant_override("h_separation",5)
		grid.add_theme_constant_override("v_separation",5)
		_popover_content.add_child(grid)
		for pair in [["位面",event.get("world_name","当前区域")],["强度",event.get("intensity_name","—")],["开始",event.get("starts_at_label","—")],["结束",event.get("ends_at_label","—")],["持续",event.get("duration_label","—")],["强度提示",event.get("warning_label","—")],["状态","正在发生" if event.get("status","")=="active" else "预测中"]]:
			var panel := PanelContainer.new()
			panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			panel.add_theme_stylebox_override("panel",Look.box(Look.TRACK,Look.LINE,4,5))
			var row := HBoxContainer.new()
			panel.add_child(row)
			var key := Look.label(str(pair[0]),11)
			key.add_theme_color_override("font_color",Look.DIM)
			row.add_child(key)
			var value := Look.label(str(pair[1]),11)
			value.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
			value.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			value.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
			value.mouse_filter = Control.MOUSE_FILTER_PASS
			value.tooltip_text = str(pair[1])
			row.add_child(value)
			grid.add_child(panel)
		if event.get("stages",[]).size()>1:
			_popover_content.add_child(Look.label("本轮雨势变化（依次发生）",12,true))
			for stage in event.stages:
				var phase := Look.label("%s  %s — %s" % [Model.WEATHER_NAMES[stage.mode],Model.absolute_time(stage.start),Model.absolute_time(stage.end)],11)
				phase.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
				_popover_content.add_child(phase)
	_popover.show()
	_resize.call_deferred()

func close_popover() -> void:
	if is_instance_valid(_popover): _popover.hide()
	_popover_id = ""
	_popover_event = {}

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode==KEY_ESCAPE and is_instance_valid(_popover) and _popover.visible:
		close_popover()
		get_viewport().set_input_as_handled()

func _clear_children(node: Node) -> void:
	for child in node.get_children():
		node.remove_child(child)
		child.queue_free()

func _detail_signature(event: Dictionary) -> String:
	if event.has("cluster_events"):
		return str(event.cluster_events.map(func(e): return [e.id,e.label,e.time_label,e.status]))
	return str([event.get("id"),event.get("label"),event.get("status"),event.get("starts_at_label"),event.get("ends_at_label"),event.get("warning_label")])
