shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx, cull_disabled;
uniform sampler2D finish_texture : source_color, filter_linear_mipmap, repeat_enable;
uniform vec4 tint : source_color = vec4(0.22, 0.235, 0.245, 1.0);
uniform float finish_strength = 0.22;
uniform float surface_roughness = 0.66;
uniform float surface_metallic = 0.16;
uniform float surface_specular = 0.25;
uniform bool stock_micro_enabled = false;
uniform float stock_micro_depth = 0.45;
uniform sampler2D stock_micro_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D stock_micro_roughness : filter_linear_mipmap, repeat_enable;
void fragment() {
	float finish = texture(finish_texture, UV * 4.0).r;
	float variation = clamp(finish / 0.035, 0.7, 1.3);
	ALBEDO = tint.rgb * mix(1.0, variation, finish_strength);
	ROUGHNESS = clamp(surface_roughness - (variation - 1.0) * 0.06 * clamp(finish_strength / 0.22, 0.0, 1.0), 0.0, 1.0);
	METALLIC = surface_metallic;
	SPECULAR = surface_specular;
	if (stock_micro_enabled) {
		vec2 detail_uv = UV * 4.0;
		NORMAL_MAP = texture(stock_micro_normal, detail_uv).rgb;
		NORMAL_MAP_DEPTH = stock_micro_depth;
		ALBEDO *= 0.94 + texture(stock_micro_roughness, detail_uv).r * 0.12;
		ROUGHNESS = clamp(ROUGHNESS + (texture(stock_micro_roughness, detail_uv).r - 0.5) * 0.12, 0.0, 1.0);
	}
}
