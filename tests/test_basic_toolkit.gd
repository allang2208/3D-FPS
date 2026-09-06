extends SceneTree
func _initialize() -> void:
	OS.set_environment("WILDERNESS_SAVE_PATH","user://basic-tools-test-"+str(OS.get_process_id())+".json")
	OS.set_environment("INVENTORY_SAVE_PATH","user://basic-tools-inventory-test-"+str(OS.get_process_id())+".save")
	call_deferred("run")

func run() -> void:
	var scene: Node3D=load("res://scenes/scenic_valley.tscn").instantiate()
	root.add_child(scene)
	current_scene=scene
	var editor: Node=scene.get_node("WildernessEditor")
	var kit: Node=editor.toolkit
	editor.set_physics_process(false)
	editor.player.set_physics_process(false)
	editor.player.set_process_unhandled_input(false)
	kit.set_process(false)
	var cam: Camera3D=editor.camera
	cam.get_node("CameraFx").process_mode=Node.PROCESS_MODE_DISABLED
	cam.set_as_top_level(true)
	var at:=Vector3(-245,0,65)
	at.y=editor.world.natural_height(at.x,at.z)
	cam.global_position=at+Vector3(0,2.2,0.1)
	cam.look_at(at)
	await physics_frame
	await physics_frame
	assert(not kit.active and not editor.act(true))
	editor.set_enabled(true)
	assert(not kit.begin_use())
	assert(kit.equip("axe"))
	assert(not kit.resolve_contact())
	assert(editor.world.edits.is_empty())
	assert(kit.equip("pickaxe"))
	kit.owned.pickaxe=false
	assert(not kit.resolve_contact())
	kit.owned.pickaxe=true
	assert(not kit.resolve_contact()) # prepares collision chunks, no instant excavation
	while not editor.world.jobs.is_empty(): await process_frame
	await physics_frame
	await physics_frame
	assert(kit.resolve_contact())
	assert(not editor.world.edits.is_empty())
	var edit_count: int=editor.world.edits.size()
	cam.global_position=at+Vector3(0,5,0.1)
	cam.look_at(at)
	assert(not kit.resolve_contact() and editor.world.edits.size()==edit_count)
	var tree: StaticBody3D
	for body in scene.get_children():
		if kit.is_tree(body):
			tree=body
			break
	assert(tree!=null)
	assert(not kit.chop(tree))
	kit.equip("axe")
	assert(kit.chop(tree) and kit.chop(tree))
	assert(kit.wood==0 and tree.visible)
	assert(kit.chop(tree))
	assert(kit.wood==0 and not tree.visible)
	assert(not kit.chop(tree) and kit.wood==0)
	var effect: Node=kit.tree_effects[kit.tree_id(tree)]
	effect.set_process(false)
	assert(not effect.collect(0))
	# Reload a save made at fracture: it must retain four unclaimed logs, no wood.
	assert(kit.load_state()==OK and kit.wood==0)
	assert(kit.felled[kit.tree_id(tree)].remaining.size()==4)
	effect.advance(3.1)
	assert(effect.finished and effect.logs.size()==4)
	assert(effect.collect(0))
	# Rebuild world pickups from the partial save, without replaying the fall.
	effect.free()
	kit.tree_effects.clear()
	assert(kit.load_state()==OK and kit.wood==1)
	kit.apply_felled()
	effect=kit.tree_effects[kit.tree_id(tree)]
	assert(effect.finished and effect.logs.size()==3 and not effect.logs.has(0))
	for i in range(1,4): assert(effect.collect(i))
	assert(kit.wood==4 and not effect.collect(0))
	editor._refresh_foliage()
	assert(not tree.visible)
	assert(kit.save_state()==OK)
	kit.wood=0
	kit.felled={}
	assert(kit.load_state()==OK and kit.wood==4 and kit.felled.size()==1)
	var restored: Node=load("res://scripts/tools/basic_toolkit.gd").new()
	restored.state_path=kit.state_path
	assert(restored.load_state()==OK and restored.wood==4 and restored.felled.size()==1)
	# Legacy boolean records already paid their wood and must not produce pickups.
	var legacy_path: String=kit.state_path+".legacy"
	var legacy:=FileAccess.open(legacy_path,FileAccess.WRITE)
	legacy.store_string(JSON.stringify({"version":1,"wood":4,"felled":{"old_tree":true},"owned":{"axe":true,"pickaxe":true}}))
	legacy.close()
	restored.state_path=legacy_path
	assert(restored.load_state()==OK and restored.wood==4 and restored.felled.old_tree.remaining.is_empty())
	restored.free()
	kit.begin_use()
	editor.set_enabled(false)
	assert(kit.elapsed<0 and not kit.pivot.visible and editor.gun.visible)
	print("BASIC_TOOLKIT PASS: empty/wrong/missing tool gates, real terrain ray and excavation, three axe hits, no duplicate wood, foliage refresh, save restore, weapon cancellation")
	scene.free()
	quit()
