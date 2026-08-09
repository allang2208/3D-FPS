// 基于 Terrain3D 官方 grass.gdshader（MIT）修改：
// - 颜色参数化（grass_color），与场景地表 grass001 色相统一
// - 其余风摆/亮度逻辑保留原版
shader_type spatial;

render_mode skip_vertex_transform, cull_disabled, blend_mix;

uniform vec2 wind_direction = vec2(1.0, 1.0);
// 与地表 grass001 贴图真实渲染色对齐（实测 hue≈118-122 / sat≈0.62 / val≈0.31），
// 避免粒子草与地面"色相不同、亮度脱节"的割裂感
uniform vec3 grass_color : source_color = vec3(0.13, 0.31, 0.12);

varying vec4 data;

void vertex() {
	data[2] = (VERTEX.y + 0.55);
	data[2] *= data[2];

	VERTEX.xz *= (1.0 - data[2]);

	COLOR = mix(COLOR, vec4(1.0), smoothstep(0.9, 1.0, data[2]));
	COLOR *= INSTANCE_CUSTOM[3] < 0.35 ? 1. : mix(1.0, 0.75, smoothstep(0.35, 0.0, data[2]));
	data.rg = INSTANCE_CUSTOM.rg;

	vec3 w_vertex = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
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
	// 亮度贴近地表：底部 0.75 倍、顶部 1.15 倍，整体 val≈0.31 附近
	ALBEDO = grass_color * (0.75 + data[2] * 0.4);
	ALBEDO.rg *= (data.rg * 0.3 + 0.9);
	ALBEDO *= pow(COLOR.rgb, vec3(2.2));
	float spec_rough = clamp(max(data[2], data[3]), 0., 1.);
	ROUGHNESS = 1. - spec_rough;
	SPECULAR = clamp(spec_rough * 0.25, 0., .15);

	// 背光减少（过强会让草叶发黄发白，与深绿地表脱节）
	BACKLIGHT = vec3(0.15);
	#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	ALBEDO = pow(ALBEDO, vec3(0.4));
	#endif
}
