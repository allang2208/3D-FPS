class_name WildernessChunkGenerator
extends RefCounted

const Context := preload("res://scripts/wilderness_generation/generation_context.gd")
const Profile := preload("res://scripts/wilderness_generation_profile.gd")
const DEFAULT_RESOLUTION := 65


static func generate(seed_value: int, coord: Vector2i, rules: Array[Dictionary],
		resolution: int = DEFAULT_RESOLUTION) -> Dictionary:
	var started := Time.get_ticks_usec()
	var context := Context.new(seed_value, coord)
	var heights := PackedFloat32Array()
	var surfaces := PackedByteArray()
	var colors := PackedColorArray()
	heights.resize(resolution * resolution)
	surfaces.resize(resolution * resolution)
	colors.resize(resolution * resolution)
	var origin: Vector2 = context.chunk_origin()
	var step := Context.CHUNK_SIZE_M / float(resolution - 1)
	var water_samples := 0
	var invalid_water_samples := 0
	for z in resolution:
		for x in resolution:
			var p := origin + Vector2(x * step, z * step)
			var index := z * resolution + x
			var height: float = context.height_at(p)
			heights[index] = height
			colors[index] = context.profile.macro_color_at(p)
			var water: float = context.profile.water_surface_at(p)
			if is_finite(water):
				water_samples += 1
				if height >= water - 0.05:
					invalid_water_samples += 1
	for z in resolution:
		for x in resolution:
			var index := z * resolution + x
			var p := origin + Vector2(x * step, z * step)
			var left := heights[z * resolution + maxi(0, x - 1)]
			var right := heights[z * resolution + mini(resolution - 1, x + 1)]
			var up := heights[maxi(0, z - 1) * resolution + x]
			var down := heights[mini(resolution - 1, z + 1) * resolution + x]
			var gradient := Vector2(right - left, down - up).length() / (step * 2.0)
			var slope_degrees := rad_to_deg(atan(gradient))
			var curvature := (left + right + up + down) * 0.25 - heights[index]
			var surface_id := _surface_id(context.biome_at(p), slope_degrees, curvature)
			surfaces[index] = surface_id
			# Alpha is presentation metadata: 1 marks river/lake substrate for the
			# streamed triplanar material. RGB remains the macro biome tint.
			var macro_color := colors[index]
			macro_color.a = 1.0 if surface_id == 1 else 0.0
			colors[index] = macro_color
	var features: Array[Dictionary] = []
	for rule in rules:
		if not bool(rule.get("enabled", true)):
			continue
		match StringName(rule.get("kind", &"")):
			&"vegetation", &"deposit":
				features.append_array(_scatter_rule(context, rule))
			&"landmark":
				features.append_array(_landmark_rule(context, rule))
	return {
		"format_version": 1,
		"generator_version": Profile.GENERATOR_VERSION,
		"world_seed": seed_value,
		"coord": coord,
		"resolution": resolution,
		"heights": heights,
		"surfaces": surfaces,
		"colors": colors,
		"features": features,
		"validation": {
			"water_samples": water_samples,
			"invalid_water_samples": invalid_water_samples,
		},
		"generation_ms": (Time.get_ticks_usec() - started) / 1000.0,
	}


static func _surface_id(biome: StringName, slope_degrees: float, curvature: float) -> int:
	if biome == &"river":
		return 1
	if slope_degrees > 38.0:
		return 2
	if slope_degrees > 18.0 or curvature > 0.75:
		return 5
	match biome:
		&"alpine": return 2
		&"forest": return 3
		&"dryland": return 4
	return 0


static func _scatter_rule(context: RefCounted, rule: Dictionary) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	var spacing := maxf(1.0, float(rule.get("minimum_spacing", 8.0)))
	var origin: Vector2 = context.chunk_origin()
	var min_cell := Vector2i(floori(origin.x / spacing), floori(origin.y / spacing))
	var max_cell := Vector2i(floori((origin.x + Context.CHUNK_SIZE_M) / spacing), floori((origin.y + Context.CHUNK_SIZE_M) / spacing))
	var candidate_index := 0
	for cell_y in range(min_cell.y, max_cell.y + 1):
		for cell_x in range(min_cell.x, max_cell.x + 1):
			var cell := Vector2i(cell_x, cell_y)
			var jitter := Vector2(context.stable_float(cell, 101), context.stable_float(cell, 103))
			var p := (Vector2(cell) + jitter) * spacing
			if p.x < origin.x or p.y < origin.y or p.x >= origin.x + Context.CHUNK_SIZE_M or p.y >= origin.y + Context.CHUNK_SIZE_M:
				continue
			candidate_index += 1
			if not _matches_common(context, p, rule):
				continue
			var kind := StringName(rule.get("kind", &""))
			var chance := float(rule.get("density", 1.0))
			if kind == &"deposit":
				chance = 1.0 - float(rule.get("vein_threshold", 0.72))
				var geology: Array = rule.get("allowed_geology", [])
				if not geology.is_empty() and context.geology_at(p) not in geology:
					continue
			if context.stable_float(cell, String(rule.get("rule_id", &"")).hash()) > chance:
				continue
			var paths: Array = rule.get("scene_paths", [])
			if paths.is_empty():
				continue
			var variant := int(context.stable_float(cell, 211) * paths.size()) % paths.size()
			var scale_range: Vector2 = rule.get("scale_range", Vector2.ONE)
			var scale := lerpf(scale_range.x, scale_range.y, context.stable_float(cell, 223))
			result.append({
				"feature_id": context.feature_id(StringName(rule.get("rule_id")), candidate_index),
				"rule_id": rule.get("rule_id"),
				"kind": kind,
				"scene_path": paths[variant],
				"position": Vector3(p.x, context.height_at(p), p.y),
				"yaw": context.stable_float(cell, 227) * TAU,
				"scale": scale,
				"harvest_item": rule.get("harvest_item", &""),
			})
	return result


static func _landmark_rule(context: RefCounted, rule: Dictionary) -> Array[Dictionary]:
	var scene_path := String(rule.get("scene_path", ""))
	if scene_path.is_empty():
		return []
	var coord: Vector2i = context.chunk_coord
	var salt := String(rule.get("rule_id", &"")).hash()
	var score: float = context.stable_float(coord, salt)
	if score > float(rule.get("chunk_chance", 0.05)):
		return []
	# Stable global rank enforces max_per_world without depending on which chunks
	# happened to generate first.
	var better_candidates := 0
	var max_per_world := int(rule.get("max_per_world", 5))
	for world_z in range(-20, 20):
		for world_x in range(-20, 20):
			var other := Vector2i(world_x, world_z)
			var other_score: float = context.stable_float(other, salt)
			if other_score <= float(rule.get("chunk_chance", 0.05)) and other_score < score:
				better_candidates += 1
				if better_candidates >= max_per_world:
					return []
	var origin: Vector2 = context.chunk_origin()
	var p := origin + Vector2(
		lerpf(48.0, Context.CHUNK_SIZE_M - 48.0, context.stable_float(coord, 307)),
		lerpf(48.0, Context.CHUNK_SIZE_M - 48.0, context.stable_float(coord, 311)))
	if not _matches_common(context, p, rule) or context.slope_at(p) > float(rule.get("slope_max", 10.0)):
		return []
	return [{
		"feature_id": context.feature_id(StringName(rule.get("rule_id")), 0),
		"rule_id": rule.get("rule_id"),
		"kind": &"landmark",
		"scene_path": scene_path,
		"position": Vector3(p.x, context.height_at(p), p.y),
		"yaw": context.stable_float(coord, 313) * TAU,
		"scale": 1.0,
		"footprint": rule.get("footprint", Vector2(24, 24)),
		"flatten_terrain": rule.get("flatten_terrain", false),
	}]


static func _matches_common(context: RefCounted, p: Vector2, rule: Dictionary) -> bool:
	var height: float = context.height_at(p)
	var height_range: Vector2 = rule.get("height_range", Vector2(-INF, INF))
	if height < height_range.x or height > height_range.y:
		return false
	var slope_range: Vector2 = rule.get("slope_range", Vector2(0.0, rule.get("slope_max", 90.0)))
	var slope: float = context.slope_at(p)
	if slope < slope_range.x or slope > slope_range.y:
		return false
	var water_range: Vector2 = rule.get("water_distance_range", Vector2(-INF, INF))
	var water_distance: float = context.water_distance(p)
	if water_distance < water_range.x or water_distance > water_range.y:
		return false
	var biomes: Array = rule.get("allowed_biomes", [])
	if not biomes.is_empty() and context.biome_at(p) not in biomes:
		return false
	if rule.has("moisture_range"):
		var moisture_range: Vector2 = rule["moisture_range"]
		var moisture: float = context.moisture_at(p)
		if moisture < moisture_range.x or moisture > moisture_range.y:
			return false
	return true
