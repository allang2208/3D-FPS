extends SceneTree
class Host:
	extends Node3D
	var camera: Camera3D
	var status: Label
var scene: Node3D
var host: Host
var kit: Node3D
var tree: StaticBody3D
var effect: Node3D
var frame:=0
var recording:=false
const OUT:="E:/3d/3-dfps/tools/basic-tools/felling-frames/"
func _initialize() -> void:
	call_deferred("run")
func run() -> void:
	root.get_node("HUD").process_mode=Node.PROCESS_MODE_DISABLED
	for child in root.get_node("HUD").get_children():
		if child is CanvasLayer: child.hide()
	DirAccess.make_dir_recursive_absolute(OUT)
	scene=Node3D.new()
	root.add_child(scene)
	current_scene=scene
	var env:=WorldEnvironment.new()
	env.environment=Environment.new()
	env.environment.background_mode=Environment.BG_COLOR
	env.environment.background_color=Color(0.24,0.32,0.38)
	env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color=Color(0.77,0.84,0.92)
	env.environment.ambient_light_energy=0.6
	scene.add_child(env)
	var sun:=DirectionalLight3D.new()
	sun.rotation_degrees=Vector3(-48,-32,0)
	sun.light_energy=1.7
	sun.shadow_enabled=true
	scene.add_child(sun)
	var ground:=StaticBody3D.new()
	scene.add_child(ground)
	var mesh:=MeshInstance3D.new()
	var plane:=BoxMesh.new()
	plane.size=Vector3(60,0.2,60)
	var mat:=StandardMaterial3D.new()
	mat.albedo_color=Color(0.14,0.18,0.12)
	plane.material=mat
	mesh.mesh=plane
	mesh.position.y=-0.1
	ground.add_child(mesh)
	var col:=CollisionShape3D.new()
	var box:=BoxShape3D.new()
	box.size=plane.size
	col.shape=box
	col.position.y=-0.1
	ground.add_child(col)
	tree=StaticBody3D.new()
	tree.set_meta("landscape_asset","res://scenes/imported_pine.tscn")
	tree.set_meta("impact_surface","wood")
	scene.add_child(tree)
	var model: Node3D=load("res://scenes/imported_pine.tscn").instantiate()
	model.variant=1
	tree.add_child(model)
	model.position.y=-model.burial_depth
	model.setup_lod()
	var trunk:=CollisionShape3D.new()
	var trunk_shape:=CylinderShape3D.new()
	trunk_shape.radius=0.3
	trunk_shape.height=7
	trunk.shape=trunk_shape
	trunk.position.y=3.5
	tree.add_child(trunk)
	host=Host.new()
	scene.add_child(host)
	host.camera=Camera3D.new()
	host.add_child(host.camera)
	host.camera.position=Vector3(16,9,19)
	host.camera.look_at(Vector3(3,4,0))
	host.camera.fov=40
	host.status=Label.new()
	host.add_child(host.status)
	kit=load("res://scripts/tools/basic_toolkit.gd").new()
	host.add_child(kit)
	kit.editor=host
	kit.state_path="user://tree-felling-render-"+str(OS.get_process_id())+".json"
	kit.equip("axe")
	kit.set_process(false)
	for i in 10: await process_frame
	await record_frames()

func record_frames() -> void:
	while frame<144:
		if frame in [10,22]: kit.chop(tree,Vector3(0.28,0.65,0),Vector3.RIGHT)
		if frame==34:
			# The player's position fixes the fall direction; the observer keeps framing.
			host.camera.position=Vector3(-2,1.7,0)
			kit.chop(tree)
			effect=kit.tree_effects[kit.tree_id(tree)]
			effect.set_process(false)
			host.camera.position=Vector3(16,9,19)
			host.camera.look_at(Vector3(3,4,0))
		if effect!=null:
			effect.advance(1.0/24.0)
			if frame>116: effect.hinge.hide()
		if frame==143:
			host.camera.position=Vector3(1.5,1.65,2.3)
			host.camera.look_at(Vector3(0,0.45,0))
			await process_frame
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png("E:/3d/3-dfps/tools/basic-tools/stump-cut-closeup.png")
			host.camera.position=Vector3(16,9,19)
			host.camera.look_at(Vector3(3,4,0))
			await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(OUT+"%03d.png" % frame)
		frame+=1
		await process_frame
	print("TREE_FELLING_RENDER PASS 144 frames / 24 fps")
	quit()
