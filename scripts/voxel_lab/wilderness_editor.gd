extends "res://scripts/voxel_lab/voxel_lab.gd"
## 正式旷野中的地形工具，共用玩家和 HUD，F7 切换武器/地形操作。
const GROUND_REWARDS := {1:"soil",2:"stone",3:"iron_ore"}
var scene: Node3D
var enabled := false
var tool_layer: CanvasLayer
var hint_label: Label
var gun: Node3D
var gun_mode: ProcessMode
var gun_visible := true
var grass_base: Image
var grass_texture: ImageTexture
var foliage: Array = []
var foliage_dirty := false
var initial_restore := true

func _ready() -> void:
	scene=get_parent()
	player=scene._player
	camera=player.get_node("Camera3D")
	gun=player.get_node_or_null("Camera3D/Gun")
	# Enter the wilderness in ordinary FPS mode. F7 explicitly hands input to
	# terrain editing, so a stale scene/meta value can never suppress the gun.
	player.set_meta("terrain_editing", false)
	save_path=OS.get_environment("WILDERNESS_SAVE_PATH") if OS.has_environment("WILDERNESS_SAVE_PATH") else "user://wilderness-terrain-v1.json"
	world=preload("res://scripts/voxel_lab/wilderness_world.gd").new()
	world.terrain=scene.terrain
	world.name="EditableGround"
	add_child(world)
	_build_ui()
	_build_preview()
	# Wilderness enters as an ordinary gameplay map. The editor may take over
	# input only after an explicit F7 toggle.
	_sync_gameplay_mode()
	grass_base=scene.grass_exclusion.duplicate()
	grass_texture=ImageTexture.create_from_image(grass_base)
	scene.get_node("ParticleGrass").process_material.set_shader_parameter("solid_exclusion",grass_texture)
	for child in scene.get_children():
		if child is MultiMeshInstance3D and child.has_meta("ground_roots"):
			var transforms: Array=[]
			for i in child.multimesh.instance_count: transforms.append(child.multimesh.get_instance_transform(i))
			foliage.append([child,child.get_meta("ground_roots"),transforms])
	var result: Error=world.load_world(save_path)
	if result!=OK and result!=ERR_FILE_NOT_FOUND:
		status.text="地形存档读取失败，原文件已保留"
		hint_label.text=status.text
		# 避免后续自动保存覆盖损坏的原文件。
		save_path+=".recovery-"+str(Time.get_unix_time_from_system())
	world.exit_save_path=save_path

func _build_ui() -> void:
	super._build_ui()
	tool_layer=info.get_parent().get_parent().get_parent()
	info.get_parent().get_child(0).text="旷野地形工具 / F7 返回武器"
	tool_layer.hide()
	var hints:=CanvasLayer.new()
	add_child(hints)
	hint_label=Label.new()
	hint_label.text="B 建造 · 6 伐木斧 · 7 矿镐 · F7 返回武器"
	hint_label.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	hint_label.position=Vector2(-220,-42)
	hint_label.add_theme_color_override("font_shadow_color",Color.BLACK)
	hint_label.add_theme_constant_override("shadow_offset_x",2)
	hint_label.add_theme_constant_override("shadow_offset_y",2)
	hints.add_child(hint_label)

func set_enabled(value: bool) -> void:
	if enabled==value:
		_sync_gameplay_mode()
		return
	if value:
		var building:=scene.get_node_or_null("BuildingSystem")
		if building!=null:
			if building.menu!=null and building.menu.is_open(): building.menu.close()
			building.set_active(false)
	enabled=value
	_sync_gameplay_mode()
	mine_delay=0.25

func _sync_gameplay_mode() -> void:
	toolkit.set_active(enabled)
	tool_layer.visible=enabled
	hint_label.visible=not enabled
	preview.visible=false
	player.set_meta("terrain_editing",enabled)
	if gun!=null:
		if enabled:
			gun_mode=gun.process_mode
			gun_visible=gun.visible
			gun.process_mode=Node.PROCESS_MODE_DISABLED
			gun.hide()
		else:
			gun.process_mode=gun_mode
			gun.visible=gun_visible

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode==KEY_F7:
		set_enabled(not enabled)
		get_viewport().set_input_as_handled()
		return
	# Tool hotkeys enter harvesting directly; F7 remains the explicit way back
	# to the firearm. Possession is still checked by BasicToolkit.equip().
	if not enabled and event is InputEventKey and event.pressed and not event.echo and event.keycode in [KEY_5,KEY_6,KEY_7]:
		set_enabled(true)
		super._input(event)
		get_viewport().set_input_as_handled()
		return
	if not enabled: return
	super._input(event)
	if event is InputEventKey and (event.keycode in [KEY_1,KEY_2,KEY_3,KEY_4,KEY_F5,KEY_F9,KEY_R] or (event.ctrl_pressed and event.keycode==KEY_Z)):
		get_viewport().set_input_as_handled()
	if event is InputEventMouseButton and Input.mouse_mode==Input.MOUSE_MODE_CAPTURED:
		get_viewport().set_input_as_handled()
	if event is InputEventKey and event.pressed and (event.keycode==KEY_Z or event.keycode==KEY_F9): foliage_dirty=true

func target() -> Dictionary:
	var query:=PhysicsRayQueryParameters3D.create(camera.global_position,camera.global_position-camera.global_basis.z*7.0,1)
	var hit:=get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty() or (hit.collider!=scene.terrain and not hit.collider.has_meta("voxel_chunk")): return {}
	var center:=Vector3i((hit.position-hit.normal*0.25).floor())
	var chosen:=center
	var best:=INF
	for y in range(-1,2):
		for z in range(-1,2):
			for x in range(-1,2):
				var p:=center+Vector3i(x,y,z)
				if world.get_cell(p)==0: continue
				var distance: float=(Vector3(p)+Vector3.ONE*0.5).distance_squared_to(hit.position-hit.normal*0.3)
				if distance<best:
					best=distance
					chosen=p
	if best==INF: return {}
	var direction:=Vector3i.ZERO
	var axis: int=hit.normal.abs().max_axis_index()
	direction[axis]=1 if hit.normal[axis]>0 else -1
	return {"mine":chosen,"place":chosen+direction}

func act(dig: bool) -> bool:
	if not enabled: return false
	if dig:
		if not toolkit.resolving:
			toolkit.begin_use()
			return false
		if not toolkit.allows_ground(): return false
	var hit:=target()
	if hit.is_empty(): return false
	var cell: Vector3i=hit.mine if dig else hit.place
	if not world.contains_cell(cell):
		status.text="已到地形边界"
		return false
	if not world.ready_at(cell):
		world.prepare_at(cell)
		status.text="正在准备此处地面，完成后即可挖掘"
		return false
	var changed: bool=toolkit.mine_cell(cell) if dig else world.place(cell,selected,player_bounds())
	if changed:
		save_delay=0.5
		foliage_dirty=true
		status.text=toolkit.mining_message if dig else "已填充 / 搭建"
	return changed

func _physics_process(delta: float) -> void:
	if world.loading:
		hint_label.text="正在恢复旷野地形…"
		return
	if initial_restore and world.jobs.is_empty():
		initial_restore=false
		foliage_dirty=true
		hint_label.text="B 建造 · 6 伐木斧 · 7 矿镐 · F7 返回武器"
	if hint_label.text=="正在恢复旷野地形…" and world.jobs.is_empty(): hint_label.text="B 建造 · 6 伐木斧 · 7 矿镐 · F7 返回武器"
	mine_delay-=delta
	if enabled and Input.mouse_mode==Input.MOUSE_MODE_CAPTURED:
		if Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT) and mine_delay<=0:
			act(true)
			mine_delay=0.22
		var hit:=target()
		preview.visible=not hit.is_empty() and world.jobs.is_empty()
		if preview.visible:
			preview.global_position=Vector3(hit.place)+Vector3.ONE*0.5
			preview_material.albedo_color=Color(0.3,0.9,0.45,0.24) if world.can_place(hit.place,selected,player_bounds()) else Color(1,0.2,0.2,0.24)
	else: preview.visible=false
	if save_delay>=0:
		save_delay-=delta
		if save_delay<0: _save()
	if foliage_dirty and world.jobs.is_empty() and save_delay<0:
		_refresh_foliage()
		foliage_dirty=false
	info.text="手持：%s · 木材 %d\n当前填充：%s\n泥土 %d · 岩石 %d · 矿石 %d · 砖 %d" % [toolkit.NAMES[toolkit.equipped],toolkit.wood,["","泥土","岩石","矿石","建筑砖"][selected],world.stock[1],world.stock[2],world.stock[3],world.stock[4]]
	if world.jobs.is_empty() and status.text=="正在准备此处地面，完成后即可挖掘": status.text="地面已就绪，可以挖掘或填充"

func harvest_ground_cell(cell: Vector3i) -> bool:
	var kind: int=world.get_cell(cell)
	var item_id: String=GROUND_REWARDS.get(kind,"")
	if item_id.is_empty(): return false
	var building:=scene.get_node_or_null("BuildingSystem")
	if building!=null:
		var foundation_error: String=building.terrain_excavation_error(cell)
		if not foundation_error.is_empty():
			status.text=foundation_error
			return false
	var hud:=get_node_or_null("/root/HUD")
	var backpack: RefCounted=hud.backpack if hud!=null else null
	if backpack==null:
		status.text="背包尚未就绪"
		return false
	var old_slots: Array=backpack.slots.duplicate(true)
	if not backpack.add_item(item_id,1):
		status.text="背包空间不足，请整理后继续采集"
		return false
	if not world.mine(cell):
		_restore_backpack(backpack,old_slots)
		return false
	# Terrain and inventory are one harvest transaction. Save terrain first;
	# if either side fails, undo the edit and restore the previous backpack.
	var terrain_error: Error=world.save_world(save_path)
	if terrain_error!=OK:
		world.undo_edit(AABB(Vector3(10000,10000,10000),Vector3.ONE))
		_restore_backpack(backpack,old_slots)
		status.text="地形保存失败，本次采集已撤销"
		return false
	var inventory_error: Error=hud.save_inventory()
	if inventory_error!=OK:
		world.undo_edit(AABB(Vector3(10000,10000,10000),Vector3.ONE))
		var rollback_error: Error=world.save_world(save_path)
		_restore_backpack(backpack,old_slots)
		status.text="背包保存失败，本次采集已撤销" if rollback_error==OK else "采集回滚保存失败，请立即返回标题"
		return false
	save_delay=-1.0
	foliage_dirty=true
	return true

func _restore_backpack(backpack: RefCounted, old_slots: Array) -> void:
	backpack.slots=old_slots
	backpack.changed.emit()

func respawn() -> void:
	if player==null: return
	var at: Vector2=scene.ARRIVAL
	var surface: float=world.natural_height(at.x,at.y)
	var hit:=get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(Vector3(at.x,190,at.y),Vector3(at.x,-64,at.y),1))
	if not hit.is_empty(): surface=hit.position.y
	player.global_position=Vector3(at.x,surface+2.5,at.y)
	player.velocity=Vector3.ZERO

func _save() -> void:
	var result: Error=world.save_world(save_path)
	if result==OK: result=toolkit.save_state()
	status.text="旷野改造已保存" if result==OK else "保存失败："+error_string(result)
	save_delay=-1.0

func _refresh_foliage() -> void:
	toolkit.rocks.apply_saved()
	var mask:=grass_base.duplicate()
	for p in world.soil_scars:
		var center:=Vector2i(roundi((p.x+512.0)*2),roundi((p.y+512.0)*2))
		for z in range(-4,5):
			for x in range(-4,5):
				var pixel:=center+Vector2i(x,z)
				if x*x+z*z<=16 and pixel.x>=0 and pixel.y>=0 and pixel.x<2048 and pixel.y<2048: mask.set_pixelv(pixel,Color.WHITE)
	grass_texture.update(mask)
	for record in foliage:
		var mm: MultiMesh=record[0].multimesh
		for i in record[1].size():
			var original: Transform3D=record[2][i]
			var p: Vector3=record[1][i].origin
			var removed: bool=record[0].get_meta("quarried_indices",{}).has(i) or _root_removed(p)
			mm.set_instance_transform(i,Transform3D(Basis.IDENTITY.scaled(Vector3.ONE*0.00001),Vector3(0,-10000,0)) if removed else original)
	for child in scene.get_children():
		if child is StaticBody3D and (child.has_meta("landscape_asset") or child.has_meta("terrain_support_root")):
			var removed: bool=child.get_meta("tool_felled",false) or child.get_meta("tool_quarried",false) or _root_removed(child.get_meta("terrain_support_root",child.global_position))
			child.visible=not removed
			for shape in child.find_children("","CollisionShape3D",true,false): shape.set_deferred("disabled",removed)

func _root_removed(p: Vector3) -> bool:
	var point:=Vector3(p.x,world.natural_height(p.x,p.z)-0.15,p.z)
	for cell in world.edits:
		if Vector2(cell.x-p.x,cell.z-p.z).length_squared()<6.0:
			return world.density(point)>0.05
	return false

func _exit_tree() -> void:
	# 子节点已经退树；世界自行保存，此处只恢复共享玩家与武器。
	if is_instance_valid(player): player.set_meta("terrain_editing",false)
	if enabled and is_instance_valid(gun):
		gun.process_mode=gun_mode
		gun.visible=gun_visible
