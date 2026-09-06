extends SceneTree
const OUT := "res://tools/ai-gen/ore-spider-release-v07-20260906"
var bolts: Array[Node3D]=[]
func _initialize() -> void: call_deferred("run_preview")
func snap(path: String) -> void:
	await process_frame
	await RenderingServer.frame_post_draw
	var frame := int(path.get_file().get_basename())
	if frame in [0, 18, 24, 26, 33, 47, 54, 66, 89]:
		root.get_texture().get_image().save_png(OUT.path_join(path))
func run_preview() -> void:
	var main: Node3D=load("res://scenes/ore_spider_demo.tscn").instantiate()
	root.add_child(main);current_scene=main
	await process_frame
	var old=main.get_node("OreSpider")
	main.remove_child(old);old.queue_free()
	var z=load("res://scenes/enemies/ore_spider.tscn").instantiate()
	main.add_child(z);z.position=Vector3(-8,0,0)
	var player=main.get_node("Player")
	player.set_physics_process(false);player.position=Vector3(-8,0,6);player.hp=10000
	z.setup(player,func(): pass);z.set_physics_process(false)
	var camera:=Camera3D.new();main.add_child(camera)
	camera.position=z.position+Vector3(3.8,2.7,5)
	camera.look_at(z.position+Vector3(0,1.1,0));camera.make_current()
	player.visible=false
	for clip in ["idle","walk","throw","slam","death"]:DirAccess.make_dir_recursive_absolute(OUT.path_join(clip))
	z._pose("Idle",0,-1)
	await snap("idle/000.png")
	for i in 34:
		z._pose("Walk",i/24.0*2,-1)
		await snap("walk/%03d.png"%i)
	z.crystal_released.connect(func(p):p.set_physics_process(false);bolts.append(p))
	z._start_attack("Throw")
	for i in 55:
		if z.state=="Throw":z._tick_attack(1.0/24)
		for p in bolts:
			if is_instance_valid(p) and not p.is_queued_for_deletion():p._physics_process(1.0/24)
		await snap("throw/%03d.png"%i)
	assert(bolts.size()==1)
	player.position=z.position+Vector3(0,0,3)
	z._start_attack("Slam")
	for i in 48:
		z._tick_attack(1.0/24)
		await snap("slam/%03d.png"%i)
	z._die()
	for i in 90:
		z._tick_death(1.0/24)
		await snap("death/%03d.png"%i)
	print("ORE_JOINT_RENDER PASS: held stone, one projectile, slam and final death slam/collapse")
	main.queue_free()
	for i in 3:await process_frame
	quit()
