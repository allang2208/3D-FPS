extends Node3D
## F6 独立运行；试验材料和存档不写入正式背包。
const World := preload("res://scripts/voxel_lab/smooth_world.gd")
const Lighting := preload("res://scripts/world_lighting.gd")
const SAVE_PATH := "user://voxel-lab-smooth-v2.json"
var world: Node3D
var player: CharacterBody3D
var camera: Camera3D
var info: Label
var status: Label
var preview: MeshInstance3D
var preview_material: StandardMaterial3D
var selected := 1
var save_path := SAVE_PATH
var save_delay := -1.0
var mine_delay := 0.0
var hidden_layers: Array[CanvasLayer] = []
var hud_was_processing := false

func _ready() -> void:
	if OS.has_environment("VOXEL_LAB_SAVE_PATH"):
		save_path = OS.get_environment("VOXEL_LAB_SAVE_PATH")
	hud_was_processing = HUD.is_processing()
	HUD.set_process(false)
	for child in HUD.get_children():
		if child is CanvasLayer and child.visible:
			hidden_layers.append(child)
			child.hide()
	_build_world()
	_build_player()
	_build_ui()
	var load_result: Error = world.load_world(save_path)
	respawn()
	status.text = "独立试验存档已恢复" if load_result == OK else "新试验场 · 材料独立计数" if load_result == ERR_FILE_NOT_FOUND else "存档无法读取，已保留原文件"
	_build_preview()
	_build_return_portal()
	print("VOXEL_LAB_READY triangles=", world.triangle_count)

func _build_world() -> void:
	add_child(Lighting.create_environment())
	add_child(Lighting.create_sun())
	world = World.new()
	world.name = "VoxelWorld"
	add_child(world)

func _build_return_portal() -> void:
	var portal := preload("res://scripts/voxel_lab/lab_portal.gd").new()
	portal.name = "ReturnPortal"
	portal.target_scene = "res://scenes/main.tscn"
	portal.label_text = "返回主场景\n走入保存并返回"
	portal.portal_color = Color(0.3, 0.9, 0.5)
	portal.position = Vector3(-9, world.natural_height(-9, 9) + 1.4, 9)
	add_child(portal)
	var valley_portal := preload("res://scripts/voxel_lab/lab_portal.gd").new()
	valley_portal.name="ValleyTestPortal"
	valley_portal.target_scene="res://scenes/voxel_valley_test.tscn"
	valley_portal.label_text="旷野接入测试\n走入测试自然山坡"
	valley_portal.portal_color=Color(0.3,0.65,1.0)
	valley_portal.position=Vector3(-6,world.natural_height(-6,12)+1.4,12)
	add_child(valley_portal)

func _build_player() -> void:
	player = CharacterBody3D.new()
	player.set_script(preload("res://scripts/player.gd"))
	player.name = "LabPlayer"
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.3
	capsule.height = 2.0
	shape.shape = capsule
	shape.position.y = 1.0
	player.add_child(shape)
	camera = Camera3D.new()
	camera.name = "Camera3D"
	camera.position.y = 1.7
	camera.current = true
	camera.far = 200.0
	player.add_child(camera)
	add_child(player)
	respawn()

func respawn() -> void:
	var surface_y := 16.0
	for y in range(15, -9, -1):
		if world.get_cell(Vector3i(-13, y, 12)) != 0:
			surface_y = y + 1.1
			break
	player.position = Vector3(-12.5, surface_y, 12.5)
	player.velocity = Vector3.ZERO
	player.look_at(Vector3(5, surface_y, 0))
	camera.rotation.x = -0.25

func _build_ui() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 30
	add_child(layer)
	var panel := PanelContainer.new()
	panel.position = Vector2(22, 22)
	var box_style := StyleBoxFlat.new()
	box_style.bg_color = Color(0.025, 0.04, 0.045, 0.90)
	box_style.content_margin_left = 18
	box_style.content_margin_right = 18
	box_style.content_margin_top = 12
	box_style.content_margin_bottom = 12
	panel.add_theme_stylebox_override("panel", box_style)
	layer.add_child(panel)
	var rows := VBoxContainer.new()
	rows.add_theme_constant_override("separation", 7)
	panel.add_child(rows)
	var title := Label.new()
	title.text = "自然体素试验场  /  48 × 48 米"
	title.add_theme_font_size_override("font_size", 23)
	rows.add_child(title)
	info = Label.new()
	info.add_theme_font_size_override("font_size", 17)
	rows.add_child(info)
	var help := Label.new()
	help.text = "WASD 移动 · 空格跳跃 · Shift 疾跑\n左键挖掘（可按住） · 右键填充 / 搭建\n1 泥土  2 岩石  3 矿石  4 建筑砖\nCtrl+Z 撤销上次操作（最多 32 步）\nF5 保存  F9 读取  R 返回地表  Esc 释放鼠标\n绿框可以放置，红框位置被占用或材料不足\n自动保存修改 · 独立材料，不影响正式背包"
	help.add_theme_font_size_override("font_size", 16)
	rows.add_child(help)
	status = Label.new()
	status.modulate = Color(0.70, 0.88, 0.64)
	rows.add_child(status)
	var reticle := Label.new()
	reticle.text = "+"
	reticle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	reticle.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	reticle.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	reticle.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(reticle)

func _build_preview() -> void:
	preview = MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3.ONE * 1.015
	preview.mesh = box
	preview.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	preview_material = StandardMaterial3D.new()
	preview_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	preview_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	preview.material_override = preview_material
	add_child(preview)

func player_bounds() -> AABB:
	var collider: CollisionShape3D=player.find_children("","CollisionShape3D",false,false)[0]
	var half:=Vector3(collider.shape.radius,collider.shape.height*0.5,collider.shape.radius)
	return world.global_transform.affine_inverse()*collider.global_transform*AABB(-half,half*2.0)

func target() -> Dictionary:
	var query := PhysicsRayQueryParameters3D.create(camera.global_position, camera.global_position - camera.global_basis.z * 7.0, 1)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty() or not hit.collider.has_meta("voxel_chunk"):
		return {}
	hit.position = world.to_local(hit.position)
	hit.normal = (world.global_basis.transposed()*hit.normal).normalized()
	# 平滑表面不一定落在存储单元的立方体边界：选择接触点附近最近的实心单元。
	var center := Vector3i((hit.position-hit.normal*0.15).floor())
	var chosen := center
	var best := INF
	for y in range(-1,2):
		for z in range(-1,2):
			for x in range(-1,2):
				var p := center+Vector3i(x,y,z)
				if world.get_cell(p) == 0:
					continue
				var distance: float = (Vector3(p)+Vector3.ONE*0.5).distance_squared_to(hit.position-hit.normal*0.25)
				if distance < best:
					best = distance
					chosen = p
	if best == INF:
		return {}
	var direction := Vector3i.ZERO
	var axis: int = hit.normal.abs().max_axis_index()
	direction[axis] = 1 if hit.normal[axis] > 0 else -1
	return {"mine":chosen,"place":chosen+direction}

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.ctrl_pressed and event.keycode == KEY_Z:
			if world.undo_edit(player_bounds()):
				save_delay = 0.5
				status.text = "已撤销上次操作，材料已恢复"
			else:
				status.text = "暂无可撤销操作，或恢复位置被玩家占用"
			get_viewport().set_input_as_handled()
			return
		if event.keycode >= KEY_1 and event.keycode <= KEY_4:
			selected = event.keycode - KEY_1 + 1
		elif event.keycode == KEY_F5:
			_save()
		elif event.keycode == KEY_F9:
			# 不在加载后把尚未保存的旧操作写回。
			save_delay = -1.0
			var result: Error = world.load_world(save_path)
			if result == OK:
				respawn()
			status.text = "已恢复存档并返回安全地表" if result == OK else "读取失败：" + error_string(result)
		elif event.keycode == KEY_R:
			respawn()
	if event is InputEventMouseButton and event.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		mine_delay = 0.25
	if event is InputEventMouseButton and event.pressed and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		if event.button_index == MOUSE_BUTTON_RIGHT:
			act(false)
			get_viewport().set_input_as_handled()

func act(dig: bool) -> bool:
	var hit := target()
	if hit.is_empty():
		return false
	var changed: bool = world.mine(hit.mine) if dig else world.place(hit.place, selected, player_bounds())
	if changed:
		save_delay = 0.5
		status.text = "已挖掘并回收材料" if dig else "已放置，已扣除材料"
	return changed

func _physics_process(delta: float) -> void:
	mine_delay -= delta
	if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED and Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT) and mine_delay <= 0:
		act(true)
		mine_delay = 0.22
	var hit := target()
	preview.visible = not hit.is_empty() and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED
	if preview.visible:
		preview.global_position = world.to_global(Vector3(hit.place) + Vector3.ONE * 0.5)
		preview_material.albedo_color = Color(0.3, 0.9, 0.45, 0.24) if world.can_place(hit.place, selected, player_bounds()) else Color(1, 0.2, 0.2, 0.24)
	if player.position.y < -20:
		respawn()
	if save_delay >= 0:
		save_delay -= delta
		if save_delay < 0:
			_save()
	info.text = "当前：%s   泥土 %d · 岩石 %d · 矿石 %d · 砖 %d\n%d FPS · %d 三角面 · 修改重建 %.1f ms / %d 区块" % [["", "泥土", "岩石", "矿石", "建筑砖"][selected], world.stock[1], world.stock[2], world.stock[3], world.stock[4], Engine.get_frames_per_second(), world.triangle_count, world.last_rebuild_ms, world.last_rebuilt_chunks]

func _save() -> void:
	var result: Error = world.save_world(save_path)
	status.text = "试验场已保存" if result == OK else "保存失败：" + error_string(result)
	save_delay = -1.0

func _exit_tree() -> void:
	if save_delay >= 0:
		world.save_world(save_path)
	HUD.set_process(hud_was_processing)
	for layer in hidden_layers:
		if is_instance_valid(layer):
			layer.show()
