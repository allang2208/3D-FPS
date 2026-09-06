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
		if child.is_in_group("scenic_trees"):
			tree_count += 1
			if absf(child.position.y - t.data.get_height(child.position)) > 0.05:
				bad_trees += 1
			if child.find_children("", "CollisionShape3D", true, false).is_empty():
				bad_trees += 1
			for mesh in child.find_children("", "MeshInstance3D", true, false):
				for surface in mesh.mesh.get_surface_count():
					var material: Material = mesh.get_active_material(surface)
					var texture: Texture2D = material.get_shader_parameter("albedo_texture") if material is ShaderMaterial else material.albedo_texture
					if texture == null:
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
	_test_grounding(scene, t)
	_test_scenery_layers(scene)
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
	check(rocks.size() > 50 and rocks.size() <= 230 and bad_shapes == 0, "accepted rocks have closed unscaled solid collision")
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


func _test_grounding(scene: Node3D, terrain: Terrain3D) -> void:
	var bad_roots := 0
	var buried_plants := 0
	var counts := {}
	var maximum_gap := -INF
	for record in scene.grounding_records:
		var kind: String = record["kind"]
		counts[kind] = counts.get(kind, 0) + 1
		var xf: Transform3D = record["transform"]
		for point in record["geometry"]["support"]:
			var world: Vector3 = xf * point
			var gap := world.y - terrain.data.get_height(world)
			maximum_gap = maxf(maximum_gap, gap)
			if not is_finite(gap) or gap > 0.005:
				bad_roots += 1
		if kind != "rock":
			var buried := 0
			var points: PackedVector3Array = record["geometry"]["clearance"]
			for point in points:
				var world: Vector3 = xf * point
				if world.y < terrain.data.get_height(world) - 0.025:
					buried += 1
			if buried > points.size() * 0.08:
				buried_plants += 1
	check(bad_roots == 0 and counts.get("plant", 0) > 500, "individual plant and tree root samples below terrain")
	check(buried_plants == 0, "upper plant samples respect burial budget")
	var overlapping := 0
	for record in scene.grounding_records:
		if record["kind"] == "plant" and scene._blocked(record["bounds"]):
			overlapping += 1
	check(overlapping == 0, "ground cover clears final rocks trunks and stumps")
	var masked := 0
	for rock in get_tree().get_nodes_in_group("scenic_rocks"):
		var local_box: AABB = rock.get_meta("local_bounds")
		var center: Vector3 = rock.position + local_box.get_center()
		var pixel := Vector2i(floori((center.x + 512) * 2), floori((center.z + 512) * 2))
		if scene.grass_exclusion.get_pixelv(pixel).r > 0.5:
			masked += 1
	check(masked == counts.get("rock", 0), "GPU grass excludes every rock footprint")
	var grass: Node3D = scene.get_node("ParticleGrass")
	var offset: Vector3 = grass.process_material.get_shader_parameter("position_offset")
	check(is_zero_approx(offset.y + grass.mesh.get_aabb().position.y), "grass offset matches actual mesh root")
	# Inspect rendered tree vertices independently of the helper's placement records.
	var floating_trunks := 0
	for tree in get_tree().get_nodes_in_group("scenic_trees"):
		var lowest_world_y := INF
		var lowest := Vector3.ZERO
		for mesh in tree.find_children("", "MeshInstance3D", true, false):
			for surface in mesh.mesh.get_surface_count():
				var name: String = mesh.get_active_material(surface).resource_name.to_lower()
				if "leaves" in name or "twig" in name or "canopy_branches" in name:
					continue
				for vertex in mesh.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]:
					var world: Vector3 = mesh.global_transform * vertex
					if world.y < lowest_world_y:
						lowest_world_y = world.y
						lowest = world
		if lowest.y > terrain.data.get_height(lowest) + 0.005:
			floating_trunks += 1
	check(floating_trunks == 0, "rendered trunk base vertices touch terrain")
	print("[grounding-test] counts=", counts, " max_root_gap=", maximum_gap, " rejected=", scene.placement_rejected)


func _test_scenery_layers(scene: Node3D) -> void:
	var conifers := 0
	var variants := {}
	var bad_lods := 0
	for tree in get_tree().get_nodes_in_group("scenic_trees"):
		if tree.get_meta("landscape_asset", "") == scene.CONIFER:
			conifers += 1
			var model = tree.get_child(0)
			variants[model.variant] = true
			if model.get_child_count() != 3:
				bad_lods += 1
			for level in model.get_child_count():
				var mesh = model.get_child(level)
				var triangles := 0
				for surface in mesh.mesh.get_surface_count():
					triangles += mesh.mesh.surface_get_array_index_len(surface) / 3
				if triangles <= 0 or triangles > [5500,3200,1700][level]:
					bad_lods += 1
				if level > 0 and mesh.cast_shadow != GeometryInstance3D.SHADOW_CASTING_SETTING_OFF:
					bad_lods += 1
				if mesh.visibility_range_begin != [0.0,45.0,105.0][level] or mesh.visibility_range_end != [45.0,105.0,450.0][level]:
					bad_lods += 1
	check(conifers > 100, "downloaded pine variants populate the forest")
	check(variants.size() == 3 and bad_lods == 0, "all three imported variants use contiguous authored LOD ranges")
	var grass_triangles := 0
	for cell in scene.get_node("ParticleGrass").particle_nodes:
		grass_triangles += cell.draw_pass_1.surface_get_array_index_len(0) / 3 * cell.amount
	check(grass_triangles < 600000, "grass grid actual mesh allocation below 600k triangles")
	check(scene.get_node("Sun").directional_shadow_max_distance <= 60, "dynamic shadows limited to near scenery")
	var grass: Mesh = scene.get_node("ParticleGrass").mesh
	var vertices: PackedVector3Array = grass.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	var roots := 0
	for point in vertices:
		if is_zero_approx(point.y):
			roots += 1
	check(vertices.size() == 36 and roots == 6, "three curved grass blades retain six ground vertices")
	var low := INF
	var high := -INF
	for x in range(-240, -20, 3):
		var p := Vector2(x, scene._river_center_z(x) + scene.stream_half_width(x) + 4)
		var offset: float = scene.shore_material_distance(p) - scene.bank_distance(p)
		low = minf(low, offset)
		high = maxf(high, offset)
	check(high - low > 1.5, "shoreline material boundary varies along the stream")
	check(scene.get_node_or_null("DistantRidge") != null and scene.get_node_or_null("FarRidge") != null, "two mountain layers preserve distant depth")
	print("[scenery-test] imported_conifers=", conifers, " shore_variation=", high - low)
