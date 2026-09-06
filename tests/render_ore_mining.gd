extends SceneTree
class Host:
	extends Node3D
	var world: Node3D
	var status: Label
func _initialize() -> void:
	call_deferred("run")
func run() -> void:
	root.get_node("HUD").process_mode=Node.PROCESS_MODE_DISABLED
	for child in root.get_node("HUD").get_children():
		if child is CanvasLayer: child.hide()
	var host:=Host.new()
	root.add_child(host)
	current_scene=host
	host.add_child(load("res://scripts/world_lighting.gd").create_environment())
	host.add_child(load("res://scripts/world_lighting.gd").create_sun())
	host.world=load("res://scripts/voxel_lab/voxel_world.gd").new()
	host.add_child(host.world)
	host.status=Label.new()
	host.add_child(host.status)
	var cell:=Vector3i(-15,1,12)
	host.world.change_cell(cell,3)
	var cam:=Camera3D.new()
	host.add_child(cam)
	cam.position=Vector3(cell)+Vector3(3,2.5,4)
	cam.look_at(Vector3(cell)+Vector3.ONE*0.5)
	cam.current=true
	var kit: Node=load("res://scripts/tools/basic_toolkit.gd").new()
	host.add_child(kit)
	kit.editor=host
	kit.set_process(false)
	kit.equip("pickaxe")
	kit.pivot=Node3D.new()
	cam.add_child(kit.pivot)
	kit.pivot.position=Vector3(0.34,-0.34,-0.64)
	var model: Node3D=load("res://assets/models/basic_tools/pickaxe_v1.glb").instantiate()
	kit.pivot.add_child(model)
	kit.orient_model(model,"pickaxe")
	kit.mining_contact={"position":Vector3(cell)+Vector3(0.5,0.65,1.0),"normal":Vector3.BACK}
	var out: String="E:/3d/3-dfps/tools/basic-tools/ore-frames/"
	DirAccess.make_dir_recursive_absolute(out)
	for i in 10: await process_frame
	root.size=Vector2i(960,640)
	for frame in 144:
		if frame in [12,30,48]:
			if kit.mine_cell(cell): host.status.text=kit.mining_message
		kit.pivot.rotation=Vector3.ZERO
		for contact in [12,30,48]:
			var phase: float=(frame-(contact-6))/24.0
			if phase>=0 and phase<0.68: kit.update_pose(phase)
		await physics_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(out+"%03d.png" % frame)
		await process_frame
	print("ORE_RENDER PASS 144 actual frames")
	quit()
