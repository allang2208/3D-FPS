extends RefCounted
## 复用当前 Terrain3D 生成的完整材质与纹理数组；仅替换其高度位移顶点阶段。
## 接口依赖随插件升级通过旷野接入测试验证，不修改 Terrain3D 的原始 shader。
static func bind_to_mesh(target: ShaderMaterial, terrain_material: Terrain3DMaterial) -> void:
	var source_rid := terrain_material.get_shader_rid()
	var code := RenderingServer.shader_get_code(source_rid)
	# 无头 Dummy renderer 不保留 shader 代码，几何测试使用插件生成的资源。
	if code.is_empty():
		terrain_material.shader_override_enabled=true
		code=terrain_material.shader_override.code
		terrain_material.shader_override_enabled=false
		source_rid=terrain_material.get_shader_rid()
	var natural_code := target.shader.code.replace("world_normal","voxel_world_normal")
	var start := code.find("void vertex()")
	assert(start>=0,"Terrain3D vertex interface changed")
	var end := _function_end(code,start)
	assert(start>=0 and end>start,"Terrain3D vertex interface changed")
	var vertex := """void vertex() {
		v_vertex = (MODEL_MATRIX * vec4(VERTEX,1.0)).xyz;
		world_position = v_vertex;
		voxel_world_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
		voxel_camera_position = CAMERA_POSITION_WORLD;
		v_vertex_xz_dist = length(v_vertex.xz - CAMERA_POSITION_WORLD.xz);
		UV = v_vertex.xz * _vertex_density;
		UV2 = UV * _region_texel_size + vec2(0.5 * _region_texel_size);
		VERTEX = (VIEW_MATRIX * vec4(v_vertex,1.0)).xyz;
		NORMAL = normalize(mat3(VIEW_MATRIX) * voxel_world_normal);
	}
	"""
	# 公共三向投射函数和纹理声明沿用试验场材质。
	var declarations := natural_code.substr(natural_code.find("uniform sampler2D"),natural_code.find("void vertex()")-natural_code.find("uniform sampler2D"))
	declarations+="varying vec3 voxel_camera_position;\n"
	code=code.substr(0,start)+declarations+vertex+code.substr(end)
	# Terrain3D 每帧更新自己的相机 uniform；独立网格使用当前渲染相机，
	# 避免双尺度贴图一直按初始化时的相机位置采样。
	code=code.replace("v_vertex - _camera_pos","v_vertex - voxel_camera_position")
	var fragment_start := code.find("void fragment()")
	var fragment_end := _function_end(code,fragment_start)
	var natural_start := natural_code.find("{",natural_code.find("void fragment()"))+1
	var natural_body := natural_code.substr(natural_start,_function_end(natural_code,natural_code.find("void fragment()"))-natural_start-1)
	var blend := """
		float disturbed = smoothstep(0.0,0.5,max(COLOR.g,COLOR.r));
		if (disturbed > 0.0) {
		vec3 source_albedo = ALBEDO;
		vec3 source_normal = NORMAL;
		float source_roughness = ROUGHNESS;
		{
	"""+natural_body+"""
		}
		ALBEDO = mix(source_albedo,ALBEDO,disturbed);
		NORMAL = normalize(mix(source_normal,NORMAL,disturbed));
		ROUGHNESS = mix(source_roughness,ROUGHNESS,disturbed);
		NORMAL_MAP_DEPTH *= 1.0-disturbed;
		AO = mix(AO,1.0,disturbed);
		}
	"""
	code=code.insert(fragment_end-1,blend)
	var shader := Shader.new()
	shader.code=code
	target.shader=shader
	sync_parameters(target,terrain_material)

static func sync_parameters(target: ShaderMaterial, terrain_material: Terrain3DMaterial) -> void:
	var source_rid := terrain_material.get_shader_rid()
	for parameter in RenderingServer.get_shader_parameter_list(source_rid):
		var value: Variant=RenderingServer.material_get_param(terrain_material.get_material_rid(),parameter.name)
		if value!=null:
			RenderingServer.material_set_param(target.get_rid(),parameter.name,value)

static func _function_end(code: String, start: int) -> int:
	var depth := 0
	for i in range(code.find("{",start),code.length()):
		if code[i]=="{": depth+=1
		elif code[i]=="}":
			depth-=1
			if depth==0: return i+1
	return -1
