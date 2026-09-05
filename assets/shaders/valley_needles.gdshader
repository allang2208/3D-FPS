shader_type spatial;
render_mode cull_disabled;
uniform sampler2D albedo_texture : source_color, filter_linear_mipmap_anisotropic;
uniform sampler2D alpha_texture : filter_linear_mipmap_anisotropic;
void fragment() {
	ALBEDO = texture(albedo_texture, UV).rgb * COLOR.rgb;
	ALPHA = texture(alpha_texture, UV).r;
	ALPHA_SCISSOR_THRESHOLD = 0.38;
	ROUGHNESS = 0.92;
	SPECULAR = 0.08;
	BACKLIGHT = vec3(0.12, 0.16, 0.07);
}
