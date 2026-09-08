extends Node3D
## Independent real-terrain combat laboratory. No production spawn/save changes.
const TYPES = ["ordinary_zombie", "runner_zombie", "miner_workwear_zombie"]
var world: Node3D
var actors: Node3D
var player
var gun
var automated := false
var hits := 0
var kills := 0
var shots := 0
var count_index := 1
var label: Label
var spawning := false
var prepared := false
var packs := {}
var director: Node

func _enter_tree() -> void:
	for key in ["INVENTORY_SAVE_PATH", "GAME_SETTINGS_PATH"]:
		if OS.get_environment(key).is_empty():
			OS.set_environment(key, "user://combat-study-%d-%s" % [OS.get_process_id(), key])
	for key in ["WILDERNESS_SAVE_PATH", "WILDERNESS_WORLD_PATH"]:
		OS.set_environment(key, "user://combat-study-%d-%s" % [OS.get_process_id(), key])
	OS.set_environment("WILDERNESS_DISABLE_BACKGROUND_CACHE", "1")
	preload("res://scripts/wilderness_generation/world_seed_store.gd").write_world({"format_version":1,"world_seed":1788835027157102,"landform_revision":8})
	for kind in TYPES + ["foreman_zombie", "ore_spider"]:
		ResourceLoader.load_threaded_request("res://scenes/enemies/%s.tscn" % kind)

func _ready() -> void:
	world = load("res://scenes/demo_terrain.tscn").instantiate()
	add_child(world)
	actors = Node3D.new()
	actors.name = "CombatActors"
	world.add_child(actors)
	player = world.get_node("Player")
	await get_tree().create_timer(5.0).timeout
	player.add_to_group("player")
	for kind in TYPES + ["foreman_zombie", "ore_spider"]:
		var path := "res://scenes/enemies/%s.tscn" % kind
		while ResourceLoader.load_threaded_get_status(path) == ResourceLoader.THREAD_LOAD_IN_PROGRESS:
			await get_tree().process_frame
		if ResourceLoader.load_threaded_get_status(path) != ResourceLoader.THREAD_LOAD_LOADED:
			push_error("Combat asset failed: " + path)
			get_tree().quit(1)
			return
		packs[kind] = ResourceLoader.load_threaded_get(path)
	player.position = grounded(Vector3(14, 0, 30))
	player.rotation = Vector3.ZERO
	player.max_hp = 1000000
	player.hp = player.max_hp
	player.damaged.connect(func(_hp): hits += 1)
	gun = player.get_node("Camera3D/Gun")
	# Use the remote baseline's equipped weapon and reserve contract.
	gun.reserve = 600
	gun.shot.connect(func(_ammo, _reserve): shots += 1)
	var layer := CanvasLayer.new()
	add_child(layer)
	label = Label.new()
	label.position = Vector2(360, 8)
	label.text = "旷野战斗测试 · F11: 10/30/60 只 · F12: 工头+矿蛛 · 测试生命值"
	layer.add_child(label)
	prepared = true
	if OS.get_cmdline_user_args().has("--foreman-review"):
		director = preload("res://scripts/roaming_combat_spawner.gd").new()
		director.study = self
		director.enabled = false
		add_child(director)
		await populate_foreman_review()
	elif not automated:
		director = preload("res://scripts/roaming_combat_spawner.gd").new()
		director.study = self
		add_child(director)

func grounded(point: Vector3) -> Vector3:
	point.y = world.terrain.data.get_height(point) + 0.06
	return point

func populate(count: int, bosses := false) -> void:
	if spawning:
		return
	spawning = true
	var started := Time.get_ticks_usec()
	var max_submit_us := 0
	for child in actors.get_children():
		child.queue_free()
	await get_tree().process_frame
	hits = 0
	kills = 0
	shots = 0
	player.hp = player.max_hp
	for i in count:
		var submit_started := Time.get_ticks_usec()
		var kind: String = TYPES[i % TYPES.size()]
		if bosses:
			kind = "foreman_zombie" if i % 2 == 0 else "ore_spider"
		var actor = packs[kind].instantiate()
		actor.name = "%s_%d" % [kind, i]
		actor.set_meta("study_kind", kind)
		var angle := -1.25 + 2.5 * float(i % 10) / 9.0
		var radius := 5.0 + float(i / 10) * 1.2
		actor.position = grounded(player.position + Vector3(sin(angle), 0, -cos(angle)) * radius)
		actor.setup(player, func(): kills += 1)
		actors.add_child(actor)
		max_submit_us = maxi(max_submit_us, Time.get_ticks_usec() - submit_started)
		# Spread creation/import submission; this phase is excluded from steady-state timing.
		await get_tree().process_frame
	spawning = false
	print("COMBAT_SPAWN ", JSON.stringify({"count":count,"bosses":bosses,"elapsed_ms":(Time.get_ticks_usec()-started)/1000.0,"max_single_submit_ms":max_submit_us/1000.0,"cached_packs":packs.size()}))

func _unhandled_key_input(event: InputEvent) -> void:
	if automated or not prepared or not event.is_pressed() or event.is_echo():
		return
	if event is InputEventKey and event.keycode == KEY_F11:
		count_index = (count_index + 1) % 3
		if not director.enabled:
			for actor in actors.get_children():
				actor.queue_free()
		director.enabled = true
		director.target_count = [10, 30, 60][count_index]
	if event is InputEventKey and event.keycode == KEY_F12:
		director.enabled = false
		populate(2, true)

func populate_foreman_review() -> void:
	for i in range(4):
		var kind := "foreman_zombie" if i == 0 else "ordinary_zombie"
		var actor = packs[kind].instantiate()
		actor.name = "ForemanReview" if i == 0 else "RallyAlly%d" % i
		actor.set_meta("study_kind", kind)
		actor.position = grounded(player.position + Vector3(0 if i == 0 else (i-2)*2.4, 0, -8 if i == 0 else -10))
		actor.setup(player, func(): kills += 1)
		actor.set_physics_process(false)
		actors.add_child(actor)
		actor.set_physics_process(false)
		await get_tree().process_frame
	for actor in actors.get_children():
		actor.set_physics_process(true)
	print("FOREMAN_REVIEW_READY actors=4 model=foreman_v11")
