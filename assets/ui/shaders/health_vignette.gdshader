shader_type canvas_item;
// 低血量边缘血雾（vignette）：屏幕边缘暗红，中心透明，intensity 控制强度
uniform float intensity : hint_range(0.0, 1.0) = 0.0;

void fragment() {
	vec2 uv = UV;
	vec2 d = abs(uv - vec2(0.5));
	float dist = max(d.x, d.y);
	float edge = smoothstep(0.25, 0.62, dist);
	vec3 col = vec3(0.72, 0.10, 0.06);
	COLOR = vec4(col, edge * intensity);
}
