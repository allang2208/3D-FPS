extends Node

var failures: Array[String] = []

func check(condition: bool, label: String) -> void:
	if not condition:
		failures.append(label)
	print("[valley-test] ", "PASS " if condition else "FAIL ", label)


func _ready() -> void:
	var scene: Node3D = load("res://scenes/demo_terrain.tscn").instantiate()
	add_child(scene)
	scene.get_node("Player").set_process_unhandled_input(false)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	for i in 120:
		await get_tree().physics_frame
	var t: Terrain3D = scene.terrain
	var player: CharacterBody3D = scene.get_node("Player")
	check(scene.get_script().resource_path == "res://scenes/scenic_valley.gd", "portal destination uses new valley")
	check(player.is_on_floor(), "arrival settles on terrain")
	var ground := t.data.get_height(player.position)
	# Player controller raises its capsule by half the standing height: root is feet.
	check(absf(player.position.y - ground) < 0.35, "player feet follow terrain")
	check(t.collision.get_rid().is_valid(), "terrain collision RID")
	var portal: Area3D = scene.get_node("ReturnPortal")
	check(portal.target_scene == "res://scenes/main.tscn", "return destination preserved")
	check(portal.position.distance_to(player.position) > 4.0, "arrival outside return trigger")
	check(scene.get_node_or_null("MouseKingNpc") != null, "NPC preserved")
	var tree_count := 0
	var bad_trees := 0
	var missing_materials := 0
	for child in scene.get_children():
		if child is StaticBody3D and child.get_meta("impact_surface", "") == "wood":
			tree_count += 1
			if absf(child.position.y - t.data.get_height(child.position)) > 0.05:
				bad_trees += 1
			if child.find_children("", "CollisionShape3D", true, false).is_empty():
				bad_trees += 1
			for mesh in child.find_children("", "MeshInstance3D", true, false):
				for surface in mesh.mesh.get_surface_count():
					if mesh.get_active_material(surface).albedo_texture == null:
						missing_materials += 1
	check(tree_count > 100 and bad_trees == 0, "forest grounded with trunk collisions")
	check(missing_materials == 0, "fir textures bound")
	var submerged := 0
	var bank_clear := 0
	for x in range(-260, 101, 10):
		var center: float = scene._river_center_z(x)
		var w: float = scene.stream_half_width(x)
		var level: float = scene.water_height(x)
		if t.data.get_height(Vector3(x, 0, center)) < level:
			submerged += 1
		if t.data.get_height(Vector3(x, 0, center + w + 3.0)) > level:
			bank_clear += 1
	check(submerged == 37 and bank_clear == 37, "stream bed submerged and dry banks above water")
	check(scene.get_node("ParticleGrass").particle_count <= 190000, "bounded near grass budget")
	_test_landscape_physics(scene, t)
	# Move using physics frames: verify the actual Area3D signal without initiating
	# an asynchronous whole-game load inside this structural runner.
	portal.target_scene = ""
	var entered := [false]
	portal.body_entered.connect(func(body: Node3D):
		if body == player:
			entered[0] = true)
	player.set_physics_process(false)
	player.position = portal.position
	for i in 8:
		await get_tree().physics_frame
	check(entered[0], "return portal detects player collision layer")
	print("[valley-test] trees=", tree_count, " failures=", failures)
	get_tree().quit(0 if failures.is_empty() else 1)


func _test_landscape_physics(scene: Node3D, terrain: Terrain3D) -> void:
	var rocks := get_tree().get_nodes_in_group("scenic_rocks")
	var max_gap := -INF
	var bad_shapes := 0
	var ray_hits := 0
	var swept := false
	var space := scene.get_world_3d().direct_space_state
	for rock in rocks:
		for local_point in rock.get_meta("underside_points"):
			var point: Vector3 = rock.to_global(local_point)
			max_gap = maxf(max_gap, point.y - terrain.data.get_height(point))
		var collisions := rock.find_children("", "CollisionShape3D", true, false)
		if collisions.size() != 1 or not collisions[0].shape is ConvexPolygonShape3D or not rock.scale.is_equal_approx(Vector3.ONE):
			bad_shapes += 1
		var box: AABB = rock.get_meta("local_bounds")
		var center: Vector3 = rock.position + box.get_center()
		var top := center + Vector3(0, box.size.y * 0.5 + 2, 0)
		var ray := PhysicsRayQueryParameters3D.create(top, center, 1)
		var hit := space.intersect_ray(ray)
		if hit.get("collider") == rock:
			ray_hits += 1
			if not swept:
				var sphere := SphereShape3D.new()
				sphere.radius = 0.25
				var query := PhysicsShapeQueryParameters3D.new()
				query.shape = sphere
				query.transform = Transform3D(Basis(), top)
				query.motion = center - top
				query.collision_mask = 1
				var fraction := space.cast_motion(query)
				swept = fraction[0] < 1.0
	check(rocks.size() == 170 and bad_shapes == 0, "all rocks have closed unscaled solid collision")
	check(max_gap <= 0.01, "sampled rock undersides embedded below terrain")
	check(ray_hits > 50, "game collision layer raycasts hit visible rock surfaces")
	check(swept, "moving physics shape blocked by rock")
	var trunk_hits := 0
	for tree in get_tree().get_nodes_in_group("scenic_trees"):
		var collision: CollisionShape3D = tree.find_children("", "CollisionShape3D", true, false)[0]
		var points: PackedVector3Array = collision.shape.points
		var center := Vector3.ZERO
		for point in points:
			center += point
		center = tree.to_global(center / points.size())
		var query := PhysicsRayQueryParameters3D.create(center + Vector3(3, 0, 0), center, 1)
		if space.intersect_ray(query).get("collider") == tree:
			trunk_hits += 1
	check(trunk_hits > 100, "raycasts hit calibrated trunk geometry")
	print("[valley-physics] rocks=", rocks.size(), " max_underside_gap=", max_gap, " rock_hits=", ray_hits, " trunk_hits=", trunk_hits)
