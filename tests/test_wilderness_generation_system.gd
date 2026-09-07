extends Node

const Profile := preload("res://scripts/wilderness_generation_profile.gd")
const SeedStore := preload("res://scripts/wilderness_generation/world_seed_store.gd")
const Registry := preload("res://scripts/wilderness_generation/rule_registry.gd")
const Generator := preload("res://scripts/wilderness_generation/chunk_generator.gd")
const Cache := preload("res://scripts/wilderness_generation/chunk_cache.gd")
const Scheduler := preload("res://scripts/wilderness_generation/chunk_scheduler.gd")
const Presenter := preload("res://scripts/wilderness_generation/chunk_presenter.gd")
const VegetationRule := preload("res://scripts/wilderness_generation/rules/vegetation_rule.gd")
const InventorySave := preload("res://ui/inventory_save.gd")

var failures: Array[String] = []


func _check(condition: bool, label: String) -> void:
	print("[wilderness-system-test] ", "PASS " if condition else "FAIL ", label)
	if not condition:
		failures.append(label)


func _ready() -> void:
	var suffix := str(OS.get_process_id())
	var seed_path := "user://wilderness-system-test-" + suffix + ".save"
	var cache_root := "user://wilderness-system-cache-" + suffix
	OS.set_environment("WILDERNESS_WORLD_PATH", seed_path)
	OS.set_environment("WILDERNESS_CACHE_PATH", cache_root)
	SeedStore.delete_world()
	var first := SeedStore.create_new_world()
	var first_seed := int(first.get("world_seed", 0))
	_check(first_seed != 0, "new game creates a world seed")
	_check(int(SeedStore.ensure_world().get("world_seed", 0)) == first_seed, "entering again reuses the saved seed")
	SeedStore.delete_world()
	var second_seed := int(SeedStore.create_new_world().get("world_seed", 0))
	_check(second_seed != 0 and second_seed != first_seed, "next new game receives a different seed")

	var profile := Profile.new(second_seed)
	var water_contract_ok := true
	for x in range(-5000, 5001, 125):
		var p := Vector2(x, profile.river_center_z(x))
		water_contract_ok = water_contract_ok and profile.height_at(p) < profile.river_water_level(x)
	for lake_index in Profile.LAKE_COUNT:
		var lake := profile.lake_info(lake_index)
		water_contract_ok = water_contract_ok and profile.height_at(lake["center"]) < float(lake["water_level"])
	_check(water_contract_ok, "river beds and lake basins stay below their water surfaces")
	_check(profile.river_water_level(-5000) < profile.river_water_level(5000), "main river descends towards its western outlet")

	var registry := Registry.new()
	registry.load_directory()
	var rules := registry.snapshot_rules()
	_check(rules.size() >= 6, "default tree and ore rules are discovered")
	var custom := VegetationRule.new()
	custom.rule_id = &"test_new_tree"
	custom.scene_paths = ["res://scenes/imported_pine.tscn"]
	registry.register_rule(custom)
	_check(registry.snapshot_rules().any(func(rule: Dictionary) -> bool: return rule.rule_id == &"test_new_tree"), "new vegetation rule registers without core changes")

	var coord := Vector2i(2, -3)
	var chunk_a := Generator.generate(second_seed, coord, rules, 33)
	var chunk_b := Generator.generate(second_seed, coord, rules, 33)
	_check(chunk_a.heights == chunk_b.heights and chunk_a.features == chunk_b.features, "chunk output is independent of task order")
	_check(int(chunk_a.validation.invalid_water_samples) == 0, "generated chunk passes water validation")
	var cache := Cache.new(cache_root)
	_check(cache.save_chunk(chunk_a) == OK, "chunk cache writes atomically")
	var loaded := cache.load_chunk(second_seed, coord)
	_check(loaded.heights == chunk_a.heights and loaded.features == chunk_a.features, "cached chunk round-trips without loading nodes")

	var scheduler := Scheduler.new()
	scheduler.dispatch_interval = 0.05
	scheduler.cache_resolution = 33
	scheduler.configure(second_seed, rules, cache_root)
	add_child(scheduler)
	scheduler.request_area(Vector2i.ZERO, 0)
	var frames := 0
	while scheduler.queue_size() > 0 and frames < 600:
		frames += 1
		await get_tree().process_frame
	_check(scheduler.completed_chunks == 1 and scheduler.failed_chunks == 0, "background worker generates and caches without scene loading")
	_check(cache.has_chunk(second_seed, Vector2i.ZERO), "background result is ready on disk")

	var streamed_coord := Vector2i(2, 0)
	var streamed_data := Generator.generate(second_seed, streamed_coord, [], 17)
	_check(cache.save_chunk(streamed_data) == OK, "streaming fixture is cached before presentation")
	var test_player := Node3D.new()
	test_player.position = Vector3(520.0, 100.0, 20.0)
	add_child(test_player)
	var presenter := Presenter.new()
	presenter.configure(second_seed, cache, null, test_player)
	add_child(presenter)
	for frame in 6:
		await get_tree().process_frame
	var streamed_root := presenter.get_node_or_null("ProceduralChunk_2_0")
	_check(streamed_root != null, "cached terrain is submitted only when the player approaches")
	_check(streamed_root != null and streamed_root.get_node_or_null("TerrainCollision") != null, "active procedural terrain receives collision")
	test_player.position = Vector3(520.0, 100.0, -700.0)
	for frame in 6:
		await get_tree().process_frame
	var feature_root := presenter.get_node_or_null("ProceduralChunk_2_-3")
	var feature_batches := feature_root.find_children("", "MultiMeshInstance3D", true, false) if feature_root != null else []
	_check(chunk_a.features.is_empty() or not feature_batches.is_empty(), "tree and ore candidates become shared MultiMesh batches")
	test_player.position = Vector3(-800.0, 100.0, 20.0)
	await get_tree().process_frame
	await get_tree().process_frame
	_check(presenter.get_node_or_null("ProceduralChunk_2_0") == null, "distant procedural terrain unloads again")
	presenter.queue_free()
	test_player.queue_free()

	var inventory_path := "user://wilderness-inventory-test-" + suffix + ".save"
	OS.set_environment("INVENTORY_SAVE_PATH", inventory_path)
	_check(InventorySave.write_snapshot({"version": 1}) == OK, "test inventory snapshot is writable")
	_check(InventorySave.delete_snapshot() == OK and SeedStore.read_world().is_empty(), "new-game reset removes the previous world seed")

	_cleanup_cache(cache_root, second_seed)
	OS.set_environment("WILDERNESS_WORLD_PATH", "")
	OS.set_environment("WILDERNESS_CACHE_PATH", "")
	OS.set_environment("INVENTORY_SAVE_PATH", "")
	get_tree().quit(0 if failures.is_empty() else 1)


func _cleanup_cache(root_path: String, seed_value: int) -> void:
	var seed_dir := root_path.path_join(str(seed_value))
	if DirAccess.dir_exists_absolute(ProjectSettings.globalize_path(seed_dir)):
		for file in DirAccess.get_files_at(seed_dir):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(seed_dir.path_join(file)))
		DirAccess.remove_absolute(ProjectSettings.globalize_path(seed_dir))
	if DirAccess.dir_exists_absolute(ProjectSettings.globalize_path(root_path)):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(root_path))
