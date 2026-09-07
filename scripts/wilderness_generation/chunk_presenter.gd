class_name WildernessChunkPresenter
extends Node3D

## Main-thread presentation layer for cached procedural chunks. Worker threads
## only produce plain data; this node creates rendering and physics gradually.

const Context := preload("res://scripts/wilderness_generation/generation_context.gd")
const Profile := preload("res://scripts/wilderness_generation_profile.gd")

@export_range(1, 2, 1) var active_radius_chunks := 1
@export_range(1, 4, 1) var unload_radius_chunks := 2
@export var authored_half_extent := 512.0

var world_seed: int
var cache: RefCounted
var scheduler: Node
var player: Node3D
var profile: RefCounted
var _loaded: Dictionary = {}
var _pending: Array[Vector2i] = []
var _build_job: Dictionary = {}
var _last_center := Vector2i(999999, 999999)
var _terrain_material: ShaderMaterial
var _water_material: StandardMaterial3D
var _asset_parts: Dictionary = {}


func configure(seed_value: int, cache_value: RefCounted, scheduler_value: Node,
		player_value: Node3D) -> void:
	world_seed = seed_value
	cache = cache_value
	scheduler = scheduler_value
	player = player_value
	profile = Profile.new(world_seed)
	if scheduler != null and scheduler.has_signal("chunk_cached"):
		scheduler.chunk_cached.connect(_on_chunk_cached)


func _ready() -> void:
	_terrain_material = _create_terrain_material()
	_water_material = StandardMaterial3D.new()
	_water_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_water_material.albedo_color = Color(0.12, 0.34, 0.40, 0.68)
	_water_material.roughness = 0.12
	_water_material.metallic_specular = 0.35
	_water_material.cull_mode = BaseMaterial3D.CULL_DISABLED
	set_process(true)


func _create_terrain_material() -> ShaderMaterial:
	var shader := Shader.new()
	shader.code = """
shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;
uniform sampler2D turf_albedo : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D turf_normal_roughness : repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D colluvium_albedo : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D colluvium_normal_roughness : repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D pebble_albedo : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D pebble_normal_roughness : repeat_enable, filter_linear_mipmap_anisotropic;
uniform float texture_scale = 0.22;
varying vec3 wilderness_world_position;
varying vec3 wilderness_world_normal;
vec4 sample_triplanar(sampler2D map, vec3 p, vec3 weights) {
	vec4 x = texture(map, p.zy);
	vec4 y = texture(map, p.xz);
	vec4 z = texture(map, p.xy);
	return x * weights.x + y * weights.y + z * weights.z;
}
void vertex() {
	wilderness_world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wilderness_world_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
}
void fragment() {
	vec3 weights = pow(abs(wilderness_world_normal), vec3(5.0));
	weights /= max(dot(weights, vec3(1.0)), 0.0001);
	vec3 sample_position = wilderness_world_position * texture_scale;
	vec4 turf = sample_triplanar(turf_albedo, sample_position, weights);
	vec4 scree = sample_triplanar(colluvium_albedo, sample_position * 0.72, weights);
	vec4 pebbles = sample_triplanar(pebble_albedo, sample_position * 0.82, weights);
	float turf_roughness = sample_triplanar(turf_normal_roughness, sample_position, weights).a;
	float scree_roughness = sample_triplanar(colluvium_normal_roughness, sample_position * 0.72, weights).a;
	float pebble_roughness = sample_triplanar(pebble_normal_roughness, sample_position * 0.82, weights).a;
	float slope = 1.0 - clamp(abs(wilderness_world_normal.y), 0.0, 1.0);
	float scree_weight = smoothstep(0.10, 0.48, slope);
	float river_weight = smoothstep(0.20, 0.80, COLOR.a);
	vec3 macro_tint = mix(vec3(1.0), clamp(COLOR.rgb * 2.25, vec3(0.72), vec3(1.08)), 0.32);
	macro_tint = mix(macro_tint, vec3(0.94, 0.96, 0.93), river_weight);
	ALBEDO = mix(mix(turf.rgb, scree.rgb, scree_weight), pebbles.rgb, river_weight) * macro_tint;
	ROUGHNESS = mix(mix(turf_roughness, scree_roughness, scree_weight), pebble_roughness, river_weight);
	SPECULAR = 0.18;
}
"""
	var material := ShaderMaterial.new()
	material.shader = shader
	material.set_shader_parameter("turf_albedo", load("res://assets/textures/terrain_prepared/grass004_alb_ht.png"))
	material.set_shader_parameter("turf_normal_roughness", load("res://assets/textures/terrain_prepared/grass004_nrm_rgh.png"))
	material.set_shader_parameter("colluvium_albedo", load("res://assets/textures/wilderness_generated/colluvium_gptimage2_v1_alb_ht.png"))
	material.set_shader_parameter("colluvium_normal_roughness", load("res://assets/textures/wilderness_generated/colluvium_gptimage2_v1_nrm_rgh.png"))
	material.set_shader_parameter("pebble_albedo", load("res://assets/textures/terrain_prepared/gravel041_alb_ht.png"))
	material.set_shader_parameter("pebble_normal_roughness", load("res://assets/textures/terrain_prepared/gravel041_nrm_rgh.png"))
	return material


func _process(_delta: float) -> void:
	if player == null or cache == null:
		return
	var center := _world_to_chunk(Vector2(player.global_position.x, player.global_position.z))
	if center != _last_center:
		_last_center = center
		_refresh_targets(center)
	if not _build_job.is_empty():
		_advance_build_job()
	elif not _pending.is_empty():
		_begin_chunk(_pending.pop_front())


func _refresh_targets(center: Vector2i) -> void:
	if scheduler != null:
		scheduler.request_area(center, 4)
	for coord_value in _loaded.keys():
		var coord: Vector2i = coord_value
		if maxi(absi(coord.x - center.x), absi(coord.y - center.y)) > unload_radius_chunks:
			_loaded[coord].queue_free()
			_loaded.erase(coord)
	if not _build_job.is_empty():
		var building_coord: Vector2i = _build_job["coord"]
		if maxi(absi(building_coord.x - center.x), absi(building_coord.y - center.y)) > unload_radius_chunks:
			var building_root: Node = _build_job["root"]
			if not building_root.is_queued_for_deletion():
				building_root.queue_free()
			_loaded.erase(building_coord)
			_build_job.clear()
	for z in range(center.y - active_radius_chunks, center.y + active_radius_chunks + 1):
		for x in range(center.x - active_radius_chunks, center.x + active_radius_chunks + 1):
			var coord := Vector2i(x, z)
			if _inside_authored_center(coord) or _loaded.has(coord) or coord in _pending:
				continue
			if cache.has_chunk(world_seed, coord):
				_pending.append(coord)


func _on_chunk_cached(coord: Vector2i, _path: String) -> void:
	if _last_center.x == 999999 or _inside_authored_center(coord) or _loaded.has(coord) or coord in _pending:
		return
	if maxi(absi(coord.x - _last_center.x), absi(coord.y - _last_center.y)) <= active_radius_chunks:
		_pending.append(coord)


func _begin_chunk(coord: Vector2i) -> void:
	if _loaded.has(coord):
		return
	var data: Dictionary = cache.load_chunk(world_seed, coord)
	if data.is_empty():
		return
	var root := Node3D.new()
	root.name = "ProceduralChunk_%d_%d" % [coord.x, coord.y]
	root.position = Vector3(coord.x * Context.CHUNK_SIZE_M, 0.0, coord.y * Context.CHUNK_SIZE_M)
	root.set_meta(&"wilderness_chunk", coord)
	add_child(root)
	_loaded[coord] = root
	_build_job = {"coord": coord, "data": data, "root": root, "stage": 0}


func _advance_build_job() -> void:
	var coord: Vector2i = _build_job["coord"]
	var data: Dictionary = _build_job["data"]
	var root: Node3D = _build_job["root"]
	match int(_build_job["stage"]):
		0:
			var terrain_mesh := _build_terrain_mesh(data)
			var terrain_instance := MeshInstance3D.new()
			terrain_instance.name = "Terrain"
			terrain_instance.mesh = terrain_mesh
			terrain_instance.material_override = _terrain_material
			root.add_child(terrain_instance)
			_build_job["terrain_mesh"] = terrain_mesh
		1:
			var terrain_body := StaticBody3D.new()
			terrain_body.name = "TerrainCollision"
			var terrain_shape := CollisionShape3D.new()
			terrain_shape.shape = (_build_job["terrain_mesh"] as ArrayMesh).create_trimesh_shape()
			terrain_body.add_child(terrain_shape)
			root.add_child(terrain_body)
		2:
			var water_mesh := _build_water_mesh(data, coord)
			if water_mesh != null:
				var water_instance := MeshInstance3D.new()
				water_instance.name = "Water"
				water_instance.mesh = water_mesh
				water_instance.material_override = _water_material
				water_instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
				root.add_child(water_instance)
		3:
			_build_feature_multimeshes(root, data.get("features", []), coord)
			_build_job.clear()
			return
	_build_job["stage"] = int(_build_job["stage"]) + 1


func _build_terrain_mesh(data: Dictionary) -> ArrayMesh:
	var resolution := int(data.get("resolution", 0))
	var heights: PackedFloat32Array = data.get("heights", PackedFloat32Array())
	var colors: PackedColorArray = data.get("colors", PackedColorArray())
	var step := Context.CHUNK_SIZE_M / float(resolution - 1)
	var coord: Vector2i = data.get("coord", Vector2i.ZERO)
	var origin := Vector2(coord) * Context.CHUNK_SIZE_M
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for z in resolution:
		for x in resolution:
			var index := z * resolution + x
			var local := Vector2(x * step, z * step)
			var height := heights[index]
			if get_parent() != null and get_parent().has_method("presentation_height"):
				height = get_parent().presentation_height(origin + local)
			st.set_color(colors[index])
			st.add_vertex(Vector3(local.x, height, local.y))
	for z in resolution - 1:
		for x in resolution - 1:
			var a := z * resolution + x
			for index in [a, a + resolution, a + 1, a + 1, a + resolution, a + resolution + 1]:
				st.add_index(index)
	st.generate_normals()
	return st.commit()


func _build_water_mesh(data: Dictionary, coord: Vector2i) -> ArrayMesh:
	var resolution := int(data.get("resolution", 0))
	var step := Context.CHUNK_SIZE_M / float(resolution - 1)
	var origin := Vector2(coord) * Context.CHUNK_SIZE_M
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var quads := 0
	for z in resolution - 1:
		for x in resolution - 1:
			var grid_points := [Vector2(x, z), Vector2(x, z + 1), Vector2(x + 1, z), Vector2(x + 1, z + 1)]
			var vertices: Array[Vector3] = []
			for grid in grid_points:
				var local: Vector2 = grid * step
				var water: float = profile.water_surface_at(origin + local)
				if is_finite(water):
					vertices.append(Vector3(local.x, water, local.y))
			if vertices.size() != 4:
				continue
			for vertex in [vertices[0], vertices[1], vertices[2], vertices[2], vertices[1], vertices[3]]:
				st.add_vertex(vertex)
			quads += 1
	if quads == 0:
		return null
	st.generate_normals()
	return st.commit()


func _build_feature_multimeshes(root: Node3D, features: Array, coord: Vector2i) -> void:
	var grouped: Dictionary = {}
	for feature_value in features:
		var feature: Dictionary = feature_value
		var path := String(feature.get("scene_path", ""))
		if path.is_empty():
			continue
		if not grouped.has(path):
			grouped[path] = []
		grouped[path].append(feature)
	for path_value in grouped:
		var path := String(path_value)
		var parts := _get_asset_parts(path)
		for part_index in parts.size():
			var part: Dictionary = parts[part_index]
			var multimesh := MultiMesh.new()
			multimesh.transform_format = MultiMesh.TRANSFORM_3D
			multimesh.mesh = part["mesh"]
			multimesh.instance_count = grouped[path].size()
			for i in grouped[path].size():
				var feature: Dictionary = grouped[path][i]
				var world_position: Vector3 = feature["position"]
				var local_position := world_position - Vector3(coord.x * Context.CHUNK_SIZE_M, 0.0, coord.y * Context.CHUNK_SIZE_M)
				var base := Transform3D(Basis(Vector3.UP, float(feature.get("yaw", 0.0))).scaled(Vector3.ONE * float(feature.get("scale", 1.0))), local_position)
				multimesh.set_instance_transform(i, base * part["transform"])
			var instance := MultiMeshInstance3D.new()
			instance.name = "%s_%d" % [path.get_file().get_basename(), part_index]
			instance.multimesh = multimesh
			instance.material_override = part.get("material")
			instance.visibility_range_end = Profile.ENTITY_RADIUS_M
			instance.visibility_range_end_margin = 50.0
			root.add_child(instance)


func _get_asset_parts(path: String) -> Array:
	if _asset_parts.has(path):
		return _asset_parts[path]
	var parts: Array = []
	var packed := load(path) as PackedScene
	if packed == null:
		_asset_parts[path] = parts
		return parts
	var scene := packed.instantiate()
	var mesh_nodes := scene.find_children("", "MeshInstance3D", true, false)
	var entered_tree := false
	# Some presentation-only asset scenes construct their meshes in _ready().
	# Let those scenes initialize once, hidden and without processing, then cache
	# only their meshes. Gameplay scenes do not belong in vegetation rules.
	if mesh_nodes.is_empty() and scene is Node3D:
		(scene as Node3D).visible = false
		scene.process_mode = Node.PROCESS_MODE_DISABLED
		add_child(scene)
		entered_tree = true
		mesh_nodes = scene.find_children("", "MeshInstance3D", true, false)
	for node_value in mesh_nodes:
		var mesh_node := node_value as MeshInstance3D
		if mesh_node.mesh == null:
			continue
		var relative := Transform3D.IDENTITY
		var cursor: Node = mesh_node
		while cursor != scene and cursor is Node3D:
			relative = (cursor as Node3D).transform * relative
			cursor = cursor.get_parent()
		parts.append({"mesh": mesh_node.mesh, "material": mesh_node.material_override, "transform": relative})
	if entered_tree:
		remove_child(scene)
	scene.free()
	_asset_parts[path] = parts
	return parts


func _inside_authored_center(coord: Vector2i) -> bool:
	var origin := Vector2(coord) * Context.CHUNK_SIZE_M
	var chunk_rect := Rect2(origin, Vector2.ONE * Context.CHUNK_SIZE_M)
	var center_rect := Rect2(Vector2.ONE * -authored_half_extent, Vector2.ONE * authored_half_extent * 2.0)
	return chunk_rect.intersects(center_rect)


func _world_to_chunk(p: Vector2) -> Vector2i:
	return Vector2i(floori(p.x / Context.CHUNK_SIZE_M), floori(p.y / Context.CHUNK_SIZE_M))
