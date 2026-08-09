shader_type canvas_item;
// 背包面板毛玻璃背景（复刻旧版 CSS backdrop-filter: blur(12px)）
// 用法：ColorRect 铺满面板，挂本 shader，颜色走 COLOR 输出（半透明暗色 + 高斯模糊采样）

uniform sampler2D screen_texture : hint_screen_texture, repeat_disable, filter_linear;
uniform float radius : hint_range(0.0, 32.0) = 9.0;
uniform vec3 tint_color : source_color = vec3(0.02, 0.025, 0.04);
uniform float tint_amount = 0.18;
uniform float alpha = 0.52;

const int TAPS = 4;

void fragment() {
	vec2 ps = 1.0 / vec2(textureSize(screen_texture, 0));
	vec3 acc = vec3(0.0);
	float wsum = 0.0;
	for (int y = -TAPS; y <= TAPS; y++) {
		for (int x = -TAPS; x <= TAPS; x++) {
			float d = float(x * x + y * y);
			float w = exp(-d / (radius * radius * 0.55));
			vec2 uv = SCREEN_UV + vec2(float(x), float(y)) * ps * radius * 0.45;
			acc += texture(screen_texture, uv).rgb * w;
			wsum += w;
		}
	}
	vec3 blurred = acc / wsum;
	vec3 tinted = mix(blurred, tint_color, tint_amount);
	COLOR = vec4(tinted, alpha);
}
