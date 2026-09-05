shader_type spatial;
render_mode cull_disabled;
uniform vec3 layer_tint : source_color = vec3(0.8, 0.87, 0.9);
varying vec3 world_position;
varying vec3 world_normal;
void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
}
void fragment() {
	float slope = 1.0 - abs(normalize(world_normal).y);
	float strata = 0.5 + 0.5 * sin(world_position.y * 0.16 + sin(world_position.z * 0.04) * 2.0);
	vec3 earth = mix(vec3(0.18, 0.23, 0.16), vec3(0.32, 0.34, 0.33), smoothstep(0.2, 0.65, slope));
	ALBEDO = earth * layer_tint * mix(0.8, 1.05, strata);
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
}
