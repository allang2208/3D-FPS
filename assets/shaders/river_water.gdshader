shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, specular_schlick_ggx;

// 溪流水面：UV 流动法线扰动 + 深度混合淡蓝 + 菲涅尔高光 + 岸缘微亮
// 用法：MeshInstance3D + PlaneMesh，材质用本 shader；把 mesh 放在河道低洼处

uniform vec4 water_color : source_color = vec4(0.16, 0.30, 0.34, 0.72);
uniform vec4 deep_color : source_color = vec4(0.08, 0.18, 0.24, 0.88);
uniform float flow_speed : hint_range(0.0, 2.0) = 0.35;
uniform float wave_scale : hint_range(0.0, 2.0) = 0.55;
uniform float fresnel_power : hint_range(0.0, 8.0) = 3.2;
uniform float specular_strength : hint_range(0.0, 2.0) = 0.7;

varying vec2 world_uv;

void vertex() {
	world_uv = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xz;
}

void fragment() {
	float t = TIME * flow_speed;
	// 两层反向流动的波（避免单层纹理感）
	vec2 uv1 = world_uv * wave_scale + vec2(t, t * 0.6);
	vec2 uv2 = world_uv * wave_scale * 1.7 - vec2(t * 0.8, t * 0.4);
	float n1 = sin(uv1.x * 6.2831 + sin(uv1.y * 4.0) * 2.0);
	float n2 = cos(uv2.y * 5.0 + sin(uv2.x * 3.0) * 1.5);
	float wave = (n1 + n2) * 0.5;

	// 深度混合：近处（深度小）淡、远处深
	float depth = 1.0 - clamp(NORMAL.z * 1.5, 0.0, 1.0);
	vec3 col = mix(water_color.rgb, deep_color.rgb, depth * 0.65 + wave * 0.12);

	// 菲涅尔：掠射角更亮更白
	float ndv = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float fres = pow(1.0 - ndv, fresnel_power);
	col += vec3(0.35, 0.5, 0.55) * fres * 0.7;
	// 波光高光
	col += vec3(0.9, 0.95, 1.0) * specular_strength * max(0.0, wave) * fres * 0.8;

	float alpha = mix(water_color.a, deep_color.a, depth * 0.5);
	alpha = clamp(alpha + fres * 0.15, 0.0, 1.0);
	ALBEDO = col;
	ALPHA = alpha;
	METALLIC = 0.0;
	ROUGHNESS = 0.12 + wave * 0.12;
	SPECULAR = 0.6;
}
