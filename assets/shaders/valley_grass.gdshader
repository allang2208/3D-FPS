// 基于 Terrain3D 官方 grass.gdshader（MIT）修改：
// - 颜色参数化（grass_color），与场景地表 grass001 色相统一
// - 近景短草：保留风摆，使用较高粗糙度抑制叶尖闪光
shader_type spatial;

render_mode skip_vertex_transform, cull_disabled, blend_mix;

uniform vec2 wind_direction = vec2(1.0, 1.0);
// 溪谷草色；实例颜色继续接收地形颜色图。
uniform vec3 grass_color : source_color = vec3(0.32, 0.40, 0.18);

varying vec4 data;

void vertex() {
	// UV.y is normalized blade length even for the shorter blades in the tuft.
	data[2] = UV.y;
	data[2] *= data[2];

	COLOR = mix(COLOR, vec4(1.0), smoothstep(0.9, 1.0, data[2]));
	COLOR *= mix(0.82, 1.0, smoothstep(0.0, 0.6, data[2]));
	data.rg = INSTANCE_CUSTOM.rg;

	vec3 w_vertex = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec3 bend_direction = normalize(MODEL_MATRIX[0].xyz + MODEL_MATRIX[2].xyz);
	w_vertex += bend_direction * data[2] * INSTANCE_CUSTOM[3] * 0.23;
	float scale = pow(INSTANCE_CUSTOM[3] * INSTANCE_CUSTOM[3], 0.707);
	float force = INSTANCE_CUSTOM[2] * data[2] * scale;
	force -= fract(force * 256.0) * force * 0.05;
	force = pow(force, 0.707);

	float lateral_wobble = sin(TIME * 2.0 * (1.0 + data.r + data.g)) * 0.25 * (1.0 - INSTANCE_CUSTOM[2]);
	vec2 direction = normalize(wind_direction);
	w_vertex.xz -= (vec2(-direction.y, direction.x) * lateral_wobble + direction) * force;
	w_vertex.y -= INSTANCE_CUSTOM[2] * force * data[2];

	data[3] = force;

	VERTEX = (VIEW_MATRIX * vec4(w_vertex, 1.0)).xyz;
	NORMAL = MODELVIEW_NORMAL_MATRIX * NORMAL;
	BINORMAL = MODELVIEW_NORMAL_MATRIX * BINORMAL;
	TANGENT = MODELVIEW_NORMAL_MATRIX * TANGENT;
}

void fragment() {
	// 草根至叶尖的轻微亮度变化。
	ALBEDO = grass_color * (0.85 + data[2] * 0.3);
	ALBEDO.rg *= (data.rg * 0.3 + 0.9);
	ALBEDO *= COLOR.rgb;
	// Gentle midrib shading gives each ribbon a curved cross-section without more triangles.
	ALBEDO *= mix(0.88, 1.04, 1.0 - abs(UV.x * 2.0 - 1.0));
	ROUGHNESS = 0.85;
	SPECULAR = 0.12;

	// 背光减少（过强会让草叶发黄发白，与深绿地表脱节）
	BACKLIGHT = vec3(0.15);
	#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	ALBEDO = pow(ALBEDO, vec3(0.4));
	#endif
}
