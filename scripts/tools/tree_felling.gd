extends Node3D
## Authored, terrain-aware fall of the real near mesh, followed by four pickups.
const Cutter=preload("res://scripts/tools/tree_cut_mesh.gd")
const FALL_TIME:=2.4
const SETTLE_TIME:=0.65
const CUT:=0.65
var toolkit: Node
var tree_key: String
var source: StaticBody3D
var direction:=Vector3.FORWARD
var axis:=Vector3.RIGHT
var hinge: Node3D
var crown: Node3D
var stump: StaticBody3D
var logs: Dictionary={}
var clock:=0.0
var landed:=false
var finished:=false
var landing_angle:=PI*0.5
var tree_height:=10.0
var radius:=0.25
var bark: Material
var cut_material: ShaderMaterial

func setup(body: StaticBody3D, owner_kit: Node, id: String, fall_direction: Vector3, restored:=false) -> void:
	source=body
	toolkit=owner_kit
	tree_key=id
	global_transform=body.global_transform
	direction=Vector3(fall_direction.x,0,fall_direction.z).normalized()
	if direction.is_zero_approx(): direction=Vector3.FORWARD
	axis=Vector3.UP.cross(direction).normalized()
	var parts:=Cutter.split_tree(body,CUT)
	tree_height=parts.height
	radius=parts.radius
	bark=parts.bark
	cut_material=ShaderMaterial.new()
	cut_material.shader=preload("res://scripts/tools/tree_wood.gdshader")
	stump=StaticBody3D.new()
	stump.name="CutStump"
	add_child(stump)
	stump.add_child(parts.lower)
	var shape:=CollisionShape3D.new()
	var cylinder:=CylinderShape3D.new()
	cylinder.radius=radius
	cylinder.height=CUT
	shape.shape=cylinder
	shape.position=Vector3(parts.center.x,CUT*0.5,parts.center.z)
	stump.add_child(shape)
	section_cap(stump,parts.contours,true)
	hinge=Node3D.new()
	hinge.position=parts.center
	add_child(hinge)
	crown=parts.upper
	hinge.add_child(crown)
	crown.position=-parts.center
	section_cap(crown,parts.contours,false)
	for sample_angle in range(10,106,2):
		var angle:=deg_to_rad(sample_angle)
		var basis:=Basis(axis,angle)
		var touches:=false
		for fraction in [0.25,0.5,0.75,0.95]:
			var p: Vector3=global_position+Vector3.UP*CUT+basis*(Vector3.UP*(tree_height-CUT)*fraction)
			if p.y-radius*0.65<=ground(p).y: touches=true
		if touches:
			landing_angle=maxf(0.1,angle-deg_to_rad(2))
			break
	if restored:
		clock=FALL_TIME+SETTLE_TIME+0.1
		landed=true
		finish()
	else:
		burst(global_position+Vector3.UP*CUT,false)
		sound("res://assets/sfx/kenney_impact/impactWood_medium_001.ogg",global_position+Vector3.UP*CUT,0.65)

func _process(delta: float) -> void:
	advance(delta)

func advance(delta: float) -> void:
	if finished: return
	clock+=delta
	var t:=clampf(clock/FALL_TIME,0,1)
	# Hinge hesitates first, then accelerates under the crown's weight.
	var angle:=landing_angle*pow(t,2.1)
	if clock>=FALL_TIME:
		var settle:=clock-FALL_TIME
		angle=landing_angle-sin(settle*12)*exp(-settle*7)*0.035
		if not landed:
			landed=true
			var impact:=global_position+direction*(tree_height*0.6)
			impact=ground(impact)
			burst(impact,true)
			sound("res://assets/sfx/kenney_impact/impactWood_medium_000.ogg",impact,0.5)
	hinge.basis=Basis(axis,angle)
	if clock>=FALL_TIME+SETTLE_TIME: finish()

func finish() -> void:
	if finished: return
	finished=true
	hinge.basis=Basis(axis,landing_angle)
	var remaining: Array=toolkit.felled[tree_key].remaining
	for index in remaining: spawn_log(int(index))
	toolkit.editor.status.text="树已倒下，准星对准木段按 E 收集"
	# Crown clears during landing dust; wood is now represented by pickups.
	if is_inside_tree() and clock<FALL_TIME+SETTLE_TIME+0.01:
		var fade:=create_tween()
		for mesh in crown.find_children("","MeshInstance3D",true,false): fade.parallel().tween_property(mesh,"transparency",1.0,0.4)
		fade.chain().tween_callback(hinge.hide)
	else: hinge.hide()
	set_process(false)

func ground(p: Vector3) -> Vector3:
	var query:=PhysicsRayQueryParameters3D.create(Vector3(p.x,global_position.y+tree_height+30,p.z),Vector3(p.x,global_position.y-100,p.z),1)
	query.exclude=[source.get_rid(),stump.get_rid()]
	for log_body in logs.values():
		if is_instance_valid(log_body): query.exclude.append(log_body.get_rid())
	for attempt in 16:
		var hit:=get_world_3d().direct_space_state.intersect_ray(query)
		if hit.is_empty(): break
		if hit.collider is StaticBody3D and hit.collider.has_meta("landscape_asset") and hit.collider.get_meta("impact_surface","")=="wood":
			query.exclude.append(hit.collider.get_rid())
			continue
		return hit.position
	return Vector3(p.x,global_position.y,p.z)

func spawn_log(index: int) -> void:
	var length:=clampf(tree_height*0.13,0.8,1.6)
	var r:=clampf(radius*(1.0-index*0.12),0.10,0.42)
	var center:=global_position+direction*(1.0+index*(length+0.18))
	var a:=ground(center-direction*length*0.5)
	var b:=ground(center+direction*length*0.5)
	var log_body:=StaticBody3D.new()
	log_body.name="HarvestLog"+str(index)
	log_body.set_meta("wood_pickup",true)
	log_body.set_meta("tree_key",tree_key)
	log_body.set_meta("log_index",index)
	add_child(log_body)
	log_body.global_position=(a+b)*0.5+Vector3.UP*(r+0.04)
	log_body.global_basis=Basis(Quaternion(Vector3.UP,(b-a).normalized()))
	var mesh:=MeshInstance3D.new()
	var cylinder:=CylinderMesh.new()
	cylinder.height=length
	cylinder.top_radius=r*0.88
	cylinder.bottom_radius=r
	cylinder.radial_segments=12
	cylinder.cap_top=false
	cylinder.cap_bottom=false
	mesh.mesh=cylinder
	mesh.material_override=bark
	log_body.add_child(mesh)
	cap(log_body,Vector3.UP*length*0.5,r*0.88)
	cap(log_body,Vector3.DOWN*length*0.5,r)
	var shape:=CollisionShape3D.new()
	var col:=CylinderShape3D.new()
	col.height=length
	col.radius=r
	shape.shape=col
	log_body.add_child(shape)
	logs[index]=log_body

func cap(parent: Node3D, at: Vector3, r: float) -> void:
	# Match the log's 12-sided bark exactly, with no thick disc outside its ends.
	var ring: Array[Vector3]=[]
	for i in 12:
		var angle:=i*TAU/12
		ring.append(at+Vector3(sin(angle)*r,0,cos(angle)*r))
	section_cap(parent,[ring],at.y>0)

func section_cap(parent: Node3D, contours: Array, up: bool) -> void:
	var geometry:=Cutter.section_mesh(contours,up)
	if geometry==null: return
	var mesh:=MeshInstance3D.new()
	mesh.name="MatchedCutSurface"
	mesh.mesh=geometry
	mesh.material_override=cut_material
	parent.add_child(mesh)

func collect(index: int) -> bool:
	if not finished or not logs.has(index): return false
	var record: Dictionary=toolkit.felled[tree_key]
	if not record.remaining.has(index): return false
	if not preload("res://scripts/building/build_costs.gd").grant(self,"wood"):
		toolkit.editor.status.text="背包空间不足，木段仍可稍后收集"
		return false
	record.remaining.erase(index)
	toolkit.wood+=1
	logs[index].queue_free()
	logs.erase(index)
	var result: Error=toolkit.save_state()
	toolkit.editor.status.text="收集木材 ×1" if result==OK else "木材已收集，但保存失败："+error_string(result)
	return true

func burst(at: Vector3, dust: bool) -> void:
	var particles:=CPUParticles3D.new()
	add_child(particles)
	particles.global_position=at
	particles.one_shot=true
	particles.explosiveness=0.95
	particles.amount=30 if dust else 14
	particles.lifetime=0.85
	particles.direction=Vector3.UP
	particles.spread=80
	particles.gravity=Vector3(0,-5,0)
	particles.initial_velocity_min=0.8
	particles.initial_velocity_max=2.6
	var chip:=BoxMesh.new()
	chip.size=Vector3(0.045,0.018,0.08) if not dust else Vector3.ONE*0.06
	var mat:=StandardMaterial3D.new()
	mat.albedo_color=Color(0.37,0.22,0.09) if not dust else Color(0.26,0.22,0.16)
	chip.material=mat
	particles.mesh=chip
	particles.finished.connect(particles.queue_free)
	particles.emitting=true

func sound(path: String, at: Vector3, pitch: float) -> void:
	var audio:=AudioStreamPlayer3D.new()
	add_child(audio)
	audio.global_position=at
	audio.stream=load(path)
	audio.pitch_scale=pitch
	audio.max_distance=35
	audio.volume_db=-6
	audio.finished.connect(audio.queue_free)
	audio.play()
