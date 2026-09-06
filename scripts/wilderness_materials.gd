extends RefCounted
## 固定取景对照可设 WILDERNESS_MATERIAL_VARIANT=baseline/existing/generated。
const PREP := "res://assets/textures/terrain_prepared/"
const GENERATED := "res://assets/textures/wilderness_generated/"
static func variant() -> String:
	return OS.get_environment("WILDERNESS_MATERIAL_VARIANT") if OS.has_environment("WILDERNESS_MATERIAL_VARIANT") else "refined"

static func configure_asset(asset: Terrain3DTextureAsset,index: int) -> void:
	var mode:=variant()
	if mode=="baseline": return
	# grass, bank sand, gravel, rock, loam: 分别校准尺度与反光。
	asset.uv_scale=[0.75,0.48,0.60,0.16,0.55][index]
	asset.normal_depth=[0.24,0.08,0.42,0.58,0.38][index]
	asset.roughness=[0.03,0.28,0.38,0.04,0.02][index]
	asset.ao_strength=[0.35,0.45,0.60,0.60,0.45][index]
	asset.detiling_rotation=[0.18,0.20,0.30,0.12,0.22][index]
	asset.detiling_shift=[0.18,0.20,0.20,0.10,0.20][index]
	if index==1 and mode=="refined":
		# The old dune texture baked large ripples into the riverbed. Use fine silt;
		# Terrain3D's existing shoreline color alpha supplies the wetness gradient.
		asset.name="Riverbank silt"
		asset.albedo_texture=load(GENERATED+"loam_alb_ht_v2.png")
		asset.normal_texture=load(GENERATED+"loam_nrm_rgh_v2.png")
		asset.normal_depth=0.18
		asset.albedo_color=Color(1.65,1.60,1.48)
	if index==0:
		if mode=="existing" or mode=="refined":
			asset.albedo_texture=load(PREP+"grass004_alb_ht.png")
		else:
			asset.albedo_texture=load(GENERATED+"turf_alb_ht_v2.png")
			asset.normal_texture=load(GENERATED+"turf_nrm_rgh_v2.png")
	if index==4:
		if mode=="existing": asset.albedo_texture=load(PREP+"ground020_alb_ht.png")
		else:
			asset.albedo_texture=load(GENERATED+"loam_alb_ht_v2.png")
			asset.normal_texture=load(GENERATED+"loam_nrm_rgh_v2.png")

static func configure_terrain(material: Terrain3DMaterial) -> void:
	if variant()=="baseline": return
	for pair in [["blend_sharpness",0.48],["dual_scale_near",45.0],["dual_scale_far",140.0],["dual_scale_reduction",0.60],["mipmap_bias",1.0],["depth_blur",0.15],["macro_variation1",Color(0.92,0.96,0.88)],["macro_variation2",Color(0.97,0.92,0.87)],["noise1_scale",0.055],["noise2_scale",0.016]]:
		material.set_shader_param(pair[0],pair[1])
	var code:=RenderingServer.shader_get_code(material.get_shader_rid())
	if code.is_empty(): return # 无头只验证几何；实机渲染验证下面的着色器。
	var anchor:="vec4 weights_id_0 = 1.0 - weights_id_1;"
	assert(code.contains(anchor),"Terrain3D blend interface changed")
	# 只打散已经混合的边缘，不把纯草地或纯岩面随机涂成另一类材质。
	code=code.replace(anchor,"""
	float wl_edge_noise = texture(noise_texture,v_vertex.xz*0.31).r-0.5;
	weights_id_1=clamp(weights_id_1+wl_edge_noise*0.5*weights_id_1*(1.0-weights_id_1),vec4(0.0),vec4(1.0));
	vec4 weights_id_0 = 1.0 - weights_id_1;
	""")
	var shader:=Shader.new()
	shader.code=code
	material.shader_override=shader
	material.shader_override_enabled=true

static func configure_voxel(material: ShaderMaterial) -> void:
	var mode:=variant()
	if mode=="baseline": return
	material.set_shader_parameter("voxel_grass_scale",0.75)
	material.set_shader_parameter("voxel_soil_scale",0.55)
	material.set_shader_parameter("voxel_rock_scale",0.16)
	material.set_shader_parameter("voxel_detail_variation",true)
	if mode=="existing" or mode=="refined":
		material.set_shader_parameter("grass_color",load(PREP+"grass004_alb_ht.png"))
	else:
		material.set_shader_parameter("grass_color",load(GENERATED+"turf_alb_ht_1k_v2.png"))
		material.set_shader_parameter("grass_normal",load(GENERATED+"turf_nrm_rgh_1k_v2.png"))
	if mode=="existing": material.set_shader_parameter("soil_color",load(PREP+"ground020_alb_ht.png"))
	else:
		material.set_shader_parameter("soil_color",load(GENERATED+"loam_alb_ht_1k_v2.png"))
		material.set_shader_parameter("soil_normal",load(GENERATED+"loam_nrm_rgh_1k_v2.png"))
