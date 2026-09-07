shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, specular_schlick_ggx;

// Clear shallow wilderness water. One screen-color lookup provides refraction;
// analytic waves avoid texture bandwidth and expensive SSR ray marching.
uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap, repeat_disable;
uniform sampler2D scene_depth : hint_depth_texture, filter_nearest, repeat_disable;
uniform vec4 shallow_color : source_color = vec4(0.055, 0.32, 0.36, 0.34);
uniform vec4 deep_color : source_color = vec4(0.025, 0.13, 0.19, 0.72);
uniform vec4 foam_color : source_color = vec4(0.90, 0.95, 0.94, 1.0);
uniform float flow_speed : hint_range(0.0, 2.0, 0.01) = 0.32;
uniform float refraction_strength : hint_range(0.0, 0.05, 0.001) = 0.012;
uniform float foam_strength : hint_range(0.0, 1.0, 0.01) = 0.72;
uniform float max_visible_depth : hint_range(0.2, 8.0, 0.1) = 2.8;

varying vec2 world_xz;

float water_hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float water_noise(vec2 p) {
	vec2 cell = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(water_hash(cell), water_hash(cell + vec2(1.0, 0.0)), f.x),
		mix(water_hash(cell + vec2(0.0, 1.0)), water_hash(cell + vec2(1.0)), f.x), f.y);
}

float wave_field(vec2 p) {
	float t = TIME * flow_speed;
	float broad = water_noise(p * 0.72 + vec2(-t, t * 0.18));
	vec2 crossed = mat2(vec2(0.80, 0.60), vec2(-0.60, 0.80)) * p;
	float fine = water_noise(crossed * 1.85 + vec2(t * 0.42, -t * 0.28));
	return broad * 0.62 + fine * 0.38;
}

void vertex() {
	world_xz = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xz;
}

void fragment() {
	float raw_depth = texture(scene_depth, SCREEN_UV).r;
	vec4 bed_h = INV_PROJECTION_MATRIX * vec4(SCREEN_UV * 2.0 - 1.0, raw_depth, 1.0);
	float safe_w = abs(bed_h.w) > 0.0001 ? bed_h.w : -0.0001;
	vec3 bed_view = bed_h.xyz / safe_w;
	float thickness = max(0.0, VERTEX.z - bed_view.z);
	float depth_ratio = clamp(thickness / max_visible_depth, 0.0, 1.0);

	vec2 wave_uv = world_xz * 0.72;
	float wave = wave_field(wave_uv);
	vec2 eps = vec2(0.055, 0.0);
	float dx = wave_field(wave_uv + eps) - wave_field(wave_uv - eps);
	float dz = wave_field(wave_uv + eps.yx) - wave_field(wave_uv - eps.yx);
	vec3 normal_world = normalize(vec3(-dx * 0.42, 1.0, -dz * 0.36));
	vec3 normal_view = normalize((VIEW_MATRIX * vec4(normal_world, 0.0)).xyz);
	NORMAL = normal_view;

	// A single distorted screen sample keeps the white pebbles visible and moving.
	vec2 refracted_uv = clamp(SCREEN_UV + normal_view.xy * refraction_strength
		* smoothstep(0.04, 0.65, thickness), vec2(0.002), vec2(0.998));
	vec3 refracted = textureLod(screen_texture, refracted_uv, depth_ratio * 1.2).rgb;
	vec3 absorption = mix(shallow_color.rgb, deep_color.rgb, depth_ratio);
	vec3 water_color = mix(refracted, absorption, 0.34 + depth_ratio * 0.42);

	float ndv = clamp(dot(normal_view, VIEW), 0.0, 1.0);
	float fresnel = pow(1.0 - ndv, 3.4);
	water_color = mix(water_color, vec3(0.42, 0.68, 0.82), fresnel * 0.58);

	// Vertex alpha marks the bank fade; shallow depth adds contact foam around stones.
	float shore = 1.0 - COLOR.a;
	float shore_foam = smoothstep(0.08, 0.48, shore) * (1.0 - smoothstep(0.76, 1.0, shore));
	float contact_foam = (1.0 - smoothstep(0.05, 0.30, thickness))
		* smoothstep(0.10, 0.62, shore) * (1.0 - smoothstep(0.82, 1.0, shore));
	float crest = smoothstep(0.69, 0.88, wave) * (0.30 + fresnel * 0.70);
	float foam = clamp(max(shore_foam, contact_foam) + crest * 0.22, 0.0, 1.0) * foam_strength;
	foam *= 0.78 + 0.22 * water_noise(world_xz * 2.4 + vec2(TIME * 0.24, 0.0));
	water_color = mix(water_color, foam_color.rgb, foam);

	ALBEDO = water_color;
	ROUGHNESS = mix(0.10, 0.24, wave) + foam * 0.24;
	SPECULAR = 0.72;
	METALLIC = 0.0;
	float base_alpha = mix(shallow_color.a, deep_color.a, depth_ratio);
	// Vertex alpha already provides a geometry-stable bank fade. Do not gate the
	// whole surface on reconstructed thickness: grazing cameras and depth prepass
	// precision could otherwise erase an otherwise valid shallow stream.
	ALPHA = clamp(max(base_alpha * COLOR.a + fresnel * 0.20, foam * 0.68), 0.0, 0.88);
}
