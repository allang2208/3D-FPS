extends MultiMeshInstance3D
## Seeded continuous spherical positions, independent of screen pixels and grids.
const STAR_COUNT := 2400
var material: ShaderMaterial
var galaxy_material: ShaderMaterial
var galaxy_dome: MeshInstance3D
var elapsed := 0.0

func _ready() -> void:
	name = "NightStarfield"
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	material = ShaderMaterial.new()
	material.shader = preload("res://assets/environment/starfield.gdshader")
	material.render_priority = -20
	material_override = material
	_build_galaxy_dome()
	var stars := MultiMesh.new()
	stars.transform_format = MultiMesh.TRANSFORM_3D
	stars.use_colors = true
	stars.use_custom_data = true
	stars.mesh = QuadMesh.new()
	stars.instance_count = STAR_COUNT
	var rng := RandomNumberGenerator.new()
	rng.seed = 907122
	var band_normal := Vector3(0.45,0.38,0.81).normalized()
	for index in STAR_COUNT:
		var direction := Vector3.UP
		while true:
			var y := rng.randf_range(0.01,1.0)
			var angle := rng.randf()*TAU
			var radial := sqrt(1.0-y*y)
			direction = Vector3(cos(angle)*radial,y,sin(angle)*radial)
			var band := exp(-pow(direction.dot(band_normal)/0.22,2.0))
			if rng.randf() < 0.38+band*0.5: break
		var magnitude := pow(rng.randf(),3.0)
		var size := lerpf(0.0020,0.0048,magnitude)
		var right := direction.cross(Vector3.FORWARD if direction.y>0.9999 else Vector3.UP).normalized()
		var up := right.cross(direction).normalized()
		stars.set_instance_transform(index,Transform3D(Basis(right,up,-direction).scaled(Vector3.ONE*size),direction))
		var temperature := rng.randf()
		var tint := Color(1.0,0.88,0.74).lerp(Color(0.77,0.87,1.0),temperature)
		stars.set_instance_color(index,tint)
		stars.set_instance_custom_data(index,Color(rng.randf(),rng.randf_range(1.1,3.7),rng.randf_range(0.12,0.32),lerpf(0.35,2.4,magnitude)))
	multimesh = stars

func _build_galaxy_dome() -> void:
	galaxy_material = ShaderMaterial.new()
	galaxy_material.shader = preload("res://assets/environment/night_sky/galaxy_dome.gdshader")
	galaxy_material.set_shader_parameter("galaxy_texture",preload("res://assets/environment/night_sky/qwantani_night_puresky_8k.jpg"))
	galaxy_material.render_priority = -30
	var sphere := SphereMesh.new()
	sphere.radius = 0.985
	sphere.height = 1.97
	sphere.radial_segments = 64
	sphere.rings = 32
	galaxy_dome = MeshInstance3D.new()
	galaxy_dome.name = "PoeticMilkyWayDome"
	galaxy_dome.mesh = sphere
	galaxy_dome.material_override = galaxy_material
	galaxy_dome.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(galaxy_dome)

func set_sky_state(state: Dictionary) -> void:
	if material == null: return
	var night := 1.0-smoothstep(-0.22,-0.04,state.direction.y)
	visible = night > 0.001
	material.set_shader_parameter("night_visibility",night)
	material.set_shader_parameter("moon_direction",-state.direction)
	if galaxy_material != null:
		galaxy_material.set_shader_parameter("night_visibility",night)
		galaxy_material.set_shader_parameter("moon_direction",-state.direction)
		galaxy_material.set_shader_parameter("cloud_cover",float(state.get("cloud_cover",0.0)))
		galaxy_material.set_shader_parameter("sidereal_rotation",fposmod(float(state.get("phase",0.0))+0.08,1.0))

func _process(delta: float) -> void:
	var camera := get_viewport().get_camera_3d()
	if camera == null: return
	global_position = camera.global_position
	scale = Vector3.ONE*minf(2000.0,camera.far*0.8)
	if visible:
		elapsed += delta
		material.set_shader_parameter("animation_time",elapsed)
