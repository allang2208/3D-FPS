shader_type spatial;
render_mode unshaded, cull_disabled, skip_vertex_transform;
uniform sampler2D atlas : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
varying flat float atlas_view;

void vertex() {
	vec3 local_camera = (inverse(MODEL_MATRIX) * vec4(CAMERA_POSITION_WORLD, 1.0)).xyz;
	float angle = atan(local_camera.x, local_camera.z);
	atlas_view = mod(floor(angle * (8.0 / TAU) + 0.5) + 8.0, 8.0);
	vec3 origin = MODEL_MATRIX[3].xyz;
	vec3 toward_camera = CAMERA_POSITION_WORLD - origin;
	vec3 right = normalize(vec3(toward_camera.z, 0.0, -toward_camera.x));
	vec3 world = origin + right * VERTEX.x * length(MODEL_MATRIX[0].xyz)
		+ vec3(0.0, VERTEX.y * length(MODEL_MATRIX[1].xyz), 0.0);
	VERTEX = (VIEW_MATRIX * vec4(world, 1.0)).xyz;
}

void fragment() {
	vec4 color = texture(atlas, vec2((clamp(UV.x, 0.001, 0.999) + atlas_view) / 8.0, UV.y));
	ALBEDO = color.rgb;
	ALPHA = color.a;
	ALPHA_SCISSOR_THRESHOLD = 0.4;
}
