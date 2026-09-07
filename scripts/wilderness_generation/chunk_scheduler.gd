class_name WildernessChunkScheduler
extends Node

signal chunk_cached(coord: Vector2i, path: String)
signal queue_drained()

const Generator := preload("res://scripts/wilderness_generation/chunk_generator.gd")
const Cache := preload("res://scripts/wilderness_generation/chunk_cache.gd")
const Context := preload("res://scripts/wilderness_generation/generation_context.gd")

@export_range(1, 4, 1) var max_worker_tasks := 2
@export_range(0.05, 2.0, 0.05) var dispatch_interval := 0.2
@export_range(17, 257, 16) var cache_resolution := 65

var world_seed: int
var rules_snapshot: Array[Dictionary] = []
var cache: RefCounted
var _pending: Array[Vector2i] = []
var _queued: Dictionary = {}
var _active: Dictionary = {}
var _results: Dictionary = {}
var _results_mutex := Mutex.new()
var _dispatch_accumulator := 0.0
var _drained_emitted := false
var completed_chunks := 0
var failed_chunks := 0


func configure(seed_value: int, rules: Array[Dictionary], cache_root: String = "") -> void:
	world_seed = seed_value
	rules_snapshot = rules.duplicate(true)
	cache = Cache.new(cache_root)


func _ready() -> void:
	set_process(true)


func request_area(center: Vector2i, radius_chunks: int) -> void:
	_drained_emitted = false
	var additions: Array[Vector2i] = []
	for z in range(center.y - radius_chunks, center.y + radius_chunks + 1):
		for x in range(center.x - radius_chunks, center.x + radius_chunks + 1):
			if x < -20 or x > 19 or z < -20 or z > 19:
				continue
			var coord := Vector2i(x, z)
			if _queued.has(coord) or cache.has_chunk(world_seed, coord):
				continue
			additions.append(coord)
	additions.sort_custom(func(a: Vector2i, b: Vector2i) -> bool:
		return a.distance_squared_to(center) < b.distance_squared_to(center))
	for coord in additions:
		_pending.append(coord)
		_queued[coord] = true


func _process(delta: float) -> void:
	_collect_completed()
	_dispatch_accumulator += delta
	if _dispatch_accumulator >= dispatch_interval:
		_dispatch_accumulator = 0.0
		_dispatch_tasks()
	if _pending.is_empty() and _active.is_empty() and not _drained_emitted:
		_drained_emitted = true
		queue_drained.emit()


func _exit_tree() -> void:
	# Worker callables reference this node, so finish the small outstanding jobs
	# before the scene tree is allowed to free it.
	set_process(false)
	for task_id_value in _active.keys():
		WorkerThreadPool.wait_for_task_completion(int(task_id_value))
	_active.clear()


func _dispatch_tasks() -> void:
	while _active.size() < max_worker_tasks and not _pending.is_empty():
		var coord: Vector2i = _pending.pop_front()
		var callable := Callable(self, "_worker_generate").bind(coord, rules_snapshot, cache_resolution, String(cache.root_path))
		var task_id := WorkerThreadPool.add_task(callable, true, "wilderness_%d_%d" % [coord.x, coord.y])
		_active[task_id] = coord


func _worker_generate(coord: Vector2i, rules: Array[Dictionary], resolution: int, cache_root: String) -> void:
	var data: Dictionary = Generator.generate(world_seed, coord, rules, resolution)
	var result: Dictionary
	if data.is_empty() or int(data.get("validation", {}).get("invalid_water_samples", 1)) > 0:
		result = {"coord": coord, "error": ERR_INVALID_DATA}
	else:
		var worker_cache: RefCounted = Cache.new(cache_root)
		var error: Error = worker_cache.save_chunk(data)
		result = {
			"coord": coord,
			"error": error,
			"path": worker_cache.chunk_path(world_seed, coord),
			"generation_ms": data.get("generation_ms", 0.0),
		}
	_results_mutex.lock()
	_results[coord] = result
	_results_mutex.unlock()


func _collect_completed() -> void:
	var finished: Array[int] = []
	for task_id in _active:
		if WorkerThreadPool.is_task_completed(task_id):
			finished.append(task_id)
	# Commit/cache at most one completed chunk per frame.
	if finished.is_empty():
		return
	var task_id := finished[0]
	var coord: Vector2i = _active[task_id]
	var wait_error: Error = WorkerThreadPool.wait_for_task_completion(task_id)
	_results_mutex.lock()
	var data: Dictionary = _results.get(coord, {"coord": coord, "error": wait_error})
	_results.erase(coord)
	_results_mutex.unlock()
	_active.erase(task_id)
	if int(data.get("error", FAILED)) == OK:
		completed_chunks += 1
		chunk_cached.emit(coord, String(data.get("path", "")))
	else:
		failed_chunks += 1


func queue_size() -> int:
	return _pending.size() + _active.size()
