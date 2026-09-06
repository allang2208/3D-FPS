extends SceneTree
class Stock:
	extends Node3D
	var quarried_rocks: Dictionary={}
	var stock: Dictionary={2:0}
class Host:
	extends Node3D
	var world: Node3D
	var status: Label
	func _save() -> void: pass
func _initialize() -> void:
	call_deferred("run")
func run() -> void:
	var iron:=OS.get_environment("IRON_PREVIEW")=="1"
	var copper:=OS.get_environment("COPPER_PREVIEW")=="1"
	if copper: iron=true
	var precious:=OS.get_environment("PRECIOUS_PREVIEW")
	if not precious.is_empty(): iron=true
	root.get_node("HUD")._ensure_built()
	root.get_node("HUD").process_mode=Node.PROCESS_MODE_DISABLED
	for child in root.get_node("HUD").get_children():
		if child is CanvasLayer: child.hide()
	var scene:=Node3D.new()
	root.add_child(scene)
	current_scene=scene
	scene.add_child(load("res://scripts/world_lighting.gd").create_environment())
	scene.add_child(load("res://scripts/world_lighting.gd").create_sun())
	var ground:=StaticBody3D.new()
	scene.add_child(ground)
	var floor_mesh:=MeshInstance3D.new()
	var plane:=BoxMesh.new()
	plane.size=Vector3(24,0.2,24)
	floor_mesh.mesh=plane
	var ground_material:=StandardMaterial3D.new()
	ground_material.albedo_color=Color(0.22,0.25,0.20)
	ground_material.roughness=1.0
	floor_mesh.material_override=ground_material
	ground.add_child(floor_mesh)
	ground.position.y= -0.1
	var floor_shape:=CollisionShape3D.new()
	var box:=BoxShape3D.new()
	box.size=plane.size
	floor_shape.shape=box
	ground.add_child(floor_shape)
	var path: String=load("res://scenes/scenic_valley.gd").ROCK
	var model: Node3D=load(path).instantiate()
	scene.add_child(model)
	var geometry: Dictionary=load("res://scenes/scenic_collision.gd").rock_geometry(model)
	var bounds: AABB=geometry.bounds
	var factor:=1.5/maxf(bounds.size.x,bounds.size.z)
	var xf:=Transform3D(Basis.IDENTITY.scaled(Vector3.ONE*factor),Vector3(0,-bounds.position.y*factor,0))
	var rock: Node3D=load("res://scenes/scenic_collision.gd").add_rock(scene,xf,geometry)
	rock.set_meta("rock_source",path)
	rock.set_meta("harvest_item","iron_ore" if iron else "stone")
	if copper: rock.set_meta("harvest_item","copper_ore")
	if not precious.is_empty(): rock.set_meta("harvest_item",precious+"_ore")
	rock.set_meta("rock_transform",xf)
	rock.set_meta("rock_extent",1.5)
	rock.set_meta("harvest_batch_key","preview")
	rock.set_meta("harvest_index",0)
	for source in model.find_children("","MeshInstance3D",true,false):
		var mesh: Mesh=source.mesh.duplicate()
		for surface in mesh.get_surface_count():
			var mat: StandardMaterial3D=source.get_active_material(surface).duplicate()
			if mat.albedo_texture==null: mat.albedo_texture=load(path.get_base_dir()+"/textures/rock_09_diff_2k.jpg")
			mat.metallic_specular=0.15
			mat.roughness=0.9
			mesh.surface_set_material(surface,mat)
			if iron: mesh.surface_set_material(surface,load("res://scripts/tools/iron_vein_material.gd").create(mesh))
			if copper: mesh.surface_set_material(surface,load("res://scripts/tools/copper_vein_material.gd").create(mesh))
			if not precious.is_empty(): mesh.surface_set_material(surface,load("res://scripts/tools/precious_vein_material.gd").create(precious,mesh))
		var batch:=MultiMeshInstance3D.new()
		batch.multimesh=MultiMesh.new()
		batch.multimesh.transform_format=MultiMesh.TRANSFORM_3D
		batch.multimesh.mesh=mesh
		batch.multimesh.instance_count=1
		batch.multimesh.set_instance_transform(0,xf*model.global_transform.affine_inverse()*source.global_transform)
		batch.set_meta("harvest_batch_key","preview")
		scene.add_child(batch)
	model.free()
	var host:=Host.new()
	scene.add_child(host)
	host.world=Stock.new()
	host.add_child(host.world)
	host.status=Label.new()
	host.add_child(host.status)
	var cam:=Camera3D.new()
	scene.add_child(cam)
	cam.position=Vector3(2.5,2.2,3.6)
	if iron: cam.position=Vector3(1.7,1.5,2.5)
	cam.look_at(Vector3(0,0.4,0))
	cam.current=true
	var kit: Node=load("res://scripts/tools/basic_toolkit.gd").new()
	host.add_child(kit)
	kit.editor=host
	kit.rocks.toolkit=kit
	kit.set_process(false)
	kit.equip("pickaxe")
	kit.pivot=Node3D.new()
	cam.add_child(kit.pivot)
	kit.pivot.position=Vector3(0.34,-0.34,-0.64)
	var pick: Node3D=load("res://assets/models/basic_tools/pickaxe_v1.glb").instantiate()
	kit.pivot.add_child(pick)
	kit.orient_model(pick,"pickaxe")
	var out: String="E:/3d/3-dfps/tools/basic-tools/scenic-rock-frames/"
	if iron: out="E:/3d/3-dfps/tools/basic-tools/iron-vein-frames/"
	if copper: out="E:/3d/3-dfps/tools/basic-tools/copper-vein-frames/"
	if not precious.is_empty(): out="E:/3d/3-dfps/tools/basic-tools/%s-vein-frames/" % precious
	DirAccess.make_dir_recursive_absolute(out)
	root.size=Vector2i(960,640)
	for i in 10: await process_frame
	for frame in 144:
		if frame in [12,30,48]: kit.rocks.strike(rock,Vector3(0,0.5,0.45),Vector3.BACK)
		kit.pivot.rotation=Vector3.ZERO
		for contact in [12,30,48]:
			var phase: float=(frame-(contact-6))/24.0
			if phase>=0 and phase<0.68: kit.update_pose(phase)
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(out+"%03d.png" % frame)
		await process_frame
	print("SCENIC_ROCK_RENDER PASS: 144 frames, source rock_09 model/material and runtime fracture")
	quit()
