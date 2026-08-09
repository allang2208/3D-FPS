shader_type spatial;
// 程序化火球（D 方案）：径向明暗 + fbm 噪声翻涌火焰，自发光，随时间动画
render_mode unshaded, blend_mix, depth_draw_alpha_prepass, cull_back;

uniform vec3 core_color : source_color = vec3(1.0, 0.96, 0.75);
uniform vec3 mid_color : source_color = vec3(1.0, 0.55, 0.18);
uniform vec3 edge_color : source_color = vec3(0.65, 0.14, 0.04);
uniform float time_scale : hint_range(0.2, 4.0) = 1.6;

float hash(vec3 p) {
	return fract(sin(dot(p, vec3(12.9898, 78.233, 45.164))) * 43758.5453);
}

float noise(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(
		mix(mix(hash(i + vec3(0, 0, 0)), hash(i + vec3(1, 0, 0)), f.x),
			mix(hash(i + vec3(0, 1, 0)), hash(i + vec3(1, 1, 0)), f.x), f.y),
		mix(mix(hash(i + vec3(0, 0, 1)), hash(i + vec3(1, 0, 1)), f.x),
			mix(hash(i + vec3(0, 1, 1)), hash(i + vec3(1, 1, 1)), f.x), f.y),
		f.z);
}

float fbm(vec3 p) {
	float v = 0.0;
	float a = 0.5;
	for (int i = 0; i < 4; i++) {
		v += a * noise(p);
		p = p * 2.03 + vec3(0.13);
		a *= 0.5;
	}
	return v;
}

void fragment() {
	vec3 view = -normalize(VERTEX);
	float fres = clamp(dot(normalize(NORMAL), view), 0.0, 1.0);
	float t = TIME * time_scale;
	vec3 p = vec3(UV.x * 3.5, UV.y * 3.5, t * 0.7);
	float n1 = fbm(p);
	float n2 = fbm(p * 1.7 + vec3(0.0, t, 1.3));
	float flame = smoothstep(0.2, 0.9, n1 * 0.65 + n2 * 0.35);
	float core = smoothstep(0.0, 0.55, fres);
	vec3 col = mix(edge_color, mid_color, core);
	col = mix(col, core_color, flame * core);
	float alpha = core * (0.7 + 0.3 * flame);
	ALBEDO = col;
	EMISSION = col * (1.1 + flame * 1.8);
	ALPHA = alpha;
}
