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
	asset.uv_scale=[0.78,0.48,0.30,0.16,0.55][index]
	asset.normal_depth=[0.30,0.08,0.48,0.58,0.38][index]
	asset.roughness=[0.03,0.28,0.38,0.04,0.02][index]
	asset.ao_strength=[0.35,0.45,0.60,0.60,0.45][index]
	asset.detiling_rotation=[0.18,0.20,0.30,0.12,0.22][index]
	asset.detiling_shift=[0.18,0.20,0.20,0.10,0.20][index]
	if index==1 and mode=="refined":
		# Shallow mountain water exposes pale rounded pebbles. Dark loam is kept
		# for excavation only, not painted as a continuous riverbed ribbon.
		asset.name="Pale river pebbles"
		asset.albedo_texture=load(PREP+"gravel041_alb_ht.png")
		asset.normal_texture=load(PREP+"gravel041_nrm_rgh.png")
		asset.uv_scale=0.34
		asset.normal_depth=0.42
		asset.roughness=0.34
		asset.albedo_color=Color(1.0,1.0,0.96)
	if index==0:
		if mode=="existing":
			asset.albedo_texture=load(PREP+"grass004_alb_ht.png")
		elif mode=="refined":
			# GPT meadow candidates remain retained references; the photographed
			# source is materially cleaner in motion and has measured PBR channels.
			asset.albedo_texture=load(PREP+"grass004_alb_ht.png")
			asset.normal_texture=load(PREP+"grass004_nrm_rgh.png")
			# Keep the photographed lawn grounded in the same muted olive family as
			# the vegetation; the terrain colour map adds the broad patch variation.
			asset.albedo_color=Color(0.68,0.92,0.48)
		else:
			asset.albedo_texture=load(GENERATED+"turf_alb_ht_v2.png")
			asset.normal_texture=load(GENERATED+"turf_nrm_rgh_v2.png")
	if index==2 and mode=="refined":
		asset.name="Slope colluvium"
		asset.albedo_texture=load(GENERATED+"colluvium_gptimage2_v1_alb_ht.png")
		asset.normal_texture=load(GENERATED+"colluvium_gptimage2_v1_nrm_rgh.png")
	if index==4:
		if mode=="existing": asset.albedo_texture=load(PREP+"ground020_alb_ht.png")
		else:
			asset.albedo_texture=load(GENERATED+"loam_alb_ht_v2.png")
			asset.normal_texture=load(GENERATED+"loam_nrm_rgh_v2.png")
			asset.albedo_color=Color(0.72,0.61,0.50)

static func configure_terrain(material: Terrain3DMaterial) -> void:
	if variant()=="baseline": return
	for pair in [["blend_sharpness",0.48],["dual_scale_near",45.0],["dual_scale_far",140.0],["dual_scale_reduction",0.60],["mipmap_bias",1.0],["depth_blur",0.15],["macro_variation1",Color(0.70,0.98,0.52)],["macro_variation2",Color(0.80,0.94,0.58)],["noise1_scale",0.055],["noise2_scale",0.016]]:
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
	var roughness_anchor := "float roughness"
	var roughness_index := code.find(roughness_anchor)
	assert(roughness_index >= 0,"Terrain3D roughness interface changed")
	# Macro variation is deliberately green for turf. Remove that global tint in
	# proportion to texture ID 1 so the river keeps its white-grey pebble identity.
	code=code.insert(roughness_index,"""
	float wl_pebble_weight = 0.0;
	for (int wl_i = 0; wl_i < 4; wl_i++) {
		for (int wl_t = 0; wl_t < 2; wl_t++) {
			if (texture_ids[wl_i][wl_t] == 1) wl_pebble_weight += t_weights[wl_i][wl_t];
		}
	}
	macrov = mix(macrov, vec3(1.0), clamp(wl_pebble_weight, 0.0, 1.0));
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
