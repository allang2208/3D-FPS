extends Node3D
const Grid := preload("res://scripts/building/block_grid.gd")
const Supports := preload("res://scripts/building/support_graph.gd")
const Save := preload("res://ui/inventory_save.gd")
const Style := preload("res://ui/style.gd")
const Costs := preload("res://scripts/building/build_costs.gd")
const Railing := preload("res://scripts/building/railing_component.gd")
const Door := preload("res://scripts/building/door_component.gd")
const PieceBody := preload("res://scripts/building/build_piece_body.gd")
const Catalog := preload("res://scripts/building/build_piece_catalog.gd")
const HISTORY_LIMIT := 64
var cells := {}
var anchors := {}
var nodes := {}
var rotations := {}
var occupied := {}
var health := {}
var states := {}
var materials := {}
var active := false
var kind := "wood"
var rotation_quarters := 0
var snap_enabled := true
var menu: CanvasLayer
var ghost: Node3D
var ghost_cube: MeshInstance3D
var ghost_railing: Node3D
var ghost_door: Node3D
var ghost_mat: StandardMaterial3D
var hint: Label
var _aim := {}
var _candidate := Vector3i.ZERO
var _reason := ""
var _cooldown := 0.0
var _wood_meshes := preload("res://scripts/building/wood_block_mesh.gd").new()
var _rail_accent: Material
var _health_save_timer: Timer
var _undo_stack: Array[Dictionary]=[]
var _redo_stack: Array[Dictionary]=[]
var player_override: Node3D
var allow_terrain_anchors := false
var minimum_cell := Vector3i(-30,0,-30)
var maximum_cell := Vector3i(102,16,30)
var sidecar_suffix := ".sky-building"
var terrain_source: Node

func _ready() -> void:
	name="BuildingSystem"
	var wood := preload("res://scripts/building/generated_wood_material.gd").create(false)
	materials["wood"] = wood
	materials["floor"] = wood
	materials["ceiling"] = wood
	# Legacy wall rows keep their authored upright grain after loading old saves.
	materials["wall"] = preload("res://scripts/building/generated_wood_material.gd").create(true)
	var stone := preload("res://scripts/building/stone_material.gd").create()
	materials["marble"] = preload("res://scripts/building/marble_material.gd").create()
	for key in ["stone","stone_floor","stone_wall","stone_ceiling"]:
		materials[key]=stone
	materials["railing"] = preload("res://scripts/building/railing_material.gd").create_body()
	_rail_accent = preload("res://scripts/building/railing_material.gd").create_accent()
	_ensure_input_actions()
	menu=load("res://scripts/building/build_panel.gd").new()
	add_child(menu)
	menu.build_requested.connect(func(choice: String):
		kind=choice
		set_active(true))
	menu.stop_requested.connect(func(): set_active(false))
	ghost=Node3D.new()
	add_child(ghost)
	ghost_cube=MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size=Vector3.ONE*.502
	ghost_cube.mesh=mesh
	ghost_mat=StandardMaterial3D.new()
	ghost_mat.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA
	ghost_mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
	ghost_cube.material_override=ghost_mat
	ghost_cube.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	ghost.add_child(ghost_cube)
	ghost_railing=Railing.make_visual(ghost_mat,ghost_mat)
	ghost.add_child(ghost_railing)
	ghost_door=Door.make_preview(ghost_mat,ghost_mat,ghost_mat)
	ghost.add_child(ghost_door)
	ghost_door.hide()
	ghost.hide()
	_health_save_timer=Timer.new()
	_health_save_timer.one_shot=true
	_health_save_timer.wait_time=.25
	_health_save_timer.timeout.connect(func(): persist())
	add_child(_health_save_timer)
	var layer := CanvasLayer.new()
	layer.layer=6
	add_child(layer)
	hint=Label.new()
	hint.theme=Style.make_theme()
	Style.apply_text_role(hint,&"body")
	hint.position=Vector2(20,80)
	hint.add_theme_stylebox_override("normal",Style.make_style(Style.COLOR_PANEL_BG,Style.COLOR_PANEL_BORDER,6,1))
	layer.add_child(hint)
	hint.hide()
	call_deferred("restore_building")

func player() -> Node3D:
	if is_instance_valid(player_override): return player_override
	var value: Variant=_property_value(get_parent(),"player")
	if is_instance_valid(value): return value
	value=_property_value(get_parent(),"_player")
	return value if is_instance_valid(value) else null

func gun() -> Node:
	var host_gun: Variant=_property_value(get_parent(),"_gun")
	if is_instance_valid(host_gun): return host_gun
	var current_player:=player()
	return current_player.get_node_or_null("Camera3D/Gun") if is_instance_valid(current_player) else null

func status_bar() -> Node:
	var value: Variant=_property_value(get_parent(),"_status_bar")
	return value if is_instance_valid(value) else null

func _property_value(object: Object, property_name: String) -> Variant:
	for property in object.get_property_list():
		if property.name==property_name: return object.get(property_name)
	return null

func _set_gun_blocked(value: bool) -> void:
	var current_gun:=gun()
	if not is_instance_valid(current_gun): return
	for property in current_gun.get_property_list():
		if property.name=="building_input_blocked":
			current_gun.set("building_input_blocked",value)
			return

func set_active(value: bool) -> void:
	if value:
		var ground_editor:=get_parent().get_node_or_null("WildernessEditor")
		if ground_editor!=null and ground_editor.has_method("set_enabled"): ground_editor.set_enabled(false)
	active=value
	_set_gun_blocked(value)
	ghost.visible=false
	hint.visible=value

func _exit_tree() -> void:
	if _health_save_timer!=null and not _health_save_timer.is_stopped(): persist()
	_set_gun_blocked(false)

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode==KEY_B:
			var ground_editor:=get_parent().get_node_or_null("WildernessEditor")
			if ground_editor!=null and ground_editor.has_method("set_enabled"): ground_editor.set_enabled(false)
			if menu.is_open(): menu.close()
			elif Input.mouse_mode==Input.MOUSE_MODE_CAPTURED: menu.open_panel()
			get_viewport().set_input_as_handled()
		elif event.keycode==KEY_ESCAPE and (active or menu.is_open()):
			if menu.is_open(): menu.close()
			set_active(false)
			get_viewport().set_input_as_handled()
	if not active or menu.is_open() or Input.mouse_mode!=Input.MOUSE_MODE_CAPTURED: return
	if event.is_action_pressed("build_undo") or event.is_action_pressed("build_redo"):
		var history_message:=redo_last() if event.is_action_pressed("build_redo") else undo_last()
		get_viewport().set_input_as_handled()
		var bar:=status_bar()
		if is_instance_valid(bar): bar.show_status(history_message,1.5)
		return
	if event.is_action_pressed("build_toggle_snap"):
		snap_enabled = not snap_enabled
		get_viewport().set_input_as_handled()
		update_aim()
		return
	if event.is_action_pressed("build_rotate_previous") or event.is_action_pressed("build_rotate_next"):
		rotation_quarters=wrapi(rotation_quarters+(-1 if event.is_action_pressed("build_rotate_previous") else 1),0,4)
		get_viewport().set_input_as_handled()
		update_aim()
		return
	if event is InputEventMouseButton and event.pressed and event.button_index in [MOUSE_BUTTON_LEFT,MOUSE_BUTTON_RIGHT]:
		get_viewport().set_input_as_handled()
		if _cooldown>0: return
		_cooldown=.15
		update_aim()
		var message := "请瞄准 6 米内的地基或方块"
		if not _aim.is_empty():
			if event.button_index==MOUSE_BUTTON_LEFT:
				message=place(_candidate,kind)
			elif _aim.collider.has_meta("built_cell"):
				message=remove_block(_aim.collider.get_meta("built_cell"))
			else: message="只能拆除自己搭建的方块"
		var bar:=status_bar()
		if is_instance_valid(bar): bar.show_status(message if not message.is_empty() else "建筑已保存",1.5)

func _process(delta: float) -> void:
	_cooldown=maxf(0,_cooldown-delta)
	_set_gun_blocked(active)
	var visible_build: bool = active and not menu.is_open() and Input.mouse_mode==Input.MOUSE_MODE_CAPTURED
	hint.visible=visible_build
	ghost.visible=false
	if not visible_build: return
	update_aim()
	var angle := resolved_rotation(_candidate)*90
	var snap_text := "吸附" if snap_enabled else "手动"
	var target_health := ""
	if not _aim.is_empty() and _aim.collider!=null and _aim.collider.has_method("health_text"):
		target_health=" · 耐久 "+_aim.collider.health_text()
	hint.text="左键放置 · 右键拆除/退款 · Ctrl+Z/Y 撤销/重做 · 滚轮旋转 · F %s  |  %s · %d° · %s%s" % ["取消吸附" if snap_enabled else "开启吸附",snap_text,angle,"可放置" if _reason.is_empty() else _reason,target_health]
	if _aim.is_empty(): return
	ghost.position=Grid.cell_center(_candidate)
	ghost.rotation.y=resolved_rotation(_candidate)*PI*.5
	ghost_cube.visible=kind not in ["railing","door"]
	ghost_railing.visible=kind=="railing"
	ghost_door.visible=kind=="door"
	var color: Color=Style.THEME_HP_GREEN if _reason.is_empty() else Style.THEME_DANGER_RED
	color.a=.3
	ghost_mat.albedo_color=color
	ghost.show()

func update_aim() -> void:
	var camera: Camera3D=player().get_node("Camera3D")
	var start:=camera.global_position
	var query:=PhysicsRayQueryParameters3D.create(start,start-camera.global_basis.z*6,3,[player().get_rid()])
	_aim=get_world_3d().direct_space_state.intersect_ray(query)
	_reason="请瞄准地基或已有方块"
	if not _aim.is_empty():
		_candidate=_candidate_from_hit(_aim)
		_reason=placement_error(_candidate,kind,resolved_rotation(_candidate))
		if _reason.is_empty(): _reason=Costs.error(self,kind)

func _candidate_from_hit(hit: Dictionary) -> Vector3i:
	if allow_terrain_anchors and _is_terrain_ground(hit.collider):
		# A Terrain3D triangle may cut through the cell containing the ray point.
		# Sample the four footprint corners and snap above the highest one so a
		# gentle slope does not intersect the flat building collision.
		var x_cell:=floori(hit.position.x/Grid.CELL_SIZE)
		var z_cell:=floori(hit.position.z/Grid.CELL_SIZE)
		var surface_y: float=hit.position.y
		if terrain_source is Terrain3D and hit.collider==terrain_source:
			for x_offset in [.05,.45]:
				for z_offset in [.05,.45]:
					var sample: float=terrain_source.data.get_height(Vector3(x_cell*Grid.CELL_SIZE+x_offset,0,z_cell*Grid.CELL_SIZE+z_offset))
					if is_finite(sample): surface_y=maxf(surface_y,sample)
		return Vector3i(x_cell,ceili((surface_y-.001)/Grid.CELL_SIZE),z_cell)
	return Grid.world_to_cell(hit.position+hit.normal*.01)

func _is_terrain_ground(collider: Object) -> bool:
	return allow_terrain_anchors and collider!=null and (collider==terrain_source or collider.has_meta("voxel_chunk"))

func _ensure_input_actions() -> void:
	_add_input_action(&"build_toggle_snap",KEY_F,0)
	_add_input_action(&"build_rotate_previous",KEY_NONE,MOUSE_BUTTON_WHEEL_UP)
	_add_input_action(&"build_rotate_next",KEY_NONE,MOUSE_BUTTON_WHEEL_DOWN)
	_add_input_action(&"build_undo",KEY_Z,0,true)
	_add_input_action(&"build_redo",KEY_Y,0,true)

func _add_input_action(action: StringName, keycode: Key, mouse_button: MouseButton, ctrl_pressed := false) -> void:
	if InputMap.has_action(action): return
	InputMap.add_action(action)
	if keycode!=KEY_NONE:
		var key := InputEventKey.new()
		key.keycode=keycode
		key.ctrl_pressed=ctrl_pressed
		InputMap.action_add_event(action,key)
	else:
		var mouse := InputEventMouseButton.new()
		mouse.button_index=mouse_button
		InputMap.action_add_event(action,mouse)

func resolved_rotation(cell: Vector3i, choice: String = "") -> int:
	var actual_choice := kind if choice.is_empty() else choice
	var definition:=Catalog.definition(actual_choice)
	if definition==null or not definition.snaps_to_same_kind or not snap_enabled: return rotation_quarters
	# A railing cell is a graph node. The stored angle supplies the isolated/end
	# direction; once neighbors exist their four-way mask authors the junction.
	for direction in [Vector3i.LEFT,Vector3i.RIGHT]:
		var neighbor_x: Vector3i=cell+direction
		if cells.get(neighbor_x,"")==actual_choice: return 0
	for direction in [Vector3i.FORWARD,Vector3i.BACK]:
		var neighbor_z: Vector3i=cell+direction
		if cells.get(neighbor_z,"")==actual_choice: return 1
	return rotation_quarters

func is_anchor(cell: Vector3i) -> bool:
	var center:=Grid.cell_center(cell)
	if allow_terrain_anchors:
		var bottom:=cell.y*Grid.CELL_SIZE
		for x in [-.20,.20]:
			for z in [-.20,.20]:
				var start:=Vector3(center.x+x,bottom+.06,center.z+z)
				var query:=PhysicsRayQueryParameters3D.create(start,start-Vector3.UP*1.06,1,[player().get_rid()])
				var hit:=get_world_3d().direct_space_state.intersect_ray(query)
				if hit.is_empty() or not _is_terrain_ground(hit.collider): return false
		return true
	if cell.y!=0: return false
	for x in [-.20,.20]:
		for z in [-.20,.20]:
			var start:=Vector3(center.x+x,.05,center.z+z)
			var hit:=get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(start,start-Vector3.UP*.12,1))
			if hit.is_empty() or not hit.collider.has_meta("build_foundation"): return false
	return true

func is_piece_anchor(cell: Vector3i, choice: String, orientation: int) -> bool:
	var definition:=Catalog.definition(choice)
	if definition==null: return false
	var bottom:=Catalog.bottom_offsets(choice,orientation)
	if bottom.is_empty(): return false
	if not definition.requires_full_base_support: return is_anchor(cell)
	for offset in bottom:
		if not is_anchor(cell+offset): return false
	return true

func terrain_excavation_error(edit_cell: Vector3i) -> String:
	if not allow_terrain_anchors: return ""
	var edit_center:=Vector3(edit_cell)+Vector3.ONE*.5
	for root in anchors:
		if not cells.has(root): continue
		for offset in Catalog.bottom_offsets(str(cells[root]),int(rotations.get(root,0))):
			var foot_cell: Vector3i=root+offset
			var foot:=Grid.cell_center(foot_cell)-Vector3.UP*Grid.CELL_SIZE*.5
			if Vector2(foot.x-edit_center.x,foot.z-edit_center.z).length()<=1.25 and absf(foot.y-edit_center.y)<=1.10:
				return "该处承托着建筑，请先拆除上方构件"
	return ""

func placement_error(cell: Vector3i, choice: String = "", orientation: int = -1) -> String:
	var actual_choice := kind if choice.is_empty() else choice
	var definition:=Catalog.definition(actual_choice)
	if definition==null: return "未知构件"
	var resolved_orientation: int=resolved_rotation(cell,actual_choice) if orientation<0 else wrapi(orientation,0,4)
	var slots:=Catalog.occupied_offsets(actual_choice,resolved_orientation)
	if occupied.size()+slots.size()>1024: return "已达到 1024 格上限"
	for offset in slots:
		var slot: Vector3i=cell+offset
		if occupied.has(slot): return "目标空间已有构件"
		if slot.x<minimum_cell.x or slot.x>=maximum_cell.x or slot.y<minimum_cell.y or slot.y>=maximum_cell.y or slot.z<minimum_cell.z or slot.z>=maximum_cell.z:
			return "超出当前地图建造范围"
	var box:=BoxShape3D.new()
	box.size=definition.collision_size-Vector3.ONE*.02
	var query:=PhysicsShapeQueryParameters3D.new()
	query.shape=box
	var placement_basis:=Basis(Vector3.UP,resolved_orientation*PI*.5)
	var center: Vector3=Grid.cell_center(cell)+placement_basis*definition.collision_center
	query.transform=Transform3D(placement_basis,center)
	query.collision_mask=7
	if not get_world_3d().direct_space_state.intersect_shape(query,1).is_empty(): return "与角色或现有场景重叠"
	var trial:=cells.duplicate()
	trial[cell]=actual_choice
	var trial_rotations:=rotations.duplicate()
	trial_rotations[cell]=resolved_orientation
	var roots:=anchors.duplicate()
	if is_piece_anchor(cell,actual_choice,resolved_orientation): roots[cell]=true
	if not Supports.supported(trial,roots,trial_rotations).has(cell): return "缺少承重支撑，或悬挑超过 2 米"
	return ""

func place(cell: Vector3i, choice: String, orientation := -1, record_history := true) -> String:
	var resolved_orientation: int=resolved_rotation(cell,choice) if orientation<0 else wrapi(orientation,0,4)
	var definition:=Catalog.definition(choice)
	if definition==null: return "未知构件"
	return _place_snapshot({
		"cell":cell,
		"kind":choice,
		"rotation":resolved_orientation,
		"health":definition.max_health,
		"state":{},
	},record_history)

func _place_snapshot(snapshot: Dictionary, record_history: bool) -> String:
	var cell: Vector3i=snapshot.cell
	var choice: String=str(snapshot.kind)
	var orientation: int=wrapi(int(snapshot.get("rotation",0)),0,4)
	var reason:=placement_error(cell,choice,orientation)
	if not reason.is_empty(): return reason
	reason=Costs.error(self,choice)
	if not reason.is_empty(): return reason
	var bp:=Costs.stock(self)
	var old_slots: Array=bp.slots.duplicate(true)
	var amount:=Costs.amount_for(choice)
	if bp.take_items(Costs.item_for(choice),amount)!=amount: return "材料不足"
	_insert_snapshot(snapshot)
	var saved:=persist()
	if saved.is_empty() and _save_inventory_now()!=OK: saved="材料保存失败，已取消放置"
	if not saved.is_empty():
		_erase_piece(cell)
		bp.slots=old_slots
		bp.changed.emit()
		refresh_edges()
		persist()
		return saved
	if record_history: _record_action({"operation":"place","piece":_piece_snapshot(cell)})
	return ""

func _insert_snapshot(snapshot: Dictionary) -> void:
	var cell: Vector3i=snapshot.cell
	var choice: String=str(snapshot.kind)
	var definition:=Catalog.definition(choice)
	var orientation: int=wrapi(int(snapshot.get("rotation",0)),0,4)
	cells[cell]=choice
	rotations[cell]=orientation
	health[cell]=clampi(int(snapshot.get("health",definition.max_health)),1,definition.max_health)
	states[cell]=snapshot.get("state",{}).duplicate(true)
	if is_piece_anchor(cell,choice,orientation): anchors[cell]=true
	_rebuild_occupancy()
	spawn_block(cell,choice)
	refresh_edges()

func spawn_block(cell: Vector3i, choice: String) -> void:
	var orientation: int=int(rotations.get(cell,0))
	var definition:=Catalog.definition(choice)
	var block:=PieceBody.new()
	block.name="%s_%d_%d_%d" % [choice.capitalize(),cell.x,cell.y,cell.z]
	block.position=Grid.cell_center(cell)
	block.rotation.y=orientation*PI*.5
	block.setup(cell,definition.max_health,int(health.get(cell,definition.max_health)))
	block.set_meta("impact_surface",definition.impact_surface)
	match definition.geometry_kind:
		"railing": Railing.add_geometry(block,materials["railing"],_rail_accent)
		"door":
			var controller:=Door.add_geometry(block,materials["railing"],materials["wood"],_rail_accent,bool(states.get(cell,{}).get("open",false)))
			block.bind_state_source(controller)
		_:
			var mesh:=_wood_meshes.for_cell(cell,cells)
			var visual:=MeshInstance3D.new()
			visual.mesh=mesh
			# Old saves may still carry wall/floor/ceiling ids. Retain the
			# authored wall grain while all new panel choices use the unified id.
			var material_id: String=choice if materials.has(choice) else definition.material_key
			visual.material_override=materials[material_id]
			block.add_child(visual)
			var shape:=BoxShape3D.new()
			shape.size=Vector3.ONE*Grid.CELL_SIZE
			var collision:=CollisionShape3D.new()
			collision.shape=shape
			block.add_child(collision)
	block.destroyed.connect(_on_piece_destroyed)
	block.health_changed.connect(_on_piece_health_changed)
	block.state_changed.connect(_on_piece_state_changed)
	nodes[cell]=block
	add_child(block)

func refresh_edges() -> void:
	# Profiles may continue along a whole wall or stair edge. Cached meshes
	# make this update cheap while keeping both sides of every seam identical.
	for cell in nodes:
		var definition:=Catalog.definition(str(cells[cell]))
		if definition!=null and definition.geometry_kind=="cube":
			for child in nodes[cell].get_children():
				if child is MeshInstance3D:
					child.mesh=_wood_meshes.for_cell(cell,cells)
					break
		elif definition!=null and definition.geometry_kind=="railing":
			Railing.rebuild_geometry(nodes[cell],materials["railing"],_rail_accent,Railing.connection_directions(cell,cells))

func remove_block(cell: Vector3i, record_history := true) -> String:
	if not cells.has(cell): return "没有可拆除的方块"
	var trial:=cells.duplicate()
	trial.erase(cell)
	var trial_rotations:=rotations.duplicate()
	trial_rotations.erase(cell)
	var trial_anchors:=anchors.duplicate()
	trial_anchors.erase(cell)
	if Supports.supported(trial,trial_anchors,trial_rotations).size()!=trial.size(): return "拆除会导致结构失去支撑，请先拆上层"
	var snapshot:=_piece_snapshot(cell)
	var bp:=Costs.stock(self)
	if bp==null: return "背包未就绪"
	var old_slots: Array=bp.slots.duplicate(true)
	if not bp.add_item(Costs.item_for(str(snapshot.kind)),Costs.amount_for(str(snapshot.kind))): return "背包空间不足，无法返还材料"
	_erase_piece(cell)
	refresh_edges()
	var saved:=persist()
	if saved.is_empty() and _save_inventory_now()!=OK: saved="材料保存失败，已取消拆除"
	if not saved.is_empty():
		bp.slots=old_slots
		bp.changed.emit()
		_insert_snapshot(snapshot)
		persist()
		return saved
	if record_history: _record_action({"operation":"remove","piece":snapshot})
	return ""

func undo_last() -> String:
	if _undo_stack.is_empty(): return "没有可撤销的建造操作"
	var action: Dictionary=_undo_stack.pop_back()
	var snapshot: Dictionary=action.piece
	var result: String
	if action.operation=="place":
		var cell: Vector3i=snapshot.cell
		if cells.has(cell): action.piece=_piece_snapshot(cell)
		result=remove_block(cell,false)
	else:
		result=_place_snapshot(snapshot,false)
	if not result.is_empty():
		_undo_stack.append(action)
		return "撤销失败："+result
	_redo_stack.append(action)
	return "已撤销上一步"

func redo_last() -> String:
	if _redo_stack.is_empty(): return "没有可重做的建造操作"
	var action: Dictionary=_redo_stack.pop_back()
	var snapshot: Dictionary=action.piece
	var result: String
	if action.operation=="place":
		result=_place_snapshot(snapshot,false)
	else:
		var cell: Vector3i=snapshot.cell
		if cells.has(cell): action.piece=_piece_snapshot(cell)
		result=remove_block(cell,false)
	if not result.is_empty():
		_redo_stack.append(action)
		return "重做失败："+result
	_undo_stack.append(action)
	return "已重做上一步"

func _record_action(action: Dictionary) -> void:
	_undo_stack.append(action.duplicate(true))
	if _undo_stack.size()>HISTORY_LIMIT: _undo_stack.pop_front()
	_redo_stack.clear()

func _clear_history() -> void:
	_undo_stack.clear()
	_redo_stack.clear()

func _piece_snapshot(cell: Vector3i) -> Dictionary:
	return {
		"cell":cell,
		"kind":str(cells[cell]),
		"rotation":int(rotations.get(cell,0)),
		"health":int(health.get(cell,Catalog.definition(str(cells[cell])).max_health)),
		"state":states.get(cell,{}).duplicate(true),
	}

func _save_inventory_now() -> Error:
	var hud=get_node_or_null("/root/HUD")
	return hud.save_inventory() if hud!=null else OK

func _erase_piece(cell: Vector3i) -> void:
	cells.erase(cell)
	rotations.erase(cell)
	health.erase(cell)
	states.erase(cell)
	anchors.erase(cell)
	var block: Node=nodes.get(cell)
	if is_instance_valid(block):
		remove_child(block)
		block.queue_free()
	nodes.erase(cell)
	_rebuild_occupancy()

func _on_piece_health_changed(cell: Vector3i, current: int, _maximum: int) -> void:
	health[cell]=current
	_health_save_timer.start()

func _on_piece_state_changed(cell: Vector3i, state: Dictionary) -> void:
	states[cell]=state.duplicate(true)
	_health_save_timer.start()

func _on_piece_destroyed(cell: Vector3i) -> void:
	if not cells.has(cell): return
	_clear_history()
	_erase_piece(cell)
	var valid:=Supports.supported(cells,anchors,rotations)
	for root in cells.keys():
		if not valid.has(root): _erase_piece(root)
	refresh_edges()
	persist()
	var bar=get_parent().get("_status_bar")
	if is_instance_valid(bar): bar.show_status("建筑构件已损毁",1.5)

func _rebuild_occupancy() -> void:
	occupied=Catalog.build_occupancy(cells,rotations)

func save_path() -> String:
	return Save.resolved_path()+sidecar_suffix

func persist() -> String:
	var rows: Array=[]
	for cell in cells:
		var definition:=Catalog.definition(str(cells[cell]))
		rows.append([cell.x,cell.y,cell.z,cells[cell],int(rotations.get(cell,0)),int(health.get(cell,definition.max_health)),states.get(cell,{})])
	# InventorySave currently accepts version 1 snapshots; the optional fifth row
	# field extends only this sidecar schema without invalidating older four-field rows.
	var error:=Save.write_snapshot({"version":1,"cell_size":Grid.CELL_SIZE,"blocks":rows},save_path())
	return "" if error==OK else "保存失败，当前建筑仅保留在本次场景"

func restore_building() -> void:
	await get_tree().physics_frame
	await get_tree().physics_frame
	var data:=Save.read_snapshot(save_path())
	if data.get("cell_size",0)!=Grid.CELL_SIZE: return
	for row in data.get("blocks",[]):
		if row is Array and row.size()>=4 and Catalog.definition(str(row[3]))!=null:
			var cell:=Vector3i(int(row[0]),int(row[1]),int(row[2]))
			cells[cell]=str(row[3])
			rotations[cell]=wrapi(int(row[4]) if row.size()>=5 else 0,0,4)
			var definition:=Catalog.definition(str(row[3]))
			health[cell]=clampi(int(row[5]) if row.size()>=6 else definition.max_health,1,definition.max_health)
			states[cell]=row[6].duplicate(true) if row.size()>=7 and row[6] is Dictionary else {}
	_rebuild_occupancy()
	for cell in cells:
		if is_piece_anchor(cell,str(cells[cell]),int(rotations.get(cell,0))): anchors[cell]=true
	var valid:=Supports.supported(cells,anchors,rotations)
	for cell in cells.keys():
		if valid.has(cell): spawn_block(cell,cells[cell])
		else:
			cells.erase(cell)
			rotations.erase(cell)
			health.erase(cell)
			states.erase(cell)
	_rebuild_occupancy()
	refresh_edges()
