shader_type spatial;
render_mode unshaded, blend_add, cull_front, depth_draw_never, fog_disabled;

uniform sampler2D galaxy_texture : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float night_visibility : hint_range(0.0, 1.0) = 0.0;
uniform float cloud_cover : hint_range(0.0, 1.0) = 0.0;
uniform float sidereal_rotation = 0.0;
uniform float galaxy_opacity : hint_range(0.0, 1.0) = 0.62;
uniform vec3 moon_direction = vec3(0.0, 1.0, 0.0);

varying vec3 sky_direction;

void vertex() {
	sky_direction = normalize((MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz - CAMERA_POSITION_WORLD);
}

void fragment() {
	vec2 panorama_uv = vec2(fract(UV.x + sidereal_rotation), clamp(UV.y, 0.0, 1.0));
	vec3 galaxy = texture(galaxy_texture, panorama_uv).rgb;
	// The source is a neutral photographic panorama. Keep its real structure,
	// deepen the long-exposure sky floor, and let the procedural atmosphere tint it.
	galaxy = max(galaxy - vec3(0.012), vec3(0.0));
	galaxy *= vec3(0.72, 0.82, 1.0);
	float horizon = smoothstep(0.015, 0.14, sky_direction.y);
	float cloud_transmission = mix(1.0, 0.08, smoothstep(0.12, 0.92, cloud_cover));
	float moon_wash = 1.0 - 0.52 * pow(max(dot(sky_direction, moon_direction), 0.0), 18.0);
	float visibility = night_visibility * cloud_transmission * horizon * moon_wash * galaxy_opacity;
	ALBEDO = galaxy;
	ALPHA = visibility;
}
