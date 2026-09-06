extends RefCounted
## 全游戏共用的环境与太阳配置；场景不再单独覆盖光照参数。

const HDRI := "res://assets/environment/hdri/kloofendal_48d_partly_cloudy_puresky_2k.hdr"

static func create_environment() -> WorldEnvironment:
	var mat := PanoramaSkyMaterial.new()
	mat.panorama = load(HDRI)
	mat.energy_multiplier = 0.9
	var sky := Sky.new()
	sky.sky_material = mat
	sky.radiance_size = Sky.RADIANCE_SIZE_256
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.32
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	# 保留白色衣物和云层的高光细节。
	env.tonemap_white = 6.0
	env.tonemap_exposure = 0.92
	env.adjustment_enabled = true
	env.adjustment_saturation = 1.0
	env.adjustment_brightness = 0.98
	env.adjustment_contrast = 1.0
	env.fog_enabled = true
	env.fog_light_color = Color(0.62, 0.70, 0.75)
	env.fog_density = 0.00055
	env.fog_height = -45.0
	env.fog_height_density = 0.0
	# 雾影响场景纵深，不覆盖 HDRI 天空。
	env.fog_sky_affect = 0.0
	env.ssao_enabled = true
	env.ssao_radius = 1.2
	env.ssao_intensity = 1.0
	env.ssil_enabled = false
	env.ssr_enabled = false
	env.glow_enabled = false
	var node := WorldEnvironment.new()
	node.name = "WorldEnvironment"
	node.environment = env
	return node

static func create_sun() -> DirectionalLight3D:
	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	sun.rotation_degrees = Vector3(-42, 30, 0)
	sun.light_energy = 0.62
	sun.light_color = Color(1.0, 0.97, 0.90)
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 55.0
	return sun
