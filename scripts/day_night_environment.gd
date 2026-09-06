extends WorldEnvironment
## Scene-local presentation, driven exclusively by the existing persistent HUD clock.
const UPDATE_INTERVAL := 0.1
var sun: DirectionalLight3D
var moon: DirectionalLight3D
var _timer := 0.0
var _materials: Array[ShaderMaterial] = []
var _cloud_sea_materials: Array[ShaderMaterial] = []
var _wisps: Array[BaseMaterial3D] = []
var current_state: Dictionary = {}
var _last_phase := -1.0
var starfield: MultiMeshInstance3D
var weather: Node3D

static func direction_at(phase: float) -> Vector3:
	var angle := fposmod(phase, 1.0) * TAU
	# East (+X), south (-Z), west (-X); noon elevation 62 degrees.
	return Vector3(cos(angle), sin(angle)*0.883, -sin(angle)*0.469).normalized()

static func sample(phase: float) -> Dictionary:
	var direction := direction_at(phase)
	var day := smoothstep(-0.12, 0.24, direction.y)
	var dusk := (1.0-smoothstep(0.04,0.38,absf(direction.y))) * smoothstep(-0.18,0.0,direction.y)
	return {"direction": direction, "phase": fposmod(phase,1.0), "day": day, "twilight": dusk,
		"zenith": Color(0.008,0.017,0.055).lerp(Color(0.17,0.39,0.69),day),
		"horizon": Color(0.026,0.035,0.055).lerp(Color(0.68,0.77,0.85),day).lerp(Color(0.75,0.48,0.34),dusk*0.48),
		"tint": Color(0.20,0.23,0.30).lerp(Color.WHITE,day).lerp(Color(1.0,0.75,0.57),dusk*0.48)}

func _ready() -> void:
	call_deferred("_bind")

func _bind() -> void:
	sun = get_parent().get_node_or_null("Sun") as DirectionalLight3D
	if sun == null:
		return
	sun.sky_mode = DirectionalLight3D.SKY_MODE_LIGHT_ONLY
	moon = DirectionalLight3D.new()
	moon.name = "Moon"
	moon.sky_mode = DirectionalLight3D.SKY_MODE_LIGHT_ONLY
	moon.light_color = Color(0.72,0.80,1.0)
	moon.light_angular_distance = 0.3
	moon.directional_shadow_max_distance = sun.directional_shadow_max_distance
	add_child(moon)
	starfield = preload("res://scripts/night_starfield.gd").new()
	add_child(starfield)
	weather = preload("res://scripts/weather_system.gd").new()
	add_child(weather)
	for item in get_parent().find_children("*", "MeshInstance3D", true, false):
		var material: Material = item.material_override
		if material is ShaderMaterial and material.shader != null and material.shader.resource_path in [
			"res://assets/environment/sky_base/cloud_sea_dynamic_v2.gdshader",
			"res://assets/environment/sky_base/mountain_sector.gdshader"]:
			if not _materials.has(material): _materials.append(material)
			if material.shader.resource_path.ends_with("cloud_sea_dynamic_v2.gdshader"):
				_cloud_sea_materials.append(material)
		elif material is BaseMaterial3D and str(item.name).begins_with("HubWisp"):
			_wisps.append(material)
	refresh()

func _process(delta: float) -> void:
	if not is_instance_valid(sun) or moon == null: return
	_timer += delta
	var hud := get_node_or_null("/root/HUD")
	if hud == null: return
	var clock: RefCounted = hud.game_clock
	var phase: float = fposmod(clock.elapsed_seconds / clock.DAY_SECONDS + clock.START_PHASE,1.0)
	_orient(direction_at(phase))
	if _timer >= UPDATE_INTERVAL and phase != _last_phase:
		_timer = fmod(_timer, UPDATE_INTERVAL)
		_last_phase = phase
		# Weather drives the shared 10 Hz environment refresh when present.
		if weather == null: apply_state(sample(phase))

func refresh() -> void:
	var hud := get_node_or_null("/root/HUD")
	if hud != null and is_instance_valid(sun) and moon != null:
		apply_state(sample(hud.game_clock.model().phase))

func _orient(direction: Vector3) -> void:
	# Basis avoids look_at singularities and makes light rays point away from the disc.
	sun.basis = Basis.looking_at(-direction,Vector3.UP)
	moon.basis = Basis.looking_at(direction,Vector3.UP)

func apply_state(state: Dictionary) -> void:
	state = state.duplicate()
	var sun_transmission := 1.0
	var moon_transmission := 1.0
	if weather != null:
		var cloud: float = weather.profile.x
		var wet: float = weather.profile.y
		sun_transmission = 1.0-weather.cloud_opacity(state.direction)*0.94
		moon_transmission = 1.0-weather.cloud_opacity(-state.direction)*0.94
		var gray := Color(0.023,0.028,0.038).lerp(Color(0.43,0.46,0.50),state.day)
		state.zenith = state.zenith.lerp(gray,cloud*0.7)
		state.horizon = state.horizon.lerp(gray,cloud*0.65)
		state.tint = state.tint.lerp(state.tint*Color(0.65,0.69,0.74),cloud*0.7)
		weather.cloud_material.set_shader_parameter("cloud_color",gray*lerpf(1.0,0.5,wet))
		environment.fog_density = lerpf(0.00055,0.0035,wet)
	state["cloud_cover"] = weather.profile.x if weather != null else 0.0
	current_state = state
	if starfield != null: starfield.set_sky_state(state)
	_orient(state.direction)
	var height: float = state.direction.y
	sun.light_energy = 0.74 * smoothstep(0.0,0.22,height)*sun_transmission
	sun.light_color = Color(1.0,0.52,0.25).lerp(Color(1.0,0.97,0.90),smoothstep(0.0,0.38,height))
	moon.light_energy = 0.22 * smoothstep(0.0,0.22,-height)*moon_transmission
	sun.shadow_enabled = height > 0.015 and sun_transmission>0.16
	moon.shadow_enabled = height < -0.015 and moon_transmission>0.16
	var mat := environment.sky.sky_material as ShaderMaterial
	mat.set_shader_parameter("sun_direction",state.direction)
	mat.set_shader_parameter("zenith",state.zenith)
	mat.set_shader_parameter("horizon",state.horizon)
	mat.set_shader_parameter("daylight",state.day)
	mat.set_shader_parameter("twilight",state.twilight)
	mat.set_shader_parameter("sun_transmission",sun_transmission)
	mat.set_shader_parameter("moon_transmission",moon_transmission)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.32,0.36,0.44).lerp(Color(0.72,0.80,0.91),state.day)
	environment.ambient_light_energy = lerpf(0.17,0.32,state.day)
	environment.fog_light_color = state.horizon
	for material in _materials:
		material.set_shader_parameter("day_night_tint",state.tint)
		material.set_shader_parameter("sun_direction",state.direction)
		material.set_shader_parameter("zenith",state.zenith)
		material.set_shader_parameter("horizon",state.horizon)
		material.set_shader_parameter("twilight",state.twilight)
	for material in _cloud_sea_materials:
		material.set_shader_parameter("weather_cloudiness",weather.profile.x if weather != null else 0.0)
		material.set_shader_parameter("weather_wetness",weather.profile.y if weather != null else 0.0)
		material.set_shader_parameter("weather_drift",weather.drift if weather != null else Vector2.ZERO)
		material.set_shader_parameter("weather_flash",weather.flash_light.light_energy if weather != null and is_instance_valid(weather.flash_light) else 0.0)
	for material in _wisps:
		material.albedo_color = Color(state.tint.r*.91,state.tint.g*.93,state.tint.b*.94,.8)
