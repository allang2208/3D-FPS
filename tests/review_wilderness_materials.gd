extends SceneTree
var camera: Camera3D
var world: Node
var scene: Node3D
var variant := ""
var output := ""
func _initialize() -> void:
	output=OS.get_environment("WILDERNESS_REVIEW_OUTPUT") if OS.has_environment("WILDERNESS_REVIEW_OUTPUT") else ProjectSettings.globalize_path("user://material-review/")
	if not output.ends_with("/"): output+="/"
	variant=OS.get_environment("WILDERNESS_REVIEW_LABEL") if OS.has_environment("WILDERNESS_REVIEW_LABEL") else preload("res://scripts/wilderness_materials.gd").variant()
	OS.set_environment("WILDERNESS_SAVE_PATH","user://material-review-"+str(OS.get_process_id())+".json")
	OS.set_environment("INVENTORY_SAVE_PATH","user://material-inventory-"+str(OS.get_process_id())+".save")
	call_deferred("run")
func capture(label: String,at: Vector3) -> void:
	for view in ["near","far"]:
		camera.global_position=at+(Vector3(0,2.2,2.8) if view=="near" else Vector3(-12,12,-15))
		camera.look_at(at)
		for i in 45: await process_frame
		await RenderingServer.frame_post_draw
		assert(root.get_texture().get_image().save_png(output+variant+"_"+label+"_"+view+".png")==OK)
func run() -> void:
	DirAccess.make_dir_recursive_absolute(output)
	scene=load("res://scenes/scenic_valley.tscn").instantiate()
	root.add_child(scene)
	current_scene=scene
	if OS.get_environment("WILDERNESS_HIDE_WATER")=="1":
		scene.get_node("River").hide()
		scene.get_node("Lake").hide()
	var editor: Node=scene.get_node("WildernessEditor")
	world=editor.world
	editor.player.set_physics_process(false)
	editor.player.set_process_unhandled_input(false)
	editor.set_enabled(true)
	editor.set_physics_process(false)
	editor.tool_layer.hide()
	editor.hint_label.hide()
	root.get_node("HUD").set_process(false)
	for layer in root.get_node("HUD").find_children("","CanvasLayer",true,false): layer.hide()
	camera=editor.camera
	if camera.has_node("CameraFx"): camera.get_node("CameraFx").process_mode=Node.PROCESS_MODE_DISABLED
	camera.set_as_top_level(true)
	camera.fov=60
	Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
	var grass:=Vector3(-245,world.natural_height(-245,65),65)
	await capture("grass",grass)
	var gz: float=scene._river_center_z(-200)+scene.stream_half_width(-200)+3.0
	await capture("gravel",Vector3(-200,world.natural_height(-200,gz),gz))
	world.prepare_at(Vector3i(-245,floori(grass.y),65))
	while not world.jobs.is_empty(): await process_frame
	for z in range(63,68):
		for x in range(-247,-242):
			var h: int=floori(world.natural_height(x+0.5,z+0.5))
			for y in range(h-2,h+1):
				var p:=Vector3i(x,y,z)
				if world.get_cell(p)!=0: world.mine(p)
	editor._refresh_foliage()
	await capture("soil",grass-Vector3.UP*1.5)
	print("MATERIAL_REVIEW_COMPLETE ",variant)
	scene.free()
	quit()
