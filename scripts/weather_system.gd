extends Node3D
## Local outdoor effects, deterministic automatic schedule from the saved game clock.
const NAMES := ["clear","overcast","light_rain","rain","storm"]
const LABELS := ["晴天","阴天","小雨","中雨","暴风雨"]
const PROFILES := {
	"clear": Vector3(0.0,0.0,0.0),
	"overcast": Vector3(0.82,0.0,0.2),
	"light_rain": Vector3(0.88,0.18,0.25),
	"rain": Vector3(0.94,0.65,0.55),
	"storm": Vector3(1.0,1.0,1.0)}
var mode := "overcast"
var automatic := true
var profile := Vector3(0.82,0,0.2)
var target := profile
var cloud_image: Image
var cloud_material: ShaderMaterial
var clouds: MeshInstance3D
var rain: GPUParticles3D
var rain_material: ParticleProcessMaterial
var rain_audio: AudioStreamPlayer
var rain_detail_audio: AudioStreamPlayer
var rain_drizzle_audio: AudioStreamPlayer
var _rain_gain := 0.0
var _detail_gain := 0.0
var _drizzle_gain := 0.0
const FLASH_DURATION := 0.72
var _restrike_time := 0.12
var thunder: AudioStreamPlayer3D
var flash_light: DirectionalLight3D
var bolt: MeshInstance3D
var drift := Vector2.ZERO
var flash_remaining := 0.0
var thunder_delay := -1.0
var strike_distance := 500.0
var sheltered := false
var _tick := 0.0
var _roof_tick := 0.0
var _storm_timer := 12.0
var _rng := RandomNumberGenerator.new()
const Schedule := preload("res://scripts/weather_schedule.gd")
var _weather_until := -1.0
var _previous_clock := -1.0
var _schedule_seed := -1
static var _cloud_cache: ImageTexture

static func scheduled_mode(elapsed: float, day_seconds: float, seed_value := 72124) -> String:
	return Schedule.state_at(elapsed,seed_value,day_seconds).mode

func _ready() -> void:
	name = "Weather"
	_rng.randomize()
	var hud := get_node_or_null("/root/HUD")
	if hud != null:
		mode = scheduled_mode(hud.game_clock.elapsed_seconds,hud.game_clock.DAY_SECONDS,hud.game_clock.weather_seed)
		if hud.has_meta("weather_override"):
			mode = hud.get_meta("weather_override")
			automatic = false
		target = PROFILES[mode]
		profile = target
	_build_clouds()
	_build_rain()
	rain_audio = _rain_player("res://assets/sfx/weather/rain_soft_v2.wav")
	rain_detail_audio = _rain_player("res://assets/sfx/weather/rain_patter_v2.wav")
	rain_drizzle_audio = _rain_player("res://assets/sfx/weather/rain_leaves_ground_ccby_v4.wav")
	thunder = AudioStreamPlayer3D.new()
	thunder.bus = "SFX"
	thunder.unit_size = 400
	thunder.max_distance = 2400
	thunder.volume_db = -6
	# Distant thunder occupies a broad area while retaining the strike direction.
	thunder.panning_strength = 0.4
	add_child(thunder)
	flash_light = DirectionalLight3D.new()
	flash_light.sky_mode = DirectionalLight3D.SKY_MODE_LIGHT_ONLY
	flash_light.light_color = Color(0.76,0.84,1.0)
	flash_light.light_energy = 0
	flash_light.rotation_degrees = Vector3(-65,25,0)
	flash_light.shadow_enabled = false
	add_child(flash_light)
	bolt = MeshInstance3D.new()
	bolt.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var material := ShaderMaterial.new()
	material.shader = preload("res://assets/environment/lightning.gdshader")
	bolt.material_override = material
	bolt.visible = false
	add_child(bolt)

func _rain_player(path: String) -> AudioStreamPlayer:
	var player := AudioStreamPlayer.new()
	player.set_meta("source_path",path)
	player.bus = "SFX"
	var stream := load(path).duplicate() as AudioStreamWAV
	stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
	# Loop positions are sample frames, never compressed bytes or stereo samples.
	stream.loop_end = roundi(stream.get_length()*stream.mix_rate)
	player.stream = stream
	player.volume_db = -80
	add_child(player)
	return player

func _update_rain_audio(delta: float) -> void:
	var amount := clampf(profile.y,0,1)
	# Exponential weather blending approaches zero without ever equalling it.
	if amount<0.001: amount = 0.0
	var cover := 0.32 if sheltered else 1.0
	var blend := 1.0-exp(-delta/0.7)
	var targets := rain_audio_targets(amount) * cover
	_rain_gain = lerpf(_rain_gain,targets.x,blend)
	_detail_gain = lerpf(_detail_gain,targets.y,blend)
	_drizzle_gain = lerpf(_drizzle_gain,targets.z,blend)
	var players: Array[AudioStreamPlayer] = [rain_audio,rain_detail_audio,rain_drizzle_audio]
	var gains := [_rain_gain,_detail_gain,_drizzle_gain]
	for i in players.size():
		var player := players[i]
		var gain: float = gains[i]
		player.volume_db = linear_to_db(maxf(gain,0.0001))
		if gain>0.0005:
			if not player.playing: player.play()
		elif player.playing:
			player.stop()

static func rain_audio_targets(amount: float) -> Vector3:
	amount = clampf(amount,0.0,1.0)
	var drizzle := Vector3(0.012,0.0,0.09)
	var medium := Vector3(0.18,0.22,0.055)
	var storm := Vector3(0.52,0.38,0.0)
	if amount<=PROFILES.light_rain.y:
		return drizzle * smoothstep(0.0,PROFILES.light_rain.y,amount)
	if amount<=PROFILES.rain.y:
		var rain_weight := smoothstep(PROFILES.light_rain.y,PROFILES.rain.y,amount)
		return drizzle.lerp(medium,rain_weight)
	var weight := smoothstep(PROFILES.rain.y,PROFILES.storm.y,amount)
	return medium.lerp(storm,weight)

func _build_clouds() -> void:
	if _cloud_cache == null:
		var noise := FastNoiseLite.new()
		noise.seed = 72124
		noise.frequency = 0.045
		noise.fractal_octaves = 4
		var generated := Image.create(128,128,false,Image.FORMAT_RF)
		var low := 1.0
		var high := -1.0
		for y in 128:
			for x in 128:
				var u := x/128.0
				var v := y/128.0
				var a := lerpf(noise.get_noise_2d(x,y),noise.get_noise_2d(x-128,y),u)
				var b := lerpf(noise.get_noise_2d(x,y-128),noise.get_noise_2d(x-128,y-128),u)
				var value := lerpf(a,b,v)
				low = minf(low,value)
				high = maxf(high,value)
				generated.set_pixel(x,y,Color(value,0,0))
		for y in 128:
			for x in 128:
				generated.set_pixel(x,y,Color((generated.get_pixel(x,y).r-low)/(high-low),0,0))
		_cloud_cache = ImageTexture.create_from_image(generated)
	cloud_image = _cloud_cache.get_image()
	cloud_material = ShaderMaterial.new()
	cloud_material.shader = preload("res://assets/environment/weather_clouds.gdshader")
	cloud_material.set_shader_parameter("cloud_texture",_cloud_cache)
	cloud_material.render_priority = -10
	clouds = MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 1
	sphere.height = 2
	sphere.radial_segments = 32
	sphere.rings = 16
	clouds.mesh = sphere
	clouds.material_override = cloud_material
	clouds.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(clouds)

func _build_rain() -> void:
	rain = GPUParticles3D.new()
	rain.amount = 1200
	rain.amount_ratio = 0.0
	rain.lifetime = 1.25
	rain.local_coords = false
	rain.fixed_fps = 30
	rain.visibility_aabb = AABB(Vector3(-20,-24,-20),Vector3(40,32,40))
	rain.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	rain_material = ParticleProcessMaterial.new()
	rain_material.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	rain_material.emission_box_extents = Vector3(12,0.3,12)
	rain_material.direction = Vector3(0,-1,0)
	rain_material.spread = 5
	rain_material.initial_velocity_min = 16
	rain_material.initial_velocity_max = 23
	rain_material.scale_min = 0.65
	rain_material.scale_max = 1.3
	var variation := Gradient.new()
	variation.set_color(0,Color(0.92,0.95,1.0,0.55))
	variation.set_color(1,Color(1.0,1.0,1.0,1.0))
	var variation_texture := GradientTexture1D.new()
	variation_texture.gradient = variation
	rain_material.color_initial_ramp = variation_texture
	rain_material.gravity = Vector3(0,-5,0)
	rain.process_material = rain_material
	var drop := QuadMesh.new()
	drop.size = Vector2(0.012,0.22)
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y
	material.albedo_color = Color(0.66,0.73,0.81,0.20)
	material.vertex_color_use_as_albedo = true
	var soft_drop := Image.create(8,64,false,Image.FORMAT_RGBA8)
	for y in 64:
		for x in 8:
			var alpha := pow(1.0-absf((x-3.5)/3.5),1.5)*sin(PI*y/63.0)
			soft_drop.set_pixel(x,y,Color(1,1,1,alpha))
	material.albedo_texture = ImageTexture.create_from_image(soft_drop)
	drop.material = material
	rain.draw_pass_1 = drop
	add_child(rain)

func set_weather(value: String, immediate := false) -> bool:
	if not PROFILES.has(value): return false
	automatic = false
	var hud := get_node_or_null("/root/HUD")
	if hud != null: hud.set_meta("weather_override",value)
	mode = value
	target = PROFILES[value]
	if immediate: profile = target
	if value != "storm":
		flash_remaining = 0
		thunder_delay = -1
		if thunder != null: thunder.stop()
	return true

func resume_automatic() -> void:
	automatic = true
	_weather_until = -1
	var hud := get_node_or_null("/root/HUD")
	if hud != null: hud.remove_meta("weather_override")

func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_F6:
		if event.shift_pressed: resume_automatic()
		else: set_weather(NAMES[(NAMES.find(mode)+1)%NAMES.size()])
		print("WEATHER ","自动" if automatic else LABELS[NAMES.find(mode)])
		get_viewport().set_input_as_handled()

func cloud_opacity(direction: Vector3) -> float:
	if cloud_image == null: return 0.0
	var uv := Vector2(direction.x,direction.z)/maxf(direction.y,0.12)*0.12+drift
	# Bilinear repeat sampling matches the visual cloud texture.
	var point := Vector2(fposmod(uv.x,1.0),fposmod(uv.y,1.0))*128.0-Vector2.ONE*0.5
	var x := int(floor(point.x))
	var y := int(floor(point.y))
	var a := lerpf(cloud_image.get_pixel(posmod(x,128),posmod(y,128)).r,cloud_image.get_pixel(posmod(x+1,128),posmod(y,128)).r,fposmod(point.x,1.0))
	var b := lerpf(cloud_image.get_pixel(posmod(x,128),posmod(y+1,128)).r,cloud_image.get_pixel(posmod(x+1,128),posmod(y+1,128)).r,fposmod(point.x,1.0))
	return smoothstep(1.0-profile.x,1.18-profile.x,lerpf(a,b,fposmod(point.y,1.0)))*smoothstep(-0.02,0.15,direction.y)

func _process(delta: float) -> void:
	var camera := get_viewport().get_camera_3d()
	if camera == null: return
	var hud := get_node_or_null("/root/HUD")
	if automatic and hud != null:
		var elapsed: float = hud.game_clock.elapsed_seconds
		if elapsed>=_weather_until or elapsed<_previous_clock or _schedule_seed!=hud.game_clock.weather_seed:
			_schedule_seed = hud.game_clock.weather_seed
			var state := Schedule.state_at(elapsed,hud.game_clock.weather_seed,hud.game_clock.DAY_SECONDS)
			_weather_until = state.until
			mode = state.mode
			target = PROFILES[mode]
		_previous_clock = elapsed
	profile = profile.lerp(target,1.0-exp(-delta/5.0))
	clouds.global_position = camera.global_position
	clouds.scale = Vector3.ONE*minf(2300,camera.far*0.9)
	drift += Vector2(0.002,0.0008)*delta*lerpf(0.4,2.0,profile.z)
	rain.global_position = camera.global_position+Vector3(0,11,0)
	_roof_tick += delta
	if _roof_tick>0.25:
		_roof_tick = 0
		var query := PhysicsRayQueryParameters3D.create(camera.global_position+Vector3.UP*.3,camera.global_position+Vector3.UP*30)
		sheltered = not get_world_3d().direct_space_state.intersect_ray(query).is_empty()
	rain.visible = profile.y>0.01 and not sheltered
	rain.emitting = rain.visible
	rain.amount_ratio = profile.y
	rain_material.direction = Vector3(profile.z*0.32,-1,profile.z*0.12).normalized()
	_update_rain_audio(delta)
	if mode == "storm" and profile.y>0.65:
		_storm_timer -= delta
		if _storm_timer<=0 and not thunder.playing and thunder_delay<0:
			trigger_lightning()
			_storm_timer = _rng.randf_range(12,25)
	if thunder_delay>=0:
		thunder_delay -= delta
		if thunder_delay<=0:
			thunder.stream = load("res://assets/sfx/weather/thunder_wilderness_%d.wav" % _rng.randi_range(1,3))
			thunder.pitch_scale = _rng.randf_range(0.96,1.03)
			thunder.play()
			thunder_delay = -1.0
	flash_remaining = maxf(0,flash_remaining-delta)
	var age := FLASH_DURATION-flash_remaining
	var flash := 0.0
	var brightness := 0.0
	if flash_remaining>0:
		var first := exp(-age/0.045)
		var second := exp(-maxf(0,age-_restrike_time)/0.065) if age>=_restrike_time else 0.0
		flash = first*0.48+second*0.32
		brightness = (first*1.7+second*1.2+exp(-age/0.22)*0.32)*smoothstep(0,0.15,flash_remaining)
	flash_light.light_energy = flash
	bolt.visible = flash_remaining>0
	bolt.material_override.set_shader_parameter("brightness",brightness)
	bolt.material_override.set_shader_parameter("reveal",minf(1.05,age/0.025))
	cloud_material.set_shader_parameter("flash",flash)
	_tick += delta
	if _tick>=0.1:
		_tick = fmod(_tick,0.1)
		cloud_material.set_shader_parameter("drift",drift)
		cloud_material.set_shader_parameter("coverage",profile.x)
		get_parent().refresh()

func trigger_lightning() -> void:
	var camera := get_viewport().get_camera_3d()
	if camera == null or mode != "storm": return
	strike_distance = _rng.randf_range(300,900)
	var forward := -camera.global_basis.z
	forward.y = 0
	if forward.length_squared()<0.001: forward = Vector3.FORWARD
	forward = forward.normalized().rotated(Vector3.UP,_rng.randf_range(-0.8,0.8))
	var origin := camera.global_position+forward*strike_distance
	thunder.global_position = origin+Vector3.UP*60
	thunder_delay = strike_distance/343.0
	flash_remaining = FLASH_DURATION
	_restrike_time = _rng.randf_range(0.09,0.17)
	var mesh := ImmediateMesh.new()
	mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
	var previous := origin+Vector3.UP*220
	var side := forward.cross(Vector3.UP).normalized()
	var lateral := 0.0
	for step in 28:
		var progress := (step+1)/28.0
		lateral += _rng.randf_range(-7,7)
		var next := origin+Vector3.UP*(220-progress*194)+side*lateral+forward*_rng.randf_range(-3,3)
		_bolt_segment(mesh,previous,next,side,lerpf(3.0,0.85,progress),1.0,step/28.0,progress)
		if step in [5,10,15,20,24]:
			var branch := next
			var sign_x := -1.0 if _rng.randf()<0.5 else 1.0
			var count := _rng.randi_range(4,7)
			for j in count:
				var end := branch+side*sign_x*_rng.randf_range(5,13)+Vector3.DOWN*_rng.randf_range(3,10)
				_bolt_segment(mesh,branch,end,side,lerpf(1.4,0.15,(j+1.0)/count),0.6,progress, minf(1,progress+(j+1)*0.015))
				branch = end
		previous = next
	mesh.surface_end()
	bolt.mesh = mesh

func _bolt_segment(mesh: ImmediateMesh, a: Vector3, b: Vector3, side: Vector3, width: float, strength: float, start: float, end: float) -> void:
	var vertices := [a-side*width,a+side*width,b+side*width*0.82,a-side*width,b+side*width*0.82,b-side*width*0.82]
	var uvs := [Vector2(0,start),Vector2(1,start),Vector2(1,end),Vector2(0,start),Vector2(1,end),Vector2(0,end)]
	for i in 6:
		mesh.surface_set_color(Color(1,1,1,strength))
		mesh.surface_set_uv(uvs[i])
		mesh.surface_add_vertex(vertices[i])
