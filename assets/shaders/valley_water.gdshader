shader_type spatial;
render_mode blend_mix, cull_disabled;

uniform sampler2D scene_depth : hint_depth_texture, filter_nearest, repeat_disable;
varying vec2 world_xz;

void vertex() {
	world_xz = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xz;
}

void fragment() {
	float depth = texture(scene_depth, SCREEN_UV).r;
	vec4 bed = INV_PROJECTION_MATRIX * vec4(SCREEN_UV * 2.0 - 1.0, depth, 1.0);
	float thickness = max(0.0, VERTEX.z - bed.z / bed.w);
	float ripples = sin(world_xz.x * 2.4 + TIME * 0.8 + sin(world_xz.y * 1.7));
	float cross_wave = sin(world_xz.y * 3.2 - TIME * 0.6 + sin(world_xz.x * 0.9));
	vec3 normal_world = normalize(vec3(ripples * 0.035, 1.0, cross_wave * 0.025));
	NORMAL = normalize((VIEW_MATRIX * vec4(normal_world, 0.0)).xyz);
	float fresnel = pow(1.0 - max(dot(NORMAL, VIEW), 0.0), 4.0);
	ALBEDO = mix(vec3(0.075, 0.13, 0.12), vec3(0.34, 0.43, 0.46), fresnel);
	ROUGHNESS = 0.24;
	SPECULAR = 0.5;
	ALPHA = mix(0.18, 0.65, clamp(thickness / 2.5, 0.0, 1.0));
	ALPHA = max(ALPHA, fresnel * 0.65) * smoothstep(0.0, 0.18, thickness) * COLOR.a;
}
