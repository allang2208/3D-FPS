extends "res://scenes/demo_terrain.gd"

## Authored scenic corridor; inherits the existing player/HUD/portal contracts.
## Bump CACHE_REVISION when changing the height/control/color recipe. -- --rebuild-valley
## regenerates only this scene's cache, never the original demo regions.
const CACHE_REVISION := "valley_02"
const VALLEY_DATA := "user://terrain_cache/" + CACHE_REVISION
const ARRIVAL := Vector2(-90.0, 32.0)
const FIR := "res://assets/models/polyhaven/fir_sapling/fir_sapling_2k.gltf"
const CANOPY_TREE := "res://assets/models/polyhaven/island_tree_02/island_tree_02_1k.gltf"
const BOULDER := "res://assets/models/polyhaven/boulder_01/boulder_01_2k.gltf"
const ROCK := "res://assets/models/polyhaven/rock_09/rock_09_2k.gltf"
var _land_noise := FastNoiseLite.new()
var _detail_meshes: Dictionary = {}
var _fir_materials: Dictionary = {}
var _batch_geometry: Dictionary = {}


func _ready() -> void:
	_land_noise.seed = 9305
	_land_noise.noise_type = FastNoiseLite.TYPE_PERLIN
	_land_noise.frequency = 0.018
	_land_noise.fractal_octaves = 3
	super._ready()
	_build_distant_ridge()


func _river_center_z(x: float) -> float:
	return 9.0 * sin(x / 49.0) + 4.0 * sin(x / 23.0)


func stream_half_width(x: float) -> float:
	return 2.8 + 1.2 * sin(x / 31.0) + 0.65 * sin(x / 12.0)


func water_height(x: float) -> float:
	return maxf(0.0, (x + 275.0) * 0.035)


func lake_radius(p: Vector2) -> float:
	return Vector2((p.x + 385.0) / 110.0, p.y / 150.0).length()


func bank_distance(p: Vector2) -> float:
	# Same boundary is used for terrain, wetness and vegetation placement.
	var stream := absf(p.y - _river_center_z(p.x)) - stream_half_width(p.x)
	if p.x < -260.0:
		return minf(stream, (lake_radius(p) - 1.0) * 110.0)
	return stream


func valley_height(p: Vector2) -> float:
	var x := p.x
	var d := absf(p.y - _river_center_z(x))
	var bank := d - stream_half_width(x)
	var noise := _land_noise.get_noise_2d(x, p.y)
	var h := water_height(x) - 0.65
	h += smoothstep(-0.6, 3.2, bank) * 1.2
	h += smoothstep(3.0, 62.0, bank) * (8.0 + noise * 4.0)
	# Left rock shoulder / right wooded ridge, lowered towards the lake mouth.
	var enclosed := smoothstep(-310.0, -160.0, x)
	var ridge_center := 84.0 if p.y > _river_center_z(x) else 72.0
	h += exp(-pow((d - ridge_center) / 34.0, 2.0)) * enclosed * (18.0 + noise * 9.0)
	h += noise * 1.3 * smoothstep(0.0, 9.0, bank)
	# The lake is a real basin; its water plane stays at a single elevation.
	var lr := lake_radius(p)
	if lr < 1.15:
		h = lerpf(-2.6 + noise * 0.3, h, smoothstep(0.86, 1.15, lr))
	return h


func _build_terrain() -> Terrain3D:
	var t := Terrain3D.new()
	t.name = "Terrain3D"
	add_child(t)
	t.region_size = 256
	t.material.auto_shader = false
	t.material.world_background = Terrain3DMaterial.NONE
	t.material.dual_scaling = true
	t.material.set_shader_param("blend_sharpness", 0.35)
	t.assets = Terrain3DAssets.new()
	var textures := ["grass001", "ground037", "gravel041", "rock063", "ground020"]
	for i in textures.size():
		var ta := Terrain3DTextureAsset.new()
		ta.name = textures[i]
		ta.albedo_texture = load(PREP_TEX % [textures[i], "alb_ht"])
		ta.normal_texture = load(PREP_TEX % [textures[i], "nrm_rgh"])
		ta.normal_depth = 0.4
		ta.roughness = 0.30
		ta.ao_strength = 1.0
		ta.uv_scale = 0.32 if i != 3 else 0.12
		ta.detiling_rotation = 0.15
		t.assets.set_texture(i, ta)
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(VALLEY_DATA))
	t.data_directory = VALLEY_DATA
	var cache_ok := FileAccess.file_exists(VALLEY_DATA + "/complete.txt")
	if cache_ok and not OS.get_cmdline_user_args().has("--rebuild-valley"):
		t.data.load_directory(VALLEY_DATA)
		print("[valley] loaded ", CACHE_REVISION)
	else:
		_generate_maps(t)
		t.data.save_directory(VALLEY_DATA)
		var marker := FileAccess.open(VALLEY_DATA + "/complete.txt", FileAccess.WRITE)
		marker.store_string(CACHE_REVISION)
	t.collision.set_mode(Terrain3DCollision.FULL_GAME)
	t.collision.build()
	return t


func _generate_maps(t: Terrain3D) -> void:
	var height := Image.create_empty(1024, 1024, false, Image.FORMAT_RF)
	var colors := Image.create_empty(1024, 1024, false, Image.FORMAT_RGBA8)
	# Terrain3D controls are uint32 bit patterns, NOT float numeric values.
	var bits := PackedByteArray()
	bits.resize(1024 * 1024 * 4)
	for iz in 1024:
		for ix in 1024:
			var p := Vector2(ix - 512.0, iz - 512.0)
			var h := valley_height(p)
			height.set_pixel(ix, iz, Color(h, 0, 0))
			var bank := bank_distance(p)
			var n := _land_noise.get_noise_2d(p.x, p.y)
			var slope := Vector2(valley_height(p + Vector2.RIGHT) - h,
				valley_height(p + Vector2.DOWN) - h).length()
			var base := 0
			var overlay := 4
			var blend := clampf((n + 0.15) * 0.35, 0.0, 0.3)
			if bank < 5.0:
				base = 2
				overlay = 1
				blend = clampf(0.35 + n * 0.8, 0.1, 0.8)
			elif bank < 9.0:
				overlay = 2
				blend = 1.0 - smoothstep(5.0, 9.0, bank)
			elif slope > 0.85:
				overlay = 3
				blend = smoothstep(0.85, 1.3, slope)
			elif p.y < _river_center_z(p.x) - 30.0:
				overlay = 4
				blend = clampf(0.35 + n, 0.15, 0.8)
			var packed := (base << 27) | (overlay << 22) | (int(blend * 255.0) << 14)
			bits.encode_u32((iz * 1024 + ix) * 4, packed)
			var tint := Color(0.88, 0.92, 0.82).lerp(Color(0.97, 0.95, 0.88), clampf(n + 0.5, 0, 1))
			var wetness := lerpf(0.42, 0.58, smoothstep(-0.5, 2.5, bank))
			colors.set_pixel(ix, iz, Color(tint.r, tint.g, tint.b, wetness))
	var control := Image.create_from_data(1024, 1024, false, Image.FORMAT_RF, bits)
	t.data.import_images([height, control, colors], Vector3(-512, 0, -512), 0.0, 1.0)
	print("[valley] generated height, five surface zones and shoreline wetness")


func _build_environment() -> void:
	super._build_environment()
	var env: Environment = get_node("WorldEnvironment").environment
	env.tonemap_exposure = 1.0
	env.ambient_light_energy = 0.40
	env.adjustment_saturation = 0.94
	env.adjustment_contrast = 1.02
	env.fog_density = 0.00025
	env.fog_height_density = 0.0
	env.ssao_intensity = 1.0
	env.ssil_enabled = false
	env.ssr_enabled = false


func _build_light() -> void:
	super._build_light()
	var sun: DirectionalLight3D = get_node("Sun")
	sun.rotation_degrees = Vector3(-42, 30, 0)
	sun.light_energy = 0.8
	sun.directional_shadow_max_distance = 160.0


func _build_instanced_nature() -> void:
	# Grounded model batches: fixed local layout, render-distance culling per batch.
	var paths := ["fern_02/fern_02_2k", "shrub_02/shrub_02_2k", "grass_medium_01/grass_medium_01_2k",
		"searsia_lucida/searsia_lucida_2k", "tree_stump_01/tree_stump_01_2k"]
	for i in 1800:
		var p := Vector2(rng.randf_range(-265, 80), rng.randf_range(-110, 115))
		if bank_distance(p) < 6.0 or p.distance_to(ARRIVAL) < 3.5:
			continue
		var kind := i % paths.size()
		var size_m := rng.randf_range(0.35, 0.8)
		if kind == 1 or kind == 3:
			size_m = rng.randf_range(0.7, 1.6)
		_batch_model("res://assets/models/polyhaven/" + paths[kind] + ".gltf", p, size_m, false)
	# Frame the arrival with shrubs, leaving the central walking route open.
	for p in [ARRIVAL + Vector2(-2, 6), ARRIVAL + Vector2(-6, 8), ARRIVAL + Vector2(0, -7), ARRIVAL + Vector2(-16, 10)]:
		_batch_model("res://assets/models/polyhaven/searsia_lucida/searsia_lucida_2k.gltf", p, 1.5, false)
	for i in 220:
		var p := ARRIVAL + Vector2(rng.randf_range(-55, 10), rng.randf_range(-10, 30))
		if bank_distance(p) > 7 and p.distance_to(ARRIVAL) > 3:
			_batch_model("res://assets/models/polyhaven/fern_02/fern_02_2k.gltf", p, rng.randf_range(0.3, 0.7), false)
	_flush_batches()


func _batch_model(path: String, p: Vector2, extent: float, rock: bool) -> void:
	var info := _tree_info(path)
	var size: Vector3 = info["size"]
	var scale_factor := extent / maxf(0.01, maxf(size.x, size.z) if rock else size.y)
	var at := Vector3(p.x, terrain.data.get_height(Vector3(p.x, 0, p.y)), p.y)
	at.y -= info["base"] * scale_factor
	if rock:
		at.y -= size.y * scale_factor * 0.18
	var xf := Transform3D(Basis(Vector3.UP, rng.randf_range(0, TAU)).scaled(Vector3.ONE * scale_factor), at)
	# Spatial grouping prevents one huge MultiMesh AABB from keeping every detail visible.
	var key := path + "@%d,%d" % [floori(p.x / 64.0), floori(p.y / 64.0)]
	if not _detail_meshes.has(key):
		_detail_meshes[key] = {"path": path, "transforms": [], "rock": rock}
	_detail_meshes[key]["transforms"].append(xf)


func _flush_batches() -> void:
	for key in _detail_meshes:
		var batch: Dictionary = _detail_meshes[key]
		var path: String = batch["path"]
		if not _batch_geometry.has(path):
			var root_model: Node3D = load(path).instantiate()
			add_child(root_model)
			var geometry: Array = []
			for child in root_model.find_children("", "MeshInstance3D", true, false):
				var mi := child as MeshInstance3D
				var mesh: Mesh = mi.mesh.duplicate()
				for surface in mesh.get_surface_count():
					var source: StandardMaterial3D = mi.get_active_material(surface)
					var material: StandardMaterial3D = source.duplicate()
					# Some pre-existing imported scenes lost their texture bindings.
					if material.albedo_texture == null:
						var asset_name := path.get_base_dir().get_file()
						material.albedo_texture = load(path.get_base_dir().path_join("textures/" + asset_name + "_diff_2k.jpg"))
					material.metallic_specular = 0.15
					material.roughness = 0.9
					mesh.surface_set_material(surface, material)
				geometry.append({"mesh": mesh, "transform": mi.global_transform})
			_batch_geometry[path] = geometry
			root_model.free()
		for part in _batch_geometry[path]:
			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.mesh = part["mesh"]
			mm.instance_count = batch["transforms"].size()
			for i in mm.instance_count:
				mm.set_instance_transform(i, batch["transforms"][i] * part["transform"])
			var node := MultiMeshInstance3D.new()
			node.multimesh = mm
			node.visibility_range_end = 420.0 if batch["rock"] else 125.0
			node.visibility_range_end_margin = 20.0
			add_child(node)
	_detail_meshes.clear()


func _build_trees() -> void:
	for i in 600:
		var p := Vector2(rng.randf_range(-310, 95), rng.randf_range(-135, 135))
		var side := p.y - _river_center_z(p.x)
		if bank_distance(p) < 14 or p.distance_to(ARRIVAL) < 8:
			continue
		if p.x > -230 and p.x < ARRIVAL.x and absf(p.y - lerpf(0.0, ARRIVAL.y, (p.x + 230.0) / (ARRIVAL.x + 230.0))) < 7:
			continue
		# Denser right forest, exposed left rock face, sparse valley saplings.
		if side > 0 and side < 55 and i % 4 != 0:
			continue
		if lake_radius(p) < 1.12:
			continue
		var info := _tree_info(FIR)
		var desired_height := rng.randf_range(8.0, 15.0) if absf(side) > 38 else rng.randf_range(3.0, 6.0)
		_place_valley_tree(p, desired_height / info["size"].y)
	for p in [ARRIVAL + Vector2(5, 12), ARRIVAL + Vector2(-8, 17), ARRIVAL + Vector2(4, -13)]:
		_place_valley_tree(p, 12.0 / _tree_info(FIR)["size"].y)
	# A continuous right-hand canopy gives the valley a forest edge. Existing
	# broadleaf crowns supply the volume missing from the small fir source.
	for ix in 18:
		for iz in 6:
			if rng.randf() < 0.2:
				continue
			var p := Vector2(-230 + ix * 17 + rng.randf_range(-10, 10), -28 - iz * 11 + rng.randf_range(-8, 8))
			if lake_radius(p) < 1.15 or bank_distance(p) < 15:
				continue
			_place_valley_tree(p, rng.randf_range(9, 18) / _tree_info(CANOPY_TREE)["size"].y, CANOPY_TREE)
	for p in [ARRIVAL + Vector2(0, 8), ARRIVAL + Vector2(-9, 12), ARRIVAL + Vector2(3, -10)]:
		_place_valley_tree(p, 13.0 / _tree_info(CANOPY_TREE)["size"].y, CANOPY_TREE)


func _place_valley_tree(p: Vector2, scale_factor: float, path: String = FIR) -> void:
	var body := StaticBody3D.new()
	body.name = "ValleyTree"
	body.set_meta("impact_surface", "wood")
	add_child(body)
	var model: Node3D = load(path).instantiate()
	body.add_child(model)
	# The download contains three side-by-side variants, not one tree.
	if path == FIR:
		var selected: Node3D = model.get_child(rng.randi_range(0, model.get_child_count() - 1))
		for child in model.get_children():
			if child != selected:
				child.free()
		selected.position = Vector3.ZERO
	# The imported GLTF currently has unbound textures. Restore them on local
	# surface overrides; leave the source asset and other scenes untouched.
	for child in model.find_children("", "MeshInstance3D", true, false):
		if path != FIR:
			continue
		for surface in child.mesh.get_surface_count():
			var source: Material = child.get_active_material(surface)
			var material_name := source.resource_name
			if not _fir_materials.has(material_name):
				var material := StandardMaterial3D.new()
				var prefix := "res://assets/models/polyhaven/fir_sapling/" + material_name
				material.albedo_texture = load("res://assets/textures/scenic_valley/fir_twigs.jpg" if "twigs" in material_name else prefix + "_diff_2k.jpg")
				material.albedo_color = Color(0.65, 0.8, 0.52) if "twigs" in material_name else Color.WHITE
				material.normal_enabled = true
				material.normal_texture = load(prefix + "_nor_gl_2k.jpg")
				material.normal_scale = 0.65
				material.roughness = 0.9
				material.metallic_specular = 0.15
				material.cull_mode = BaseMaterial3D.CULL_DISABLED
				_fir_materials[material_name] = material
			child.set_surface_override_material(surface, _fir_materials[material_name])
	model.scale = Vector3.ONE * scale_factor
	model.rotation.y = rng.randf_range(0, TAU)
	var info := _tree_info(path)
	var h := terrain.data.get_height(Vector3(p.x, 0, p.y))
	body.position = Vector3(p.x, h, p.y)
	model.position.y = -info["base"] * scale_factor
	var shape := CylinderShape3D.new()
	shape.radius = clampf(scale_factor * 0.1, 0.12, 0.4)
	shape.height = info["size"].y * scale_factor * 0.65
	var collision := CollisionShape3D.new()
	collision.shape = shape
	collision.position.y = shape.height * 0.5
	body.add_child(collision)
	for child in model.find_children("", "GeometryInstance3D", true, false):
		child.visibility_range_end = 450.0


func _build_landmark_rocks() -> void:
	# Nested rock outcrops form the left shoulder rather than isolated pebbles.
	for i in 38:
		var p := Vector2(rng.randf_range(-210, 0), rng.randf_range(42, 77))
		_batch_model(BOULDER if i % 2 == 0 else ROCK, p, rng.randf_range(5.0, 12.0), true)
	for i in 12:
		var p := Vector2(-40 - i * 11 + rng.randf_range(-5, 5), 35 + rng.randf_range(-4, 13))
		_batch_model(ROCK, p, rng.randf_range(11.0, 18.0), true)
	for i in 120:
		var x := rng.randf_range(-285, 45)
		var side := -1.0 if i % 2 == 0 else 1.0
		var p := Vector2(x, _river_center_z(x) + side * (stream_half_width(x) + rng.randf_range(-0.5, 5.0)))
		_batch_model(ROCK, p, rng.randf_range(0.4, 2.6), true)
	_flush_batches()


func _build_river() -> void:
	var river := MeshInstance3D.new()
	river.name = "River"
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	const CROSS := 8
	const START := -275
	const END := 125
	for x in range(START, END + 1, 2):
		var width := stream_half_width(x)
		for j in CROSS + 1:
			var lateral := (float(j) / CROSS * 2.0 - 1.0) * width
			var p := Vector3(x, water_height(x), _river_center_z(x) + lateral)
			st.set_normal(Vector3.UP)
			st.set_color(Color(1, 1, 1, smoothstep(0, 0.55, width - absf(lateral))))
			st.add_vertex(p)
	var rows := (END - START) / 2 + 1
	for i in rows - 1:
		for j in CROSS:
			var a := i * (CROSS + 1) + j
			var b := a + CROSS + 1
			for index in [a, b, a + 1, a + 1, b, b + 1]:
				st.add_index(index)
	var material := ShaderMaterial.new()
	material.shader = load("res://assets/shaders/valley_water.gdshader")
	river.mesh = st.commit()
	river.material_override = material
	add_child(river)
	var lake := MeshInstance3D.new()
	lake.name = "Lake"
	var lake_st := SurfaceTool.new()
	lake_st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in 96:
		for p in [Vector3(-385, 0, 0), Vector3(-385 + cos(TAU * i / 96) * 110, 0, sin(TAU * i / 96) * 150),
			Vector3(-385 + cos(TAU * (i + 1) / 96) * 110, 0, sin(TAU * (i + 1) / 96) * 150)]:
			lake_st.set_normal(Vector3.UP)
			lake_st.set_color(Color.WHITE)
			lake_st.add_vertex(p)
	lake.mesh = lake_st.commit()
	lake.material_override = material
	add_child(lake)


func _build_particle_grass() -> void:
	var pt: Node3D = load("res://addons/terrain_3d/extras/particle_example/Terrain3DParticles.tscn").instantiate()
	pt.name = "ParticleGrass"
	# Configure before binding terrain so the large default grid is never allocated.
	pt.instance_spacing = 0.1875
	pt.cell_width = 16.0
	pt.grid_width = 5
	var pm: ShaderMaterial = pt.process_material.duplicate()
	pm.shader = load("res://assets/shaders/valley_grass_process.gdshader")
	pm.set_shader_parameter("min_scale", Vector3(0.035, 0.18, 0.035))
	pm.set_shader_parameter("max_scale", Vector3(0.055, 0.48, 0.055))
	pm.set_shader_parameter("clod_scale_boost", 0.12)
	pm.set_shader_parameter("patch_min_threshold", 0.12)
	pm.set_shader_parameter("patch_max_threshold", 0.5)
	pm.set_shader_parameter("wind_strength", 0.28)
	pm.set_shader_parameter("surface_slope_min", 0.7)
	pm.set_shader_parameter("main_noise_scale", 0.025)
	pm.set_shader_parameter("random_spacing", 0.85)
	pt.process_material = pm
	var gm := ShaderMaterial.new()
	gm.shader = load("res://assets/shaders/valley_grass.gdshader")
	pt.mesh_material_override = gm
	pt.terrain = terrain
	add_child(pt)
	print("[valley] grass instances=", pt.particle_count)


func _build_player() -> void:
	super._build_player()
	_player.position = Vector3(ARRIVAL.x, terrain.data.get_height(Vector3(ARRIVAL.x, 0, ARRIVAL.y)) + 1.1, ARRIVAL.y)
	_player.rotation.y = PI * 0.5 - 0.12
	var cam: Camera3D = _player.get_node("Camera3D")
	cam.rotation.x = -0.08
	cam.fov = 70.0
	cam.far = 2500.0


func _build_return_portal() -> void:
	super._build_return_portal()
	var p := Vector3(ARRIVAL.x + 8, 0, ARRIVAL.y + 3)
	p.y = terrain.data.get_height(p) + 1.4
	get_node("ReturnPortal").position = p


func _build_mouse_king() -> void:
	super._build_mouse_king()
	var p := Vector3(ARRIVAL.x + 5, 0, ARRIVAL.y - 5)
	p.y = terrain.data.get_height(p) + 0.9
	get_node("MouseKingNpc").position = p


func _build_distant_ridge() -> void:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for ix in 49:
		for iz in 81:
			var x := -1100.0 + ix * 12.5
			var z := -800.0 + iz * 20.0
			var edge := sin(PI * ix / 48.0)
			var h := maxf(0, edge) * (65 + 38 * sin(z / 123.0) + 18 * sin(z / 44.0))
			h += maxf(0, edge) * _land_noise.get_noise_2d(x, z) * 35
			st.set_color(Color(0.31, 0.37, 0.39).lerp(Color(0.58, 0.59, 0.56), clampf(h / 110, 0, 1)))
			st.add_vertex(Vector3(x, h - 5, z))
	for ix in 48:
		for iz in 80:
			var a := ix * 81 + iz
			for index in [a, a + 81, a + 1, a + 1, a + 81, a + 82]:
				st.add_index(index)
	st.generate_normals()
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.roughness = 1.0
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	var mountain := MeshInstance3D.new()
	mountain.name = "DistantRidge"
	mountain.mesh = st.commit()
	mountain.material_override = mat
	add_child(mountain)
