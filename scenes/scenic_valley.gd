extends "res://scenes/demo_terrain.gd"

## Authored scenic corridor; inherits the existing player/HUD/portal contracts.
## Bump CACHE_REVISION when changing the height/control/color recipe. -- --rebuild-valley
## regenerates only this scene's cache, never the original demo regions.
const CACHE_REVISION := "valley_03"
const VALLEY_DATA := "user://terrain_cache/" + CACHE_REVISION
const ARRIVAL := Vector2(-90.0, 32.0)
const FIR := "res://assets/models/polyhaven/fir_sapling/fir_sapling_2k.gltf"
const CANOPY_TREE := "res://assets/models/polyhaven/island_tree_02/island_tree_02_1k.gltf"
const CONIFER := "res://scenes/imported_pine.tscn"
const YOUNG_PINE := "res://assets/models/polyhaven/pine_sapling_small/pine_sapling_small_1k.gltf"
const LEAF_TREE := "res://assets/models/polyhaven/tree_small_02/tree_small_02_1k.gltf"
const BOULDER := "res://assets/models/polyhaven/boulder_01/boulder_01_2k.gltf"
const ROCK := "res://assets/models/polyhaven/rock_09/rock_09_2k.gltf"
const ScenicCollision := preload("res://scenes/scenic_collision.gd")
var _land_noise := FastNoiseLite.new()
var _patch_noise := FastNoiseLite.new()
var _detail_meshes: Dictionary = {}
var _fir_materials: Dictionary = {}
var _batch_geometry: Dictionary = {}
var _rock_collision_geometry: Dictionary = {}
var _trunk_collision_geometry: Dictionary = {}
var _root_geometry: Dictionary = {}
var _nature_variants: Dictionary = {}
var _occupied: Array[AABB] = []
var _plant_roots: Array[Rect2] = []
var grounding_records: Array[Dictionary] = []
var placement_rejected := 0
var grass_exclusion: Image


func _ready() -> void:
	_land_noise.seed = 9305
	_land_noise.noise_type = FastNoiseLite.TYPE_PERLIN
	_land_noise.frequency = 0.018
	_land_noise.fractal_octaves = 3
	_patch_noise.seed = 28061
	_patch_noise.frequency = 0.17
	_patch_noise.fractal_octaves = 3
	super._ready()
	_build_distant_ridge()
	if _player!=null:
		var ground_editor:=preload("res://scripts/voxel_lab/wilderness_editor.gd").new()
		ground_editor.name="WildernessEditor"
		add_child(ground_editor)
		var building:=preload("res://scripts/building/build_system.gd").new()
		building.player_override=_player
		building.allow_terrain_anchors=true
		building.terrain_source=terrain
		# Terrain3D covers roughly -512..512 m. Keep a small safety border and
		# express the range in the shared half-metre building grid.
		building.minimum_cell=Vector3i(-992,-128,-992)
		building.maximum_cell=Vector3i(992,384,992)
		building.sidecar_suffix=".wilderness-building"
		add_child(building)


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


func shore_material_distance(p: Vector2) -> float:
	# Vegetation and material edges share this broken band, while the physical
	# water boundary remains the same continuous, walkable shoreline.
	var bank := bank_distance(p)
	return bank + (_patch_noise.get_noise_2d(p.x, p.y) * 3.8 + _land_noise.get_noise_2d(p.x * 2, p.y * 2) * 4.5) * smoothstep(0.0, 2.5, bank)


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
	var textures := ["grass004", "ground092c", "gravel041", "rock063", "ground020"]
	for i in textures.size():
		var ta := Terrain3DTextureAsset.new()
		ta.name = textures[i]
		ta.albedo_texture = load(PREP_TEX % [textures[i], "alb_ht"])
		if i==0: ta.albedo_texture=load("res://assets/textures/wilderness_generated/turf_alb_ht_v1.png")
		elif i==4: ta.albedo_texture=load("res://assets/textures/wilderness_generated/loam_alb_ht_v1.png")
		ta.normal_texture = load(PREP_TEX % [textures[i], "nrm_rgh"])
		ta.normal_depth = 0.4
		ta.roughness = 0.30
		ta.ao_strength = 1.0
		ta.uv_scale = 0.5 if i == 0 else (0.32 if i != 3 else 0.12)
		ta.detiling_rotation = 0.15
		preload("res://scripts/wilderness_materials.gd").configure_asset(ta,i)
		t.assets.set_texture(i, ta)
	preload("res://scripts/wilderness_materials.gd").configure_terrain(t.material)
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
			var bank := shore_material_distance(p)
			var n := _land_noise.get_noise_2d(p.x, p.y)
			var slope := Vector2(valley_height(p + Vector2.RIGHT) - h,
				valley_height(p + Vector2.DOWN) - h).length()
			var base := 0
			var overlay := 4
			var blend := clampf((n + 0.15) * 0.35, 0.0, 0.3)
			if bank < 1.5:
				base = 1
				overlay = 2
				blend = clampf(0.2 + _patch_noise.get_noise_2d(p.x, p.y) * 0.65, 0.05, 0.55)
			elif bank < 6.5:
				overlay = 2
				blend = 1.0 - smoothstep(1.5, 6.5, bank)
			elif slope > 0.85:
				overlay = 3
				blend = smoothstep(0.85, 1.3, slope)
			elif p.y < _river_center_z(p.x) - 30.0:
				overlay = 4
				blend = clampf(0.35 + n, 0.15, 0.8)
			var packed := (base << 27) | (overlay << 22) | (int(blend * 255.0) << 14)
			bits.encode_u32((iz * 1024 + ix) * 4, packed)
			var tint := Color(0.62, 0.69, 0.55).lerp(Color(0.88, 0.91, 0.79), clampf(n + 0.5, 0, 1))
			if bank < 7:
				tint = tint.lerp(Color(0.46, 0.44, 0.39), 1.0 - smoothstep(-0.3, 6.5, bank))
			var wetness := lerpf(0.3, 0.56, smoothstep(-0.5, 3.0, bank))
			colors.set_pixel(ix, iz, Color(tint.r, tint.g, tint.b, wetness))
	var control := Image.create_from_data(1024, 1024, false, Image.FORMAT_RF, bits)
	t.data.import_images([height, control, colors], Vector3(-512, 0, -512), 0.0, 1.0)
	print("[valley] generated height, five surface zones and shoreline wetness")


func _build_instanced_nature() -> void:
	# The inherited build order calls this before rocks and trees. Populate after
	# those solid obstacles exist so ground cover can avoid their footprints.
	pass


func _populate_ground_cover() -> void:
	# Grounded model batches: fixed local layout, render-distance culling per batch.
	var paths := ["fern_02/fern_02_2k", "shrub_02/shrub_02_2k", "grass_medium_01/grass_medium_01_2k",
		"searsia_lucida/searsia_lucida_2k", "tree_stump_01/tree_stump_01_2k"]
	var candidates: Array[Dictionary] = []
	for i in 2600:
		var p := Vector2(rng.randf_range(-265, 80), rng.randf_range(-110, 115))
		if shore_material_distance(p) < 4.0 or bank_distance(p) < 2.5 or p.distance_to(ARRIVAL) < 3.5:
			continue
		if _patch_noise.get_noise_2d(p.x * 0.35, p.y * 0.35) < -0.18 and i % 3 != 0:
			continue
		var kind := 4 if i % 21 == 0 else i % 4
		var size_m := rng.randf_range(0.2, 0.55)
		if kind == 1 or kind == 3:
			size_m = rng.randf_range(0.5, 1.25)
		candidates.append({"kind": kind, "p": p, "size": size_m})
	# Solid stumps precede foliage, which must not later acquire a stump inside it.
	for kind in [4, 0, 1, 2, 3]:
		for candidate in candidates:
			if candidate["kind"] == kind:
				_batch_model("res://assets/models/polyhaven/" + paths[kind] + ".gltf", candidate["p"], candidate["size"], false)
	# Frame the arrival with shrubs, leaving the central walking route open.
	for p in [ARRIVAL + Vector2(-2, 6), ARRIVAL + Vector2(-6, 8), ARRIVAL + Vector2(0, -7), ARRIVAL + Vector2(-16, 10)]:
		_batch_model("res://assets/models/polyhaven/searsia_lucida/searsia_lucida_2k.gltf", p, 1.5, false)
	for i in 220:
		var p := ARRIVAL + Vector2(rng.randf_range(-55, 10), rng.randf_range(-10, 30))
		if bank_distance(p) > 7 and p.distance_to(ARRIVAL) > 3:
			_batch_model("res://assets/models/polyhaven/fern_02/fern_02_2k.gltf", p, rng.randf_range(0.3, 0.7), false)
	_flush_batches()
	_update_grass_exclusion()
	print("[valley-grounding] accepted=", grounding_records.size(), " rejected=", placement_rejected)


func _blocked(box: AABB) -> bool:
	var footprint := Rect2(Vector2(box.position.x, box.position.z), Vector2(box.size.x, box.size.z))
	for obstacle in _occupied:
		var other := Rect2(Vector2(obstacle.position.x, obstacle.position.z), Vector2(obstacle.size.x, obstacle.size.z))
		if footprint.intersects(other):
			return true
	for reserve in [ARRIVAL, ARRIVAL + Vector2(8, 3), ARRIVAL + Vector2(5, -5)]:
		if footprint.grow(2.0).has_point(reserve):
			return true
	return false


func _prepare_variants(path: String) -> Array:
	if _nature_variants.has(path):
		return _nature_variants[path]
	var probe: Node3D = load(path).instantiate()
	var count := probe.get_child_count()
	probe.free()
	var variants: Array = []
	for variant in count:
		var model: Node3D = load(path).instantiate()
		add_child(model)
		var selected: Node3D = model.get_child(variant)
		for child in model.get_children():
			if child != selected:
				child.free()
		# Keep authored orientation, discard catalog/display translations.
		selected.position = Vector3.ZERO
		var key := path + "#" + str(variant)
		_root_geometry[key] = ScenicCollision.root_geometry(model)
		_cache_batch_geometry(key, path, model)
		variants.append(key)
		model.free()
	_nature_variants[path] = variants
	return variants


func _batch_model(path: String, p: Vector2, extent: float, rock: bool, iron: bool=false, copper: bool=false, precious: String="") -> void:
	var ore_kind := "iron" if iron else ("copper" if copper else precious)
	var geometry_key := path
	if iron: geometry_key += ":iron"
	elif copper: geometry_key += ":copper"
	elif not precious.is_empty(): geometry_key += ":"+precious
	if not rock:
		var variants := _prepare_variants(path)
		geometry_key = variants[rng.randi_range(0, variants.size() - 1)]
	var size: Vector3 = _tree_info(path)["size"] if rock else _root_geometry[geometry_key]["bounds"].size
	var scale_factor := extent / maxf(0.01, maxf(size.x, size.z) if rock else size.y)
	var at := Vector3(p.x, terrain.data.get_height(Vector3(p.x, 0, p.y)), p.y)
	var yaw := rng.randf_range(0, TAU)
	var xf := Transform3D(Basis(Vector3.UP, yaw).scaled(Vector3.ONE * scale_factor), at)
	if rock:
		if not _rock_collision_geometry.has(path):
			var probe: Node3D = load(path).instantiate()
			add_child(probe)
			_rock_collision_geometry[path] = ScenicCollision.rock_geometry(probe)
			probe.free()
		var geometry: Dictionary = _rock_collision_geometry[path]
		xf = ScenicCollision.fit_rock(terrain.data, p, scale_factor, yaw, geometry)
		var rock_box: AABB = xf * geometry["bounds"]
		if not xf.is_finite() or rock_box.end.y - terrain.data.get_height(rock_box.get_center()) < rock_box.size.y * 0.25:
			placement_rejected += 1
			return
		# Preserve nested outcrops, but keep arrival/NPC/portal clear.
		for reserve in [ARRIVAL, ARRIVAL + Vector2(8, 3), ARRIVAL + Vector2(5, -5)]:
			if Rect2(Vector2(rock_box.position.x, rock_box.position.z), Vector2(rock_box.size.x, rock_box.size.z)).grow(2).has_point(reserve):
				placement_rejected += 1
				return
		# Keep the old source/ground-fit identity so existing mined deposits stay gone.
		var legacy_position := global_transform * xf.origin
		var legacy_id := "%s:%.3f:%.3f:%.3f" % [path, legacy_position.x, legacy_position.y, legacy_position.z]
		if not ore_kind.is_empty():
			var variants := ["rounded", "slab", "leaning", "ridge", "wedge", "saddle", "tall", "long"]
			# Position hash is stable and consumes no landscape RNG values.
			var variant_index := ("%.3f,%.3f" % [p.x, p.y]).hash() % variants.size()
			path = "res://assets/models/ore_variants/%s/model.scn" % variants[variant_index]
			geometry_key = path + ":" + ore_kind
			if not _rock_collision_geometry.has(path):
				var variant_model: Node3D = load(path).instantiate()
				add_child(variant_model)
				var variant_geometry: Dictionary = ScenicCollision.rock_geometry(variant_model)
				# Sculpted upper overhangs must not pull the entire deposit underground.
				var base_support := PackedVector3Array()
				var variant_bounds: AABB = variant_geometry.bounds
				for point in variant_geometry.support:
					if point.y <= variant_bounds.position.y + variant_bounds.size.y * 0.12:
						base_support.append(point)
				variant_geometry.support = base_support
				_rock_collision_geometry[path] = variant_geometry
				variant_model.free()
			geometry = _rock_collision_geometry[path]
			var variant_size: Vector3 = geometry.bounds.size
			scale_factor = extent / maxf(variant_size.x, variant_size.z)
			xf = ScenicCollision.fit_rock(terrain.data, p, scale_factor, yaw, geometry)
			if not xf.is_finite():
				placement_rejected += 1
				return
			rock_box = xf * geometry.bounds
		var rock_body:=ScenicCollision.add_rock(self, xf, geometry)
		if not ore_kind.is_empty():
			rock_body.set_meta("harvest_identity", legacy_id)
			rock_body.set_meta("rock_fragments", load(path.get_base_dir()+"/fragments.res"))
		rock_body.set_meta("terrain_support_root",xf.origin)
		var harvest_key:=geometry_key+"@%d,%d" % [floori(p.x/64.0),floori(p.y/64.0)]
		rock_body.set_meta("rock_source",path)
		rock_body.set_meta("harvest_item","iron_ore" if iron else ("copper_ore" if copper else "stone"))
		if not precious.is_empty(): rock_body.set_meta("harvest_item",precious+"_ore")
		rock_body.set_meta("rock_transform",xf)
		rock_body.set_meta("rock_extent",extent)
		rock_body.set_meta("harvest_batch_key",harvest_key)
		rock_body.set_meta("harvest_index",_detail_meshes[harvest_key].transforms.size() if _detail_meshes.has(harvest_key) else 0)
		_occupied.append(rock_box.grow(0.2))
		grounding_records.append({"kind": "rock", "transform": xf, "geometry": geometry})
	else:
		var geometry: Dictionary = _root_geometry[geometry_key]
		var fit := ScenicCollision.fit_root(terrain.data, p, scale_factor, yaw, geometry)
		if fit.is_empty():
			placement_rejected += 1
			return
		xf = fit["transform"]
		var box: AABB = xf * geometry["bounds"]
		if _blocked(box.grow(0.12)):
			placement_rejected += 1
			return
		var root_box: AABB = xf * ScenicCollision.bounds(geometry["support"])
		var root_area := Rect2(Vector2(root_box.position.x, root_box.position.z), Vector2(root_box.size.x, root_box.size.z)).grow(0.08)
		for other in _plant_roots:
			if root_area.intersects(other):
				placement_rejected += 1
				return
		_plant_roots.append(root_area)
		grounding_records.append({"kind": "stump" if "tree_stump" in path else "plant", "transform": xf, "geometry": geometry, "bounds": box})
		if "tree_stump" in path:
			var stump := StaticBody3D.new()
			add_child(stump)
			stump.set_meta("impact_surface", "wood")
			stump.set_meta("terrain_support_root",xf.origin)
			var collision := CollisionShape3D.new()
			var shape := BoxShape3D.new()
			shape.size = box.size
			collision.shape = shape
			stump.position = box.get_center()
			stump.add_child(collision)
			_occupied.append(box.grow(0.1))
	# Spatial grouping prevents one huge MultiMesh AABB from keeping every detail visible.
	var key := geometry_key + "@%d,%d" % [floori(p.x / 64.0), floori(p.y / 64.0)]
	if not _detail_meshes.has(key):
		_detail_meshes[key] = {"path": path, "geometry_key": geometry_key, "transforms": [], "rock": rock}
	_detail_meshes[key]["transforms"].append(xf)


func _cache_batch_geometry(key: String, path: String, root_model: Node3D) -> void:
	var geometry: Array = []
	for child in root_model.find_children("", "MeshInstance3D", true, false):
		var mi := child as MeshInstance3D
		var mesh: Mesh = mi.mesh.duplicate()
		for surface in mesh.get_surface_count():
			var source: StandardMaterial3D = mi.get_active_material(surface)
			var material: StandardMaterial3D = source.duplicate()
			if material.albedo_texture == null:
				var asset_name := path.get_base_dir().get_file()
				material.albedo_texture = load(path.get_base_dir().path_join("textures/" + asset_name + "_diff_2k.jpg"))
			material.metallic_specular = 0.15
			material.roughness = 0.9
			mesh.surface_set_material(surface, material)
		geometry.append({"mesh": mesh, "transform": root_model.global_transform.affine_inverse() * mi.global_transform})
	_batch_geometry[key] = geometry
	if key.ends_with(":iron") or key.ends_with(":copper") or key.ends_with(":silver") or key.ends_with(":gold"):
		for part in geometry:
			var iron_material:=preload("res://scripts/tools/iron_vein_material.gd").create(part.mesh)
			if key.ends_with(":copper"): iron_material=preload("res://scripts/tools/copper_vein_material.gd").create(part.mesh)
			if key.ends_with(":silver") or key.ends_with(":gold"):
				iron_material=preload("res://scripts/tools/precious_vein_material.gd").create(key.get_slice(":",2),part.mesh)
			for s in part.mesh.get_surface_count(): part.mesh.surface_set_material(s,iron_material)


func _flush_batches() -> void:
	for key in _detail_meshes:
		var batch: Dictionary = _detail_meshes[key]
		var path: String = batch["path"]
		var geometry_key: String = batch["geometry_key"]
		if not _batch_geometry.has(geometry_key):
			var root_model: Node3D = load(path).instantiate()
			add_child(root_model)
			_cache_batch_geometry(geometry_key, path, root_model)
			root_model.free()
		for part in _batch_geometry[geometry_key]:
			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.mesh = part["mesh"]
			mm.instance_count = batch["transforms"].size()
			for i in mm.instance_count:
				mm.set_instance_transform(i, batch["transforms"][i] * part["transform"])
			var node := MultiMeshInstance3D.new()
			node.multimesh = mm
			node.set_meta("ground_roots",batch["transforms"].duplicate())
			node.set_meta("harvest_batch_key",key)
			node.visibility_range_end = 420.0 if batch["rock"] else 65.0
			node.lod_bias = 0.5
			node.visibility_range_end_margin = 20.0
			add_child(node)
	_detail_meshes.clear()


func _build_trees() -> void:
	# Reserve near silhouettes before filling the forest, with a view between them.
	for p in [ARRIVAL + Vector2(1, 7), ARRIVAL + Vector2(-7, 10), ARRIVAL + Vector2(2, -8), ARRIVAL + Vector2(-15, -12)]:
		_place_valley_tree(p, rng.randf_range(1.0, 1.35), CONIFER)
	for i in 950:
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
		var density := clampf(0.65 + _land_noise.get_noise_2d(p.x * 2.0, p.y * 2.0) * 1.1, 0.2, 0.95)
		if rng.randf() > density:
			continue
		var path := CONIFER if i % 5 != 0 else YOUNG_PINE
		var info := _tree_info(path)
		var desired_height := rng.randf_range(9.0, 17.0) if path == CONIFER else rng.randf_range(3, 6)
		_place_valley_tree(p, desired_height / info["size"].y, path)
	for p in [ARRIVAL + Vector2(5, 12), ARRIVAL + Vector2(-8, 17), ARRIVAL + Vector2(4, -13)]:
		_place_valley_tree(p, 12.0 / _tree_info(CONIFER)["size"].y, CONIFER)
	# A continuous right-hand canopy gives the valley a forest edge. Existing
	# broadleaf crowns supply the volume missing from the small fir source.
	for ix in 18:
		for iz in 6:
			if rng.randf() < 0.2:
				continue
			var p := Vector2(-230 + ix * 17 + rng.randf_range(-10, 10), -28 - iz * 11 + rng.randf_range(-8, 8))
			if lake_radius(p) < 1.15 or bank_distance(p) < 15:
				continue
			var path := CONIFER if (ix + iz) % 3 != 0 else LEAF_TREE
			_place_valley_tree(p, rng.randf_range(10, 18) / _tree_info(path)["size"].y, path)
	for p in [ARRIVAL + Vector2(0, 8), ARRIVAL + Vector2(-9, 12), ARRIVAL + Vector2(3, -10)]:
		_place_valley_tree(p, 13.0 / _tree_info(CANOPY_TREE)["size"].y, CANOPY_TREE)
	_populate_ground_cover()


func _place_valley_tree(p: Vector2, scale_factor: float, path: String = FIR) -> void:
	var body := StaticBody3D.new()
	body.name = "ValleyTree"
	body.set_meta("impact_surface", "wood")
	body.set_meta("landscape_asset", path)
	add_child(body)
	var model: Node3D = load(path).instantiate()
	if path == CONIFER:
		model.variant = rng.randi_range(0, 2)
	body.add_child(model)
	var variant_key := path + (":" + str(model.variant) if path == CONIFER else "")
	# The download contains three side-by-side variants, not one tree.
	if path == FIR or path == YOUNG_PINE:
		var selected: Node3D = model.get_child(rng.randi_range(0, model.get_child_count() - 1))
		variant_key += ":" + str(selected.name)
		for child in model.get_children():
			if child != selected:
				child.free()
		selected.position = Vector3.ZERO
	# Capture unscaled wood geometry before assigning scene-local materials.
	if not _trunk_collision_geometry.has(variant_key):
		_trunk_collision_geometry[variant_key] = ScenicCollision.trunk_hulls(model)
		_root_geometry[variant_key] = ScenicCollision.root_geometry(model, true)
		if path == CONIFER:
			# Raise fitting samples to the top of the root flare: the solver then
			# places the entire flare beneath the lowest terrain sample.
			var geometry: Dictionary = _root_geometry[variant_key]
			var support: PackedVector3Array = geometry["support"]
			for index in support.size():
				support[index].y += model.burial_depth
			geometry["support"] = support
	var root_geometry: Dictionary = _root_geometry[variant_key]
	var yaw := rng.randf_range(0, TAU)
	var fit: Dictionary = {}
	var xf := Transform3D.IDENTITY
	var trunk_box := AABB()
	# A bounded local search preserves forest density without accepting bad roots.
	var original := p
	for attempt in 9:
		p = original if attempt == 0 else original + Vector2.from_angle(attempt * 2.399963) * (1.5 + attempt * 0.45)
		if bank_distance(p) < 14 or lake_radius(p) < 1.12:
			continue
		fit = ScenicCollision.fit_root(terrain.data, p, scale_factor, yaw, root_geometry, true)
		if fit.is_empty():
			continue
		xf = fit["transform"]
		trunk_box = xf * ScenicCollision.bounds(root_geometry["support"])
		for points in _trunk_collision_geometry[variant_key]:
			trunk_box = trunk_box.merge(xf * ScenicCollision.bounds(points))
		if not _blocked(trunk_box.grow(0.2)):
			break
		fit = {}
	if fit.is_empty():
		placement_rejected += 1
		body.free()
		return
	# The imported GLTF currently has unbound textures. Restore them on local
	# surface overrides; leave the source asset and other scenes untouched.
	for child in model.find_children("", "MeshInstance3D", true, false):
		if path != FIR and path != CONIFER:
			for surface in child.mesh.get_surface_count():
				var source: StandardMaterial3D = child.get_active_material(surface)
				var key := path + ":" + source.resource_name
				if not _fir_materials.has(key):
					var local: StandardMaterial3D = source.duplicate()
					local.roughness = 0.92
					local.metallic_specular = 0.08
					local.albedo_color = Color(0.6, 0.85, 0.48) if "leaves" in source.resource_name or "twig" in source.resource_name else Color(0.72, 0.70, 0.65)
					_fir_materials[key] = local
				child.set_surface_override_material(surface, _fir_materials[key])
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
	var h := terrain.data.get_height(Vector3(p.x, 0, p.y))
	body.position = Vector3(p.x, h, p.y)
	model.transform = Transform3D(xf.basis, xf.origin - body.position)
	ScenicCollision.add_trunk(body, model.transform, _trunk_collision_geometry[variant_key])
	_occupied.append(trunk_box.grow(0.2))
	grounding_records.append({"kind": "tree", "transform": xf, "geometry": root_geometry})
	for child in model.find_children("", "GeometryInstance3D", true, false):
		child.visibility_range_end = 260.0 if path == YOUNG_PINE else 450.0
		child.lod_bias = 0.5
	if path == CONIFER:
		model.setup_lod()


func _build_landmark_rocks() -> void:
	# Nested rock outcrops form the left shoulder rather than isolated pebbles.
	for i in 38:
		var p := Vector2(rng.randf_range(-210, 0), rng.randf_range(42, 77))
		_batch_model(BOULDER if i % 2 == 0 else ROCK, p, rng.randf_range(5.0, 12.0), true)
	for i in 12:
		var p := Vector2(-40 - i * 11 + rng.randf_range(-5, 5), 35 + rng.randf_range(-4, 13))
		_batch_model(ROCK, p, rng.randf_range(11.0, 18.0), true)
	for i in 180:
		var x := rng.randf_range(-285, 45)
		var side := -1.0 if i % 2 == 0 else 1.0
		var p := Vector2(x, _river_center_z(x) + side * (stream_half_width(x) + rng.randf_range(-0.5, 5.0)))
		var extent:=rng.randf_range(0.18, 1.8)
		var precious: String=""
		if extent>=0.65:
			if i%22==3: precious="silver"
			elif i%33==7 and i%11!=5: precious="gold"
		_batch_model(BOULDER if i % 3 == 0 else ROCK, p, extent, true, i%11==0 and extent>=0.65, i%11==5 and extent>=0.65, precious)
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
	var pt: Node3D = load("res://scenes/scenic_particle_grass.tscn").instantiate()
	pt.name = "ParticleGrass"
	pt.mesh = preload("res://scenes/scenic_foliage.gd").grass_mesh()
	# Configure before binding terrain so the large default grid is never allocated.
	pt.instance_spacing = 0.25
	pt.cell_width = 8.0
	pt.grid_width = 7
	var pm: ShaderMaterial = pt.process_material.duplicate()
	pm.shader = load("res://assets/shaders/valley_grass_process.gdshader")
	pm.set_shader_parameter("min_scale", Vector3(0.07, 0.13, 0.07))
	pm.set_shader_parameter("max_scale", Vector3(0.12, 0.38, 0.12))
	pm.set_shader_parameter("clod_scale_boost", 0.1)
	pm.set_shader_parameter("patch_min_threshold", 0.06)
	pm.set_shader_parameter("patch_max_threshold", 0.3)
	pm.set_shader_parameter("wind_strength", 0.28)
	pm.set_shader_parameter("surface_slope_min", 0.7)
	pm.set_shader_parameter("main_noise_scale", 0.025)
	pm.set_shader_parameter("random_spacing", 0.85)
	# Root calibration follows the actual ribbon mesh; no inherited magic offset.
	pm.set_shader_parameter("position_offset", Vector3(0, -pt.mesh.get_aabb().position.y, 0))
	pm.set_shader_parameter("normal_strength", 0.6)
	pt.process_material = pm
	var gm := ShaderMaterial.new()
	gm.shader = load("res://assets/shaders/valley_grass.gdshader")
	pt.mesh_material_override = gm
	pt.terrain = terrain
	add_child(pt)
	print("[valley] grass instances=", pt.particle_count)


func _update_grass_exclusion() -> void:
	# 0.5m mask, shared by all GPU grass cells; no per-blade CPU physics queries.
	grass_exclusion = Image.create_empty(2048, 2048, false, Image.FORMAT_R8)
	for box in _occupied:
		var lo := Vector2i(floori((box.position.x + 511.75) * 2), floori((box.position.z + 511.75) * 2))
		var hi := Vector2i(ceili((box.end.x + 512.25) * 2), ceili((box.end.z + 512.25) * 2))
		var area := Rect2i(lo, hi - lo).intersection(Rect2i(0, 0, 2048, 2048))
		grass_exclusion.fill_rect(area, Color.WHITE)
	var material: ShaderMaterial = get_node("ParticleGrass").process_material
	material.set_shader_parameter("solid_exclusion", ImageTexture.create_from_image(grass_exclusion))


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
	_build_ridge_layer(0)
	_build_ridge_layer(1)


func _ridge_height(x: float, z: float, edge: float) -> float:
	var ridges := 1.0 - absf(_land_noise.get_noise_2d(x * 0.55, z * 0.55))
	return pow(maxf(0, edge), 0.85) * (45 + 55 * ridges + 20 * sin(z / 93.0) + 15 * sin(z / 37.0))


func _build_ridge_layer(layer: int) -> void:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for ix in 81:
		for iz in 161:
			var x := -1050.0 - layer * 400 + ix * 5.5
			var z := -800.0 + iz * 10.0
			var edge := sin(PI * ix / 80.0)
			var h := _ridge_height(x, z + layer * 73, edge) * (1 + layer * 0.45)
			st.add_vertex(Vector3(x, h - 5, z))
	for ix in 80:
		for iz in 160:
			var a := ix * 161 + iz
			for index in [a, a + 161, a + 1, a + 1, a + 161, a + 162]:
				st.add_index(index)
	st.generate_normals()
	var mat := ShaderMaterial.new()
	mat.shader = load("res://assets/shaders/valley_mountain.gdshader")
	mat.set_shader_parameter("layer_tint", Color(0.8, 0.87, 0.9) if layer == 0 else Color(0.91, 0.95, 1.0))
	var mountain := MeshInstance3D.new()
	mountain.name = "DistantRidge" if layer == 0 else "FarRidge"
	mountain.mesh = st.commit()
	mountain.material_override = mat
	add_child(mountain)
