shader_type spatial;
render_mode blend_mix, cull_disabled;

uniform sampler2D scene_depth : hint_depth_texture, filter_nearest, repeat_disable;
varying vec2 world_xz;

float water_hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}
float water_noise(vec2 p) {
	vec2 cell = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(water_hash(cell), water_hash(cell + vec2(1, 0)), f.x),
		mix(water_hash(cell + vec2(0, 1)), water_hash(cell + vec2(1, 1)), f.x), f.y);
}

void vertex() {
	world_xz = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xz;
}

void fragment() {
	float depth = texture(scene_depth, SCREEN_UV).r;
	vec4 bed = INV_PROJECTION_MATRIX * vec4(SCREEN_UV * 2.0 - 1.0, depth, 1.0);
	float thickness = max(0.0, VERTEX.z - bed.z / bed.w);
	vec2 flow = world_xz * 1.3 + vec2(-TIME * 0.18, TIME * 0.04);
	float ripples = water_noise(flow) - 0.5;
	float cross_wave = water_noise(mat2(vec2(0.8, 0.6), vec2(-0.6, 0.8)) * flow * 1.7 + vec2(12.4, 5.8)) - 0.5;
	vec3 normal_world = normalize(vec3(ripples * 0.09, 1.0, cross_wave * 0.07));
	NORMAL = normalize((VIEW_MATRIX * vec4(normal_world, 0.0)).xyz);
	float fresnel = pow(1.0 - max(dot(NORMAL, VIEW), 0.0), 4.0);
	ALBEDO = mix(vec3(0.075, 0.13, 0.12), vec3(0.34, 0.43, 0.46), fresnel);
	ROUGHNESS = 0.30;
	SPECULAR = 0.32;
	ALPHA = mix(0.12, 0.62, 1.0 - exp(-thickness * 0.65));
	ALPHA = max(ALPHA, fresnel * 0.65) * smoothstep(0.0, 0.18, thickness) * COLOR.a;
}
