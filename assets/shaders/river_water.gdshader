shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, specular_schlick_ggx;

// Stream water surface: UV flow normal wobble + depth-tinted teal + fresnel
// highlight. Deeper/opaque colors + soft highlights keep it reading as water
// instead of washing out to white-green under the bright sky.
// Usage: MeshInstance3D + PlaneMesh with this shader; mesh sits at bed height.
uniform vec4 water_color : source_color = vec4(0.30, 0.58, 0.62, 0.34);
uniform vec4 deep_color : source_color = vec4(0.20, 0.42, 0.48, 0.46);
uniform float flow_speed : hint_range(0.0, 4.0) = 0.9;
uniform float wave_scale : hint_range(0.0, 4.0) = 1.0;
uniform float fresnel_power : hint_range(0.0, 8.0) = 3.2;
uniform float specular_strength : hint_range(0.0, 2.0) = 0.3;
uniform float refraction_strength : hint_range(0.0, 1.0) = 0.5;
uniform sampler2D screen_tex : hint_screen_texture, repeat_disable, filter_linear;

varying vec2 world_uv;

void vertex() {
	world_uv = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xz;
}

void fragment() {
	float t = TIME * flow_speed;
	// Two opposing flow wave layers to avoid a single repeating stripe.
	vec2 uv1 = world_uv * wave_scale + vec2(t, t * 0.6);
	vec2 uv2 = world_uv * wave_scale * 1.7 - vec2(t * 0.8, t * 0.4);
	float n1 = sin(uv1.x * 6.2831 + sin(uv1.y * 4.0) * 2.0);
	float n2 = cos(uv2.y * 5.0 + sin(uv2.x * 3.0) * 1.5);
	float wave = (n1 + n2) * 0.5;
	// Flow streaks along the river axis (X is the flow direction).
	float streak = sin(world_uv.x * 1.2 - t * 2.5) * 0.5 + 0.5;
	streak *= sin(world_uv.y * 6.0 + t) * 0.5 + 0.5;
	wave = wave * 0.6 + streak * 0.4;

	// Depth tint: looking straight down = shallow/clear, grazing = deeper.
	float ndv = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float depth = 1.0 - ndv;
	vec3 col = mix(water_color.rgb, deep_color.rgb, depth * 0.65 + wave * 0.12);

	// Screen-space refraction: sample the opaque scene (riverbed/pebbles)
	// behind the surface, distorted by the wave field. Strongest when
	// looking straight down, fades out at grazing angles.
	vec2 refr_uv = SCREEN_UV + vec2(n1, n2) * 0.0035 + vec2(wave * 0.004, -wave * 0.003);
	vec3 refracted = texture(screen_tex, refr_uv).rgb;
	col = mix(col, refracted, clamp(ndv * refraction_strength * 0.7, 0.0, 0.55));

	// Fresnel: grazing angles get a soft sky-light tint, not pure white.
	float fres = pow(1.0 - ndv, fresnel_power);
	col += vec3(0.22, 0.36, 0.42) * fres * 0.35;
	// Sparkle highlights riding the wave crests.
	col += vec3(0.9, 0.95, 1.0) * specular_strength * max(0.0, wave) * fres * 0.8;

	float alpha = mix(water_color.a, deep_color.a, depth * 0.5);
	alpha = clamp(alpha + fres * 0.15, 0.0, 1.0);
	alpha *= COLOR.a;  // 岸线软边：顶点色 alpha 在两岸渐隐
	ALBEDO = col;
	ALPHA = alpha;
	METALLIC = 0.0;
	ROUGHNESS = 0.18 + wave * 0.14;
	SPECULAR = 0.6;
}
