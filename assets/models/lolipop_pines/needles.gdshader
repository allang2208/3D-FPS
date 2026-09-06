shader_type spatial;
render_mode cull_disabled;
uniform sampler2D albedo_texture : source_color, filter_linear_mipmap_anisotropic;
uniform sampler2D opacity_texture : filter_linear_mipmap;
uniform sampler2D normal_texture : hint_normal, filter_linear_mipmap_anisotropic;
void fragment() {
	ALBEDO = texture(albedo_texture, UV).rgb * vec3(0.72, 0.82, 0.66);
	ALPHA = texture(opacity_texture, UV).r;
	ALPHA_SCISSOR_THRESHOLD = 0.4;
	NORMAL_MAP = texture(normal_texture, UV).rgb;
	ROUGHNESS = 0.92;
	SPECULAR = 0.08;
	BACKLIGHT = ALBEDO * 0.15;
}
