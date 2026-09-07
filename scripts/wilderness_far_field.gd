class_name WildernessFarField
extends Node3D

## Ten-times-wide visual terrain. The authored Terrain3D center remains the
## interactive layer; this ring is deliberately render-only: no bodies,
## collisions, harvestables or per-tree nodes are created outside it.

const Profile := preload("res://scripts/wilderness_generation_profile.gd")
const SeedStore := preload("res://scripts/wilderness_generation/world_seed_store.gd")
const Registry := preload("res://scripts/wilderness_generation/rule_registry.gd")
const Scheduler := preload("res://scripts/wilderness_generation/chunk_scheduler.gd")
const Presenter := preload("res://scripts/wilderness_generation/chunk_presenter.gd")

@export var world_seed: int = 0
@export_range(128, 1024, 128) var macro_texture_size := 512
@export var inner_half_extent := 480.0
@export var outer_half_extent: float = Profile.WORLD_HALF_EXTENT_M

var profile: RefCounted
var generation_stats: Dictionary = {}
var _terrain: Terrain3D
var _scheduler: Node
var _presenter: Node3D


func _ready() -> void:
	if world_seed == 0:
		var world := SeedStore.ensure_world()
		world_seed = int(world.get("world_seed", 1))
	profile = Profile.new(world_seed)
	set_meta(&"wilderness_seed", world_seed)
	call_deferred(&"_build_after_parent")


func _build_after_parent() -> void:
	var started_usec := Time.get_ticks_usec()
	_terrain = get_parent().get_node_or_null("Terrain3D") as Terrain3D
	var material := _build_macro_material()
	var triangles := 0
	triangles += _add_patch("FarNorth", -outer_half_extent, outer_half_extent,
		-outer_half_extent, -inner_half_extent, 128, 48, material)
	triangles += _add_patch("FarSouth", -outer_half_extent, outer_half_extent,
		inner_half_extent, outer_half_extent, 128, 48, material)
	triangles += _add_patch("FarWest", -outer_half_extent, -inner_half_extent,
		-inner_half_extent, inner_half_extent, 48, 24, material)
	triangles += _add_patch("FarEast", inner_half_extent, outer_half_extent,
		-inner_half_extent, inner_half_extent, 48, 24, material)
	var camera := get_viewport().get_camera_3d()
	if camera != null:
		camera.far = maxf(camera.far, outer_half_extent * 1.45)
	_start_background_cache()
	generation_stats = {
		"seed": world_seed,
		"world_size_m": outer_half_extent * 2.0,
		"near_entity_radius_m": Profile.ENTITY_RADIUS_M,
		"impostor_radius_m": Profile.IMPOSTOR_RADIUS_M,
		"far_triangles": triangles,
		"far_texture_px": macro_texture_size,
		"physics_bodies": 0,
		"generation_ms": (Time.get_ticks_usec() - started_usec) / 1000.0,
	}
	print("[wilderness-far] ", generation_stats)


func _start_background_cache() -> void:
	if OS.get_environment("WILDERNESS_DISABLE_BACKGROUND_CACHE") == "1":
		return
	var registry := Registry.new()
	registry.load_directory()
	_scheduler = Scheduler.new()
	_scheduler.name = "WildernessChunkScheduler"
	_scheduler.configure(world_seed, registry.snapshot_rules())
	add_child(_scheduler)
	var player := get_parent().get_node_or_null("Player") as Node3D
	_presenter = Presenter.new()
	_presenter.name = "WildernessChunkPresenter"
	_presenter.configure(world_seed, _scheduler.cache, _scheduler, player)
	add_child(_presenter)
	var player_xz := Vector2(player.global_position.x, player.global_position.z) if player != null else Vector2.ZERO
	var center := Vector2i(floori(player_xz.x / 256.0), floori(player_xz.y / 256.0))
	_scheduler.request_area(center, 4)


func _build_macro_material() -> StandardMaterial3D:
	var image := Image.create_empty(macro_texture_size, macro_texture_size, true, Image.FORMAT_RGB8)
	for y in macro_texture_size:
		var wz := lerpf(-outer_half_extent, outer_half_extent, float(y) / float(macro_texture_size - 1))
		for x in macro_texture_size:
			var wx := lerpf(-outer_half_extent, outer_half_extent, float(x) / float(macro_texture_size - 1))
			image.set_pixel(x, y, profile.macro_color_at(Vector2(wx, wz)))
	image.generate_mipmaps()
	var material := StandardMaterial3D.new()
	material.resource_name = "GeneratedWildernessFarTexture"
	material.albedo_texture = ImageTexture.create_from_image(image)
	material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	material.roughness = 0.94
	material.metallic_specular = 0.08
	return material


func _add_patch(patch_name: String, x0: float, x1: float, z0: float, z1: float,
		x_segments: int, z_segments: int, material: Material) -> int:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for iz in z_segments + 1:
		var z := lerpf(z0, z1, float(iz) / float(z_segments))
		for ix in x_segments + 1:
			var x := lerpf(x0, x1, float(ix) / float(x_segments))
			var y := _seam_height(Vector2(x, z))
			st.set_uv(Vector2(
				(x + outer_half_extent) / (outer_half_extent * 2.0),
				(z + outer_half_extent) / (outer_half_extent * 2.0)))
			st.add_vertex(Vector3(x, y, z))
	var row := x_segments + 1
	for iz in z_segments:
		for ix in x_segments:
			var a := iz * row + ix
			for index in [a, a + row, a + 1, a + 1, a + row, a + row + 1]:
				st.add_index(index)
	st.generate_normals()
	var mesh_instance := MeshInstance3D.new()
	mesh_instance.name = patch_name
	mesh_instance.mesh = st.commit()
	mesh_instance.material_override = material
	mesh_instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mesh_instance.visibility_range_begin = 360.0
	mesh_instance.visibility_range_begin_margin = 80.0
	mesh_instance.set_meta(&"render_only", true)
	add_child(mesh_instance)
	return x_segments * z_segments * 2


func _seam_height(p: Vector2) -> float:
	var generated: float = profile.height_at(p)
	if _terrain == null:
		return generated
	var edge_distance := maxf(absf(p.x), absf(p.y)) - inner_half_extent
	if edge_distance > 180.0:
		return generated
	var near_height := _terrain.data.get_height(Vector3(
		clampf(p.x, -511.0, 511.0), 0.0, clampf(p.y, -511.0, 511.0)))
	if not is_finite(near_height):
		return generated
	return lerpf(near_height, generated, smoothstep(0.0, 180.0, maxf(0.0, edge_distance)))


func presentation_height(p: Vector2) -> float:
	return _seam_height(p)
