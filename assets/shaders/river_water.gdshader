shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, specular_schlick_ggx;

// Stream water: transparent teal ribbon + screen-space reflections + depth
// refraction. SSR ray-march adapted from marcelb/GodotSSRWater (MIT): it
// solves Godot's limitation where SSR only works on opaque surfaces, so the
// transparent stream can still mirror the sky and banks like the reference.
// Vertex color alpha keeps the soft shore fade (1 = open water, 0 = bank).

uniform vec4 water_color : source_color = vec4(0.20, 0.60, 0.66, 0.24);
uniform vec4 deep_color : source_color = vec4(0.12, 0.45, 0.52, 0.40);
uniform float flow_speed : hint_range(0.0, 4.0) = 0.9;
uniform float wave_scale : hint_range(0.0, 4.0) = 1.0;
uniform float fresnel_power : hint_range(0.0, 8.0) = 3.2;
uniform float specular_strength : hint_range(0.0, 2.0) = 0.20;
uniform float refraction_strength : hint_range(0.0, 1.0) = 0.5;
uniform float foam_strength : hint_range(0.0, 1.0) = 0.40;
uniform float max_visible_depth : hint_range(0.1, 30.0) = 6.0;
uniform float ssr_resolution : hint_range(0.05, 4.0) = 0.7;
uniform float ssr_max_travel : hint_range(0.0, 80.0) = 32.0;
uniform float ssr_max_diff : hint_range(0.1, 10.0) = 3.0;
uniform float ssr_mix_strength : hint_range(0.0, 1.0) = 0.6;
uniform float ssr_screen_border_fadeout : hint_range(0.0, 1.0) = 0.3;
uniform sampler2D screen_tex : hint_screen_texture, repeat_disable, filter_linear;
uniform sampler2D depth_tex : hint_depth_texture, repeat_disable, filter_nearest;

varying vec2 world_uv;

const float EPSILON = 1e-5;

void vertex() {
	world_uv = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xz;
}

// Analytic flow field: two opposing wave layers + stream streaks along X.
float flow_value(vec2 wuv) {
	float t = TIME * flow_speed;
	vec2 uv1 = wuv * wave_scale + vec2(t, t * 0.6);
	vec2 uv2 = wuv * wave_scale * 1.7 - vec2(t * 0.8, t * 0.4);
	float n1 = sin(uv1.x * 6.2831 + sin(uv1.y * 4.0) * 2.0);
	float n2 = cos(uv2.y * 5.0 + sin(uv2.x * 3.0) * 1.5);
	float wave = (n1 + n2) * 0.5;
	float streak = sin(wuv.x * 1.2 - t * 2.5) * 0.5 + 0.5;
	streak *= sin(wuv.y * 6.0 + t) * 0.5 + 0.5;
	return wave * 0.6 + streak * 0.4;
}

bool is_within_screen_boundaries(vec2 position) {
	return position.x > 0.0 && position.x < 1.0 && position.y > 0.0 && position.y < 1.0;
}

vec2 get_uv_from_view_position(vec3 position_view_space, mat4 proj_m) {
	vec4 position_clip_space = proj_m * vec4(position_view_space.xyz, 1.0);
	vec2 position_ndc = position_clip_space.xy / position_clip_space.w;
	return position_ndc.xy * 0.5 + 0.5;
}

vec3 get_view_position_from_uv(vec2 uv, float depth, mat4 inv_proj_m) {
	vec4 position_ndc = vec4((uv * 2.0) - 1.0, depth, 1.0);
	vec4 view_position = inv_proj_m * position_ndc;
	return view_position.xyz /= view_position.w;
}

bool is_zero(float value) {
	return abs(value) < EPSILON;
}

float get_screen_border_alpha(vec2 screen_position) {
	vec2 shifted = 4.0 * screen_position * (1.0 - screen_position);
	float mask = shifted.x * shifted.y;
	float offset = mix(0.0, 0.5, (clamp(ssr_screen_border_fadeout, 0.75, 1.0) - 0.75) / 0.25);
	float alpha = clamp(smoothstep(0.0, 2.0 * ssr_screen_border_fadeout, mask) - offset, 0.0, 1.0);
	return is_zero(ssr_screen_border_fadeout) ? 1.0 : alpha;
}

// Ray-march the reflected view ray against the opaque depth buffer, returning
// the reflected scene color plus a border-fade alpha.
vec4 get_ssr_color(vec3 surface_view_position, vec3 normal_view_space,
		vec3 view_view_space, mat4 proj_m, mat4 inv_proj_m) {
	if (ssr_max_travel < EPSILON) {
		return vec4(0.0);
	}
	vec3 current_position_view_space = surface_view_position;
	vec3 view_direction_view_space = view_view_space * -1.0;
	vec3 reflect_vector_view_space = normalize(reflect(view_direction_view_space.xyz, normal_view_space.xyz));
	vec2 current_screen_position = vec2(0.0);
	vec3 resulting_color = vec3(-1.0);
	for (float travel = 0.0; resulting_color.x < 0.0 && travel < ssr_max_travel;
			travel += ssr_resolution) {
		current_position_view_space += reflect_vector_view_space * ssr_resolution;
		current_screen_position = get_uv_from_view_position(current_position_view_space, proj_m);
		float depth_probe_raw = texture(depth_tex, current_screen_position).x;
		vec3 depth_probe_view_position = get_view_position_from_uv(current_screen_position, depth_probe_raw, inv_proj_m);
		float depth_diff = depth_probe_view_position.z - current_position_view_space.z;
		vec3 ssr_screen_color = texture(screen_tex, current_screen_position.xy).rgb;
		resulting_color = (is_within_screen_boundaries(current_screen_position)
			&& depth_diff >= 0.0 && depth_diff < ssr_max_diff) ? ssr_screen_color : vec3(-1.0);
	}
	float alpha = get_screen_border_alpha(current_screen_position);
	return vec4(resulting_color, alpha);
}

vec2 get_refracted_uv(vec2 raw_screen_uv, float screen_depth_raw,
		vec3 view, vec3 normal, mat4 proj_m, mat4 inv_proj_m) {
	vec3 screen_view_position_original = get_view_position_from_uv(raw_screen_uv, screen_depth_raw, inv_proj_m);
	float screen_center_distance = clamp(abs(length(raw_screen_uv - vec2(0.5, 0.5))) * 2.0, 0.0, 1.0);
	float refraction_intensity_deglitched = mix(1.0 - refraction_strength, 1.0, screen_center_distance);
	vec3 refraction_position_view_space = screen_view_position_original
		+ normalize(refract(view, -normal, refraction_intensity_deglitched));
	return get_uv_from_view_position(refraction_position_view_space, proj_m);
}

void fragment() {
	float wave = flow_value(world_uv);

	// Perturbed view-space normal from analytic wave derivatives.
	vec2 e = vec2(0.05, 0.0);
	float hx = flow_value(world_uv - e) - flow_value(world_uv + e);
	float hz = flow_value(world_uv - e.yx) - flow_value(world_uv + e.yx);
	vec3 normal = normalize(vec3(NORMAL.xy + vec2(hx, hz) * 0.18, NORMAL.z));

	float ndv = clamp(dot(normal, VIEW), 0.0, 1.0);
	float depth_ratio = 1.0 - ndv;
	vec3 col = mix(water_color.rgb, deep_color.rgb, depth_ratio * 0.65 + wave * 0.12);

	// Depth-based refraction offset for the probes below.
	float screen_depth_raw = texture(depth_tex, SCREEN_UV).x;
	vec2 refraction_uv = refraction_strength > 0.0
		? get_refracted_uv(SCREEN_UV, screen_depth_raw, VIEW, normal, PROJECTION_MATRIX, INV_PROJECTION_MATRIX)
		: SCREEN_UV;
	// Refracted background copy: a distorted "see-through" layer on top of the
	// alpha blend, so submerged stones shimmer instead of staying static.
	vec3 refracted = texture(screen_tex, refraction_uv).rgb;
	col = mix(col, refracted, clamp(ndv * refraction_strength * 0.22, 0.0, 0.22));

	// SSR: mirror sky/banks on the transparent surface.
	float surface_depth = FRAGCOORD.z;
	vec3 surface_view_position = get_view_position_from_uv(SCREEN_UV, surface_depth, INV_PROJECTION_MATRIX);
	vec4 ssr_color = get_ssr_color(surface_view_position, normal, VIEW, PROJECTION_MATRIX, INV_PROJECTION_MATRIX);
	if (ssr_color.r >= 0.0) {
		col = mix(col, ssr_color.rgb, ssr_mix_strength * ssr_color.a);
	}

	// Fresnel sky tint + sparkle highlights riding wave crests.
	float fres = pow(1.0 - ndv, fresnel_power);
	col += vec3(0.38, 0.62, 0.85) * fres * 0.55;
	col += vec3(0.9, 0.95, 1.0) * specular_strength * max(0.0, wave) * fres * 0.8;

	// Bank foam: white lace where the shore fade meets open water.
	float shore = 1.0 - COLOR.a;
	float foam = smoothstep(0.42, 0.62, shore) * (0.35 + 0.65 * max(0.0, wave));
	foam *= 0.65 + 0.35 * sin(world_uv.x * 3.0 + world_uv.y * 5.0 + TIME * 2.0);
	// Wave-crest foam speckles on open water.
	float crest = smoothstep(0.62, 0.95, wave);
	foam = max(foam, crest * 0.16 * (1.0 - shore * 0.5));
	col = mix(col, vec3(0.92, 0.95, 0.97), clamp(foam * foam_strength, 0.0, 1.0));

	// Alpha: shallow = clearer (see the bed), grazing = more opaque, then
	// multiply by the vertex-color shore fade.
	float alpha = mix(water_color.a, deep_color.a, depth_ratio * 0.5);
	alpha = clamp(alpha + fres * 0.15, 0.0, 1.0);
	alpha = clamp(alpha + foam * 0.14, 0.0, 1.0);
	alpha *= COLOR.a;

	ALBEDO = col;
	ALPHA = alpha;
	METALLIC = 0.0;
	ROUGHNESS = 0.18 + wave * 0.14;
	SPECULAR = 0.6;
	NORMAL = normal;
}
