class_name WildernessGenerationProfile
extends RefCounted

## Deterministic, world-space wilderness rules shared by far rendering and
## future streamed Terrain3D regions. All queries depend only on seed + world
## coordinates, so chunk load order cannot change the generated landscape.

const NEAR_WORLD_SIZE_M := 1024.0
const WORLD_SIZE_M := NEAR_WORLD_SIZE_M * 10.0
const NEAR_HALF_EXTENT_M := NEAR_WORLD_SIZE_M * 0.5
const WORLD_HALF_EXTENT_M := WORLD_SIZE_M * 0.5
const ENTITY_RADIUS_M := 450.0
const IMPOSTOR_RADIUS_M := 1500.0
const GENERATOR_VERSION := 5
const LAKE_COUNT := 2

var seed: int
var _continent := FastNoiseLite.new()
var _hills := FastNoiseLite.new()
var _detail := FastNoiseLite.new()
var _ridge := FastNoiseLite.new()
var _drainage := FastNoiseLite.new()
var _moisture := FastNoiseLite.new()
var _temperature := FastNoiseLite.new()
var _lakes: Array[Dictionary] = []


func _init(world_seed: int = 1) -> void:
	configure(world_seed)


func configure(world_seed: int) -> void:
	seed = world_seed
	_configure_noise(_continent, seed + 11, 0.00042, 4, 0.52)
	_configure_noise(_hills, seed + 37, 0.00165, 3, 0.48)
	_configure_noise(_detail, seed + 71, 0.0065, 2, 0.42)
	_configure_noise(_ridge, seed + 83, 0.00125, 4, 0.48)
	_configure_noise(_drainage, seed + 91, 0.0028, 3, 0.46)
	_configure_noise(_moisture, seed + 101, 0.0009, 3, 0.5)
	_configure_noise(_temperature, seed + 149, 0.00062, 2, 0.5)
	_lakes.clear()
	for lake_index in LAKE_COUNT:
		_lakes.append(_make_lake_info(lake_index))


func _configure_noise(noise: FastNoiseLite, noise_seed: int, frequency: float,
		octaves: int, gain: float) -> void:
	noise.seed = noise_seed
	noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	noise.frequency = frequency
	noise.fractal_type = FastNoiseLite.FRACTAL_FBM
	noise.fractal_octaves = octaves
	noise.fractal_gain = gain


func height_at(p: Vector2) -> float:
	var edge := maxf(absf(p.x), absf(p.y)) / WORLD_HALF_EXTENT_M
	var island_falloff := smoothstep(0.72, 1.0, edge)
	var macro := _continent.get_noise_2d(p.x, p.y) * 92.0
	var rolling := _hills.get_noise_2d(p.x, p.y) * 32.0
	var surface := _detail.get_noise_2d(p.x, p.y) * 5.0
	var base_height := macro + rolling + surface - island_falloff * 70.0
	# Narrow ridged contours and drainage cuts add meso-scale landform detail
	# without turning the ground into high-frequency noise. Lowlands remain calm.
	var upland := smoothstep(8.0, 72.0, base_height)
	var ridge_line := pow(1.0 - absf(_ridge.get_noise_2d(p.x, p.y)), 6.0)
	var drainage_line := pow(1.0 - absf(_drainage.get_noise_2d(p.x, p.y)), 11.0)
	base_height += ridge_line * 15.0 * upland
	base_height -= drainage_line * 6.5 * upland
	var river_cut := river_influence(p)
	var river_bed := river_water_level(p.x) - 4.0 - river_cut * 2.0
	var result := lerpf(base_height, river_bed, river_cut)
	for lake_index in LAKE_COUNT:
		var lake := lake_info(lake_index)
		var center: Vector2 = lake["center"]
		var radii: Vector2 = lake["radii"]
		var normalized := Vector2((p.x - center.x) / radii.x, (p.y - center.y) / radii.y).length()
		if normalized < 1.18:
			var lake_bed: float = lake["water_level"] - 6.0 + normalized * 1.5
			result = lerpf(lake_bed, result, smoothstep(0.82, 1.18, normalized))
	return result


func river_center_z(x: float) -> float:
	var phase := float(abs(seed) % 997) * 0.013
	var authored_extension := 9.0 * sin(x / 49.0) + 4.0 * sin(x / 23.0)
	var wilderness_course := sin(x / 620.0 + phase) * 310.0 + sin(x / 190.0 - phase * 0.7) * 82.0
	var wilderness_weight := smoothstep(NEAR_HALF_EXTENT_M, NEAR_HALF_EXTENT_M + 700.0, absf(x))
	return lerpf(authored_extension, wilderness_course, wilderness_weight)


func river_half_width(x: float) -> float:
	var authored_width := 2.8 + 1.2 * sin(x / 31.0) + 0.65 * sin(x / 12.0)
	var wilderness_width := 18.0 + (sin(x / 270.0 + float(seed % 113)) + 1.0) * 7.0
	var wilderness_weight := smoothstep(NEAR_HALF_EXTENT_M, NEAR_HALF_EXTENT_M + 700.0, absf(x))
	return lerpf(authored_width, wilderness_width, wilderness_weight)


func river_water_level(x: float) -> float:
	# The authored valley drains west. Preserve its water height at both seams,
	# then continue monotonically towards the lower western outlet.
	if x < -NEAR_HALF_EXTENT_M:
		return lerpf(-28.0, 0.0, clampf((x + WORLD_HALF_EXTENT_M) / (WORLD_HALF_EXTENT_M - NEAR_HALF_EXTENT_M), 0.0, 1.0))
	if x > NEAR_HALF_EXTENT_M:
		var east_seam := (NEAR_HALF_EXTENT_M + 275.0) * 0.035
		return lerpf(east_seam, 58.0, clampf((x - NEAR_HALF_EXTENT_M) / (WORLD_HALF_EXTENT_M - NEAR_HALF_EXTENT_M), 0.0, 1.0))
	return maxf(0.0, (x + 275.0) * 0.035)


func lake_info(index: int) -> Dictionary:
	return _lakes[index]


func _make_lake_info(index: int) -> Dictionary:
	var t := (float(index) + 1.0) / (float(LAKE_COUNT) + 1.0)
	var jitter := signed_hash_float(seed, Vector2i(index, 917), 31) * 0.08
	var x := lerpf(-WORLD_HALF_EXTENT_M * 0.62, WORLD_HALF_EXTENT_M * 0.48, clampf(t + jitter, 0.12, 0.88))
	var center := Vector2(x, river_center_z(x))
	var rx := 95.0 + hash_float(seed, Vector2i(index, 311), 17) * 105.0
	var rz := rx * (1.15 + hash_float(seed, Vector2i(index, 619), 23) * 0.65)
	return {"center": center, "radii": Vector2(rx, rz), "water_level": river_water_level(x)}


func river_influence(p: Vector2) -> float:
	var distance := absf(p.y - river_center_z(p.x))
	return 1.0 - smoothstep(river_half_width(p.x), river_half_width(p.x) + 95.0, distance)


func water_distance(p: Vector2) -> float:
	var closest := absf(p.y - river_center_z(p.x)) - river_half_width(p.x)
	for lake_index in LAKE_COUNT:
		var lake := lake_info(lake_index)
		var center: Vector2 = lake["center"]
		var radii: Vector2 = lake["radii"]
		var normalized := Vector2((p.x - center.x) / radii.x, (p.y - center.y) / radii.y).length()
		closest = minf(closest, (normalized - 1.0) * minf(radii.x, radii.y))
	return closest


func water_surface_at(p: Vector2) -> float:
	for lake_index in LAKE_COUNT:
		var lake := lake_info(lake_index)
		var center: Vector2 = lake["center"]
		var radii: Vector2 = lake["radii"]
		if Vector2((p.x - center.x) / radii.x, (p.y - center.y) / radii.y).length() <= 1.0:
			return lake["water_level"]
	if absf(p.y - river_center_z(p.x)) <= river_half_width(p.x):
		return river_water_level(p.x)
	return NAN


func moisture_at(p: Vector2) -> float:
	return clampf((_moisture.get_noise_2d(p.x, p.y) + 1.0) * 0.5 + maxf(0.0, 1.0 - water_distance(p) / 240.0) * 0.45, 0.0, 1.0)


func temperature_at(p: Vector2) -> float:
	return clampf((_temperature.get_noise_2d(p.x, p.y) + 1.0) * 0.5 - maxf(0.0, height_at(p)) / 360.0, 0.0, 1.0)


func slope_at(p: Vector2, sample_distance: float = 2.0) -> float:
	var dx := height_at(p + Vector2(sample_distance, 0.0)) - height_at(p - Vector2(sample_distance, 0.0))
	var dz := height_at(p + Vector2(0.0, sample_distance)) - height_at(p - Vector2(0.0, sample_distance))
	return rad_to_deg(atan(Vector2(dx, dz).length() / (sample_distance * 2.0)))


func geology_at(p: Vector2) -> StringName:
	var band := signed_hash_float(seed, Vector2i(floori(p.x / 640.0), floori(p.y / 640.0)), 71)
	if height_at(p) > 78.0 or band > 0.48:
		return &"granite"
	if band < -0.42:
		return &"sedimentary"
	return &"metamorphic"


func biome_at(p: Vector2) -> StringName:
	var height := height_at(p)
	var water := water_distance(p)
	var wet := clampf((_moisture.get_noise_2d(p.x, p.y) + 1.0) * 0.5 + maxf(0.0, 1.0 - water / 240.0) * 0.45, 0.0, 1.0)
	var warm := clampf((_temperature.get_noise_2d(p.x, p.y) + 1.0) * 0.5 - maxf(0.0, height) / 360.0, 0.0, 1.0)
	if water <= 0.0:
		return &"river"
	if height > 82.0:
		return &"alpine"
	if wet > 0.6:
		return &"forest"
	if warm > 0.64 and wet < 0.42:
		return &"dryland"
	return &"meadow"


func detail_band(distance_to_player: float) -> StringName:
	if distance_to_player <= ENTITY_RADIUS_M:
		return &"entity"
	if distance_to_player <= IMPOSTOR_RADIUS_M:
		return &"impostor"
	return &"texture"


func macro_color_at(p: Vector2) -> Color:
	var biome := biome_at(p)
	var color := Color(0.33, 0.39, 0.24)
	match biome:
		&"river":
			color = Color(0.16, 0.30, 0.35)
		&"alpine":
			color = Color(0.35, 0.36, 0.34)
		&"forest":
			color = Color(0.16, 0.25, 0.12)
		&"dryland":
			color = Color(0.43, 0.37, 0.24)
		&"meadow":
			color = Color(0.31, 0.40, 0.22)
	var variation := _detail.get_noise_2d(p.x, p.y) * 0.055
	return Color(color.r + variation, color.g + variation, color.b + variation, 1.0)


static func hash_u32(world_seed: int, cell: Vector2i, salt: int = 0) -> int:
	var value := int(world_seed) ^ (cell.x * 73856093) ^ (cell.y * 19349663) ^ (salt * 83492791)
	value = ((value >> 16) ^ value) * 0x45d9f3b
	value = ((value >> 16) ^ value) * 0x45d9f3b
	return abs((value >> 16) ^ value)


static func hash_float(world_seed: int, cell: Vector2i, salt: int = 0) -> float:
	return float(hash_u32(world_seed, cell, salt) & 0x00ffffff) / float(0x01000000)


static func signed_hash_float(world_seed: int, cell: Vector2i, salt: int = 0) -> float:
	return hash_float(world_seed, cell, salt) * 2.0 - 1.0
