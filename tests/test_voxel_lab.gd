extends SceneTree
const World := preload("res://scripts/voxel_lab/voxel_world.gd")
var failures: Array[String] = []

func _initialize() -> void:
	call_deferred("run")

func check(ok: bool, label: String) -> void:
	print("PASS " if ok else "FAIL ", label)
	if not ok:
		failures.append(label)

func ray(world: Node3D, from: Vector3, to: Vector3) -> Dictionary:
	return world.get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(from, to, 1))

func run() -> void:
	root.get_node("HUD").set_process(false)
	var world := World.new()
	root.add_child(world)
	await physics_frame
	await physics_frame
	var p := Vector3i(-8, 0, 10)
	var start := Vector3(-7.5, 5, 10.5)
	var end := Vector3(-7.5, -5, 10.5)
	var before := ray(world, start, end)
	check(not before.is_empty() and is_equal_approx(before.position.y, 1.0), "surface collision before excavation")
	var amount: int = world.stock[1]
	check(world.mine(p), "dig soil")
	check(world.stock[1] == amount + 1, "mining awards one material")
	check(world.last_rebuilt_chunks == 3, "chunk edge updates only three affected chunks")
	await physics_frame
	await physics_frame
	var after := ray(world, start, end)
	check(not after.is_empty() and is_equal_approx(after.position.y, 0.0), "collision floor lowers after dig")
	var outside := AABB(Vector3(100, 100, 100), Vector3.ONE)
	check(world.place(p, 1, outside), "refill excavated cell")
	check(world.stock[1] == amount, "refill consumes awarded material")
	check(not world.edits.has(p), "refill original soil removes redundant delta")
	check(not world.place(p, 1, outside), "occupied cell rejects placement")
	check(not world.mine(Vector3i(0, -8, 0)), "bottom boundary remains solid")
	check(not world.mine(Vector3i(24, 0, 0)), "outside bounds rejects mining")
	var build := Vector3i(-8, 1, 10)
	check(not world.place(build, 4, AABB(Vector3(build), Vector3.ONE)), "cannot place inside player")
	check(not world.place(Vector3i(-8, 12, 10), 4, outside), "unsupported floating block rejected")
	check(world.place(build, 4, outside), "place building brick")
	await physics_frame
	await physics_frame
	var built := ray(world, start, end)
	check(not built.is_empty() and is_equal_approx(built.position.y, 2.0), "building collision is walkable")
	var cave := Vector3i(7, 3, 0)
	check(world.mine(cave) and world.get_cell(cave + Vector3i.UP) != 0, "underground excavation preserves roof")
	await physics_frame
	await physics_frame
	var ceiling := ray(world, Vector3(7.5, 3.5, 0.5), Vector3(7.5, 5.5, 0.5))
	check(not ceiling.is_empty() and is_equal_approx(ceiling.position.y, 4.0), "underground roof has collision")
	var timings: Array[float] = []
	for x in range(-6, 6):
		world.mine(Vector3i(x, 0, 7))
		timings.append(world.last_rebuild_ms)
	var path := "user://voxel-lab-acceptance-" + str(OS.get_process_id()) + ".json"
	check(world.save_world(path) == OK, "save terrain and stock")
	var expected := world.cells.duplicate()
	var expected_stock := world.stock.duplicate()
	world.reset_data()
	check(world.load_world(path) == OK and world.cells == expected and world.stock == expected_stock, "reload exact terrain and material counts")
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string('{"version":1,"generator":"hill-v1","edits":[[900,0,0,1]],"stock":[1,2,3,4]}')
	file.close()
	check(world.load_world(path) == ERR_FILE_CORRUPT and world.cells == expected, "invalid save rejected without partial mutation")
	DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
	timings.sort()
	print("VOXEL_BENCH edit_count=", timings.size(), " median_ms=", timings[timings.size() / 2], " max_ms=", timings.back(), " triangles=", world.triangle_count)
	world.queue_free()
	await process_frame
	print("VOXEL_ACCEPTANCE failures=", failures.size())
	quit(0 if failures.is_empty() else 1)
