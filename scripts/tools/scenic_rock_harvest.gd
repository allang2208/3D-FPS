extends RefCounted
const BAKED={"rock_09":preload("res://assets/models/basic_tools/rock_fragments/rock_09.res"),"boulder_01":preload("res://assets/models/basic_tools/rock_fragments/boulder_01.res")}
const ORE_NAMES={"iron_ore":"铁矿","copper_ore":"铜矿","silver_ore":"银矿","gold_ore":"金矿"}
var toolkit: Node3D
var hits: Dictionary={}
var last_effect: Node3D

static func rock_id(body: Node3D) -> String:
	if body.has_meta("harvest_identity"): return body.get_meta("harvest_identity")
	var p:=body.global_position
	return "%s:%.3f:%.3f:%.3f" % [body.get_meta("rock_source"),p.x,p.y,p.z]

func strike(body: Node3D, at: Vector3, normal: Vector3) -> bool:
	if not toolkit.allows_ground(): return false
	var editor: Node3D=toolkit.editor
	var item: String=body.get_meta("harvest_item","stone")
	var title: String=ORE_NAMES[item]+"脉" if ORE_NAMES.has(item) else "石块"
	var id:=rock_id(body)
	if editor.world.quarried_rocks.has(id): return false
	if body.get_meta("rock_extent",1.0)>3.0:
		editor.status.text="这是大型岩壁，请采集周围的独立石块"
		return false
	if not hits.has(id): hits.clear()
	var count: int=hits.get(id,0)+1
	hits[id]=count
	var fx:=preload("res://scripts/tools/ore_break_fx.gd").new()
	editor.add_child(fx)
	if count<3:
		fx.strike(at,normal,count,false,false)
		editor.status.text="%s采集 %d / 3" % [title,count]
		return true
	var material: Material
	for node in body.get_parent().get_children():
		if node is MultiMeshInstance3D and node.get_meta("harvest_batch_key","")==body.get_meta("harvest_batch_key"):
			material=node.multimesh.mesh.surface_get_material(0)
	var source: String=body.get_meta("rock_source")
	var baked: Resource=BAKED.get(source.get_base_dir().get_file())
	if body.has_meta("rock_fragments"): baked=body.get_meta("rock_fragments")
	var shards: Array=[]
	if baked!=null:
		var xf: Transform3D=body.get_parent().global_transform*body.get_meta("rock_transform")
		for part in baked.get_meta("pieces"):
			var mesh: ArrayMesh=part.mesh.duplicate()
			var fragment_material: Material=material
			if ORE_NAMES.has(item) and material is ShaderMaterial:
				fragment_material=material.duplicate()
				fragment_material.set_shader_parameter("projection_offset",part.center)
			for s in mesh.get_surface_count(): mesh.surface_set_material(s,fragment_material)
			shards.append({"mesh":mesh,"center":xf*part.center-body.global_position,"basis":xf.basis,"hull":part.get("hull",PackedVector3Array())})
	if shards.is_empty():
		fx.queue_free()
		return false
	if not preload("res://scripts/building/build_costs.gd").grant(toolkit,item):
		fx.queue_free()
		editor.status.text="背包空间不足，请整理后继续采集"
		return false
	editor.world.quarried_rocks[id]=true
	if item=="stone": editor.world.stock[2]+=1
	apply_saved()
	fx.fracture(shards,body.global_position,at,normal)
	last_effect=fx
	hits.erase(id)
	editor._save()
	editor.status.text+="；%s已破碎，%s +1" % [title,ORE_NAMES.get(item,"石块")]
	return true

func apply_saved() -> void:
	var editor: Node3D=toolkit.editor
	var parent:=editor.get_parent()
	var batches: Dictionary={}
	for body in parent.get_children():
		if not body.has_meta("rock_source"): continue
		var removed: bool=editor.world.quarried_rocks.has(rock_id(body))
		body.set_meta("tool_quarried",removed)
		if not removed: continue
		for shape in body.find_children("","CollisionShape3D",true,false): shape.set_deferred("disabled",true)
		var key: String=body.get_meta("harvest_batch_key")
		if not batches.has(key): batches[key]={}
		batches[key][body.get_meta("harvest_index")]=true
	for node in parent.get_children():
		if not node is MultiMeshInstance3D or not node.has_meta("harvest_batch_key"): continue
		var removed: Dictionary=batches.get(node.get_meta("harvest_batch_key"),{})
		node.set_meta("quarried_indices",removed)
		for i in removed:
			node.multimesh.set_instance_transform(i,Transform3D(Basis.IDENTITY.scaled(Vector3.ONE*0.00001),Vector3(0,-10000,0)))
