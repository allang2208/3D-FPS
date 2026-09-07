extends Node3D
## Starter tools for the voxel prototype. Resources stay outside the RPG economy.
const MODELS = {"axe":preload("res://assets/models/basic_tools/axe_v1.glb"), "pickaxe":preload("res://assets/models/basic_tools/pickaxe_v1.glb")}
const NAMES = {"":"空手", "axe":"伐木斧", "pickaxe":"矿镐"}
const REACH := 3.2
const CONTACT := 0.24
const DURATION := 0.68
var editor: Node3D
var equipped := ""
var owned := {"axe":true, "pickaxe":true}
var wood := 0
var felled: Dictionary = {}
var tree_hits: Dictionary = {}
var resolving := false
var elapsed := -1.0
var contacted := false
var active := true
var pivot: Node3D
var models: Dictionary = {}
var state_path := ""
var save_allowed := true
var tree_effects: Dictionary={}
var mining_hits: Dictionary={}
var mining_contact: Dictionary={}
var mining_message:=""
var mining_cracks: Array[Node3D]=[]
var rocks=preload("res://scripts/tools/scenic_rock_harvest.gd").new()

func setup(host: Node3D) -> void:
	editor=host
	rocks.toolkit=self
	state_path=editor.save_path+".tools-v1.json"
	pivot=Node3D.new()
	editor.camera.add_child(pivot)
	pivot.position=Vector3(0.34,-0.34,-0.64)
	for kind in MODELS:
		var model: Node3D=MODELS[kind].instantiate()
		pivot.add_child(model)
		orient_model(model,kind)
		model.visible=false
		models[kind]=model
	var loaded:=load_state()
	if loaded!=OK and loaded!=ERR_FILE_NOT_FOUND:
		editor.status.text="工具存档损坏，原文件保留，本次不能保存砍伐"
	apply_felled()
	editor.info.get_parent().get_child(2).text+="\nE 收集准星处的木段"

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and (event.keycode==KEY_F9 or (event.ctrl_pressed and event.keycode==KEY_Z)):
		mining_hits.clear()
		rocks.hits.clear()
	if active and event is InputEventKey and event.pressed and not event.echo and event.keycode==KEY_E and Input.mouse_mode==Input.MOUSE_MODE_CAPTURED:
		collect_target()
		get_viewport().set_input_as_handled()

func collect_target() -> bool:
	if not active: return false
	var cam: Camera3D=editor.camera
	var query:=PhysicsRayQueryParameters3D.create(cam.global_position,cam.global_position-cam.global_basis.z*REACH,1)
	var hit:=editor.get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty() or not hit.collider.has_meta("wood_pickup"): return false
	var id: String=hit.collider.get_meta("tree_key")
	if not tree_effects.has(id): return false
	return tree_effects[id].collect(hit.collider.get_meta("log_index"))

func equip(kind: String) -> bool:
	if kind!="" and not owned.get(kind,false): return false
	cancel()
	equipped=kind
	for id in models: models[id].visible=active and id==kind
	return true

func set_active(value: bool) -> void:
	active=value
	cancel()
	if is_instance_valid(pivot): pivot.visible=value
	for id in models: models[id].visible=value and id==equipped

func cancel() -> void:
	elapsed=-1
	resolving=false
	if is_instance_valid(pivot): pivot.rotation=Vector3.ZERO

func begin_use() -> bool:
	if not active or elapsed>=0: return false
	if equipped=="" or not owned.get(equipped,false):
		editor.status.text="需要装备工具：6 伐木斧 / 7 矿镐"
		return false
	elapsed=0
	contacted=false
	return true

func allows_ground() -> bool:
	return active and equipped=="pickaxe" and owned.get("pickaxe",false)

func _process(delta: float) -> void:
	if elapsed<0: return
	if not active or Input.mouse_mode!=Input.MOUSE_MODE_CAPTURED:
		cancel()
		return
	elapsed+=delta
	update_pose(elapsed)
	if elapsed>=CONTACT and not contacted:
		contacted=true
		resolve_contact()
	if elapsed>=DURATION: cancel()

static func orient_model(model: Node3D, kind: String) -> void:
	if kind=="pickaxe":
		# The imported head spans local X. Turn it into the forward/down swing plane.
		model.basis=Basis.from_euler(Vector3(deg_to_rad(-12),0,deg_to_rad(-24)))*Basis(Vector3.UP,PI*0.5)
	else:
		model.rotation_degrees=Vector3(-12,25,-24)

func update_pose(time: float) -> void:
	# Fresh tool action: brief backswing, angled downward contact, slower recovery.
	var angle: float
	if time<CONTACT:
		angle=lerpf(-0.45,0.95,pow(time/CONTACT,2.0))
	else:
		angle=lerpf(0.95,0.0,smoothstep(CONTACT,DURATION,time))
	pivot.rotation=Vector3(-angle,0.0,angle*0.26)

func resolve_contact() -> bool:
	if not active or not owned.get(equipped,false): return false
	var cam: Camera3D=editor.camera
	var query:=PhysicsRayQueryParameters3D.create(cam.global_position,cam.global_position-cam.global_basis.z*REACH,1)
	var hit:=editor.get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty(): return false
	var body: Node=hit.collider
	if is_tree(body):
		if equipped!="axe":
			editor.status.text="砍树需要伐木斧（6）"
			return false
		return chop(body,hit.position,hit.normal)
	if not allows_ground():
		editor.status.text="泥土、岩石和矿石需要矿镐（7）"
		return false
	if body.has_meta("rock_source"):
		return rocks.strike(body,hit.position,hit.normal)
	mining_contact=hit
	resolving=true
	var changed: bool=editor.act(true)
	resolving=false
	return changed

func mine_cell(cell: Vector3i) -> bool:
	if not allows_ground(): return false
	var kind: int=editor.world.get_cell(cell)
	mining_message="已挖掘，材料已收入背包"
	if kind!=2 and kind!=3: return _mine_ground(cell)
	if not mining_hits.has(cell): mining_hits.clear()
	var count: int=mining_hits.get(cell,0)+1
	mining_hits[cell]=count
	var at: Vector3=mining_contact.get("position",editor.world.to_global(Vector3(cell)+Vector3.ONE*0.5))
	var normal: Vector3=mining_contact.get("normal",Vector3.UP)
	if count<3:
		var tap:=preload("res://scripts/tools/ore_break_fx.gd").new()
		editor.add_child(tap)
		tap.strike(at,normal,count,kind==3,false)
		mining_cracks.append(tap)
		mining_cracks=mining_cracks.filter(is_instance_valid)
		editor.status.text="%s采集 %d / 3" % ["矿石" if kind==3 else "岩石",count]
		return false
	if not _mine_ground(cell): return false
	mining_hits.erase(cell)
	for tap in mining_cracks:
		if is_instance_valid(tap) and is_instance_valid(tap.crack): tap.crack.hide()
	mining_cracks.clear()
	var burst:=preload("res://scripts/tools/ore_break_fx.gd").new()
	editor.add_child(burst)
	burst.strike(at,normal,3,kind==3,true)
	mining_message="%s已爆裂，材料已回收" % ("矿石" if kind==3 else "岩石")
	return true

func _mine_ground(cell: Vector3i) -> bool:
	# The standalone voxel lab keeps its isolated stock. Formal wilderness
	# exposes an atomic terrain + backpack harvest entry point instead.
	if editor.has_method("harvest_ground_cell"):
		return editor.harvest_ground_cell(cell)
	return editor.world.mine(cell)

static func is_tree(body: Node) -> bool:
	return body is StaticBody3D and body.has_meta("landscape_asset") and body.get_meta("impact_surface","")=="wood"

static func tree_id(body: Node3D) -> String:
	var p:=body.global_position
	return "%s:%.3f:%.3f:%.3f" % [body.get_meta("landscape_asset",""),p.x,p.y,p.z]

func chop(body: Node3D, contact_point:=Vector3.INF, contact_normal:=Vector3.UP) -> bool:
	if not active or equipped!="axe" or not owned.get("axe",false) or not is_tree(body): return false
	var id:=tree_id(body)
	if felled.has(id): return false
	var count: int=tree_hits.get(id,0)+1
	tree_hits[id]=count
	if count<3:
		var fx:=preload("res://scripts/tools/tree_felling.gd").new()
		editor.add_child(fx)
		fx.set_process(false)
		var at: Vector3=contact_point if contact_point.is_finite() else body.global_position+Vector3.UP*0.65
		fx.burst(at,false)
		fx.sound("res://assets/sfx/kenney_impact/impactWood_medium_000.ogg",at,1.0)
		fx.create_tween().tween_interval(1.5).finished.connect(fx.queue_free)
		if contact_point.is_finite():
			var scar:=MeshInstance3D.new()
			scar.set_meta("harvest_scar",true)
			var patch:=SphereMesh.new()
			patch.radius=0.07+count*0.025
			patch.height=0.018
			scar.mesh=patch
			var material:=StandardMaterial3D.new()
			material.albedo_color=Color(0.48,0.29,0.12)
			scar.material_override=material
			body.add_child(scar)
			scar.global_position=contact_point+contact_normal*0.004
			scar.global_basis=Basis(Quaternion(Vector3.UP,contact_normal.normalized()))
		editor.status.text="砍伐 %d / 3" % count
		return true
	var away: Vector3=body.global_position-editor.camera.global_position
	away.y=0
	if away.is_zero_approx(): away=-editor.camera.global_basis.z
	away=away.normalized()
	felled[id]={"direction":[away.x,0.0,away.z],"remaining":[0,1,2,3]}
	_start_fall(body,id,false)
	_hide_tree(body)
	editor.status.text="树干断裂，正在倾倒；落地后按 E 收集木段"
	var result:=save_state()
	if result!=OK: editor.status.text="砍伐保存失败："+error_string(result)
	return true

func _start_fall(body: StaticBody3D, id: String, restored: bool) -> void:
	if tree_effects.has(id): return
	var effect:=preload("res://scripts/tools/tree_felling.gd").new()
	editor.get_parent().add_child(effect)
	var d: Array=felled[id].direction
	effect.setup(body,self,id,Vector3(d[0],d[1],d[2]),restored)
	tree_effects[id]=effect

func _hide_tree(body: Node3D) -> void:
	body.set_meta("tool_felled",true)
	body.hide()
	for shape in body.find_children("","CollisionShape3D",true,false): shape.set_deferred("disabled",true)

func apply_felled() -> void:
	if editor==null: return
	for body in editor.get_parent().get_children():
		if is_tree(body) and felled.has(tree_id(body)):
			_start_fall(body,tree_id(body),true)
			_hide_tree(body)

func save_state() -> Error:
	if not save_allowed: return ERR_FILE_CORRUPT
	var file:=FileAccess.open(state_path+".tmp",FileAccess.WRITE)
	if file==null: return FileAccess.get_open_error()
	file.store_string(JSON.stringify({"version":2,"wood":wood,"felled":felled,"owned":owned}))
	file.close()
	return DirAccess.rename_absolute(state_path+".tmp",state_path)

func load_state() -> Error:
	if not FileAccess.file_exists(state_path): return ERR_FILE_NOT_FOUND
	var data: Variant=JSON.parse_string(FileAccess.get_file_as_string(state_path))
	if not data is Dictionary or (data.get("version")!=1 and data.get("version")!=2) or not data.get("wood") is float or data.wood<0 or data.wood!=floor(data.wood) or not data.get("felled") is Dictionary or not data.get("owned") is Dictionary:
		save_allowed=false
		return ERR_FILE_CORRUPT
	for id in data.felled:
		var record: Variant=data.felled[id]
		if data.version==1 and record==true:
			data.felled[id]={"direction":[0.0,0.0,-1.0],"remaining":[]}
			continue # old saves already received all four wood units
		if not id is String or not record is Dictionary or not record.get("direction") is Array or record.direction.size()!=3 or not record.get("remaining") is Array:
			save_allowed=false
			return ERR_FILE_CORRUPT
		for value in record.direction:
			if not (value is float or value is int) or not is_finite(value):
				save_allowed=false
				return ERR_FILE_CORRUPT
		var seen: Array=[]
		for value in record.remaining:
			if not (value is float or value is int) or value!=floor(value) or value<0 or value>3 or seen.has(int(value)):
				save_allowed=false
				return ERR_FILE_CORRUPT
			seen.append(int(value))
		record.remaining=seen
	for kind in ["axe","pickaxe"]:
		if not data.owned.get(kind) is bool:
			save_allowed=false
			return ERR_FILE_CORRUPT
	wood=int(data.wood)
	felled=data.felled
	owned=data.owned
	return OK

func _exit_tree() -> void:
	if is_instance_valid(pivot): pivot.queue_free()
	for effect in tree_effects.values():
		if is_instance_valid(effect): effect.queue_free()
