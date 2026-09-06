extends SceneTree
var failures := 0
func _initialize() -> void:
	OS.set_environment("INVENTORY_SAVE_PATH", "user://portal-test-inventory-"+str(OS.get_process_id())+".save")
	OS.set_environment("VOXEL_LAB_SAVE_PATH", "user://portal-test-world-"+str(OS.get_process_id())+".json")
	call_deferred("run")
func check(ok: bool, label: String) -> void:
	print("PASS " if ok else "FAIL ",label)
	if not ok:
		failures += 1
func wait_scene(path: String) -> bool:
	for i in 600:
		await physics_frame
		if current_scene != null and current_scene.scene_file_path == path:
			return true
	return false
func run() -> void:
	change_scene_to_file("res://scenes/main.tscn")
	await wait_scene("res://scenes/main.tscn")
	await physics_frame
	var portal: Area3D = current_scene.get_node("VoxelLabPortal")
	var player: CharacterBody3D = current_scene.get_node("Player")
	check(portal.position.distance_to(player.position)>2.0,"spawn does not immediately enter portal")
	player.position = portal.position-Vector3(0,1,0)
	player.velocity = Vector3.ZERO
	var entered := await wait_scene("res://scenes/voxel_lab.tscn")
	check(entered,"physical portal enters voxel lab")
	if not entered:
		quit(1)
		return
	check(not root.get_node("HUD").is_processing(),"formal HUD paused inside test scene")
	current_scene.world.mine(Vector3i(7,3,0))
	current_scene.save_delay = 0.5
	var back: Area3D = current_scene.get_node("ReturnPortal")
	current_scene.player.position = back.position-Vector3(0,1,0)
	current_scene.player.velocity = Vector3.ZERO
	check(await wait_scene("res://scenes/main.tscn"),"LabPlayer physically triggers return portal")
	check(FileAccess.file_exists(OS.get_environment("VOXEL_LAB_SAVE_PATH")),"return saves independent edits")
	check(root.get_node("HUD").is_processing(),"formal HUD restored after return")
	for i in 120:
		await physics_frame
	check(current_scene.scene_file_path == "res://scenes/main.tscn","return spawn does not cause teleport loop")
	print("PORTAL_ACCEPTANCE failures=",failures)
	quit(0 if failures==0 else 1)
