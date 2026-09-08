shader_type canvas_item;
uniform sampler2D screen_texture : hint_screen_texture, repeat_disable, filter_linear_mipmap;
uniform vec2 node_size = vec2(600.0, 900.0);
uniform float corner_radius = 26.0;
uniform float blur_radius = 7.0;
uniform float blur_lod = 3.5;
uniform float refraction_px = 1.5;
uniform float surface_alpha = 0.96;
uniform vec3 tint : source_color = vec3(0.10, 0.16, 0.28);
uniform float tint_strength = 0.64;
void fragment() {
    vec2 p = (UV - 0.5) * node_size;
    vec2 q = abs(p) - node_size * 0.5 + corner_radius;
    float dist = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - corner_radius;
    float mask = 1.0 - smoothstep(-0.8, 0.8, dist);
    vec2 normal = normalize(p / max(node_size, vec2(1.0)) + vec2(0.0001));
    float rim = exp(-abs(dist) / 7.0);
    vec2 uv = SCREEN_UV + normal * SCREEN_PIXEL_SIZE * rim * refraction_px;
    // Mip-filtered blur avoids separated ghost images from sparse full-res taps.
    vec3 c = textureLod(screen_texture, uv, blur_lod).rgb;
    c = mix(c, tint, tint_strength);
    float edge = 1.0 - smoothstep(0.5, 1.8, abs(dist + 1.0));
    float light = 0.10 + 0.24 * clamp(0.5 - normal.y * 0.5 - normal.x * 0.2, 0.0, 1.0);
    c += vec3(0.66, 0.80, 1.0) * (edge * light + rim * 0.024);
    COLOR = vec4(c, mask * surface_alpha);
}
