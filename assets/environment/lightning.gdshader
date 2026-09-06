shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, fog_disabled;
uniform float brightness = 0.0;
uniform float reveal = 1.0;
void fragment() {
    float edge = abs(UV.x * 2.0 - 1.0);
    float core = exp(-edge * edge * 170.0);
    float halo = pow(max(0.0, 1.0 - edge), 3.0) * 0.22;
    float growth = 1.0 - smoothstep(reveal - 0.035, reveal, UV.y);
    ALBEDO = mix(vec3(0.38, 0.55, 1.0), vec3(0.87, 0.93, 1.0), core);
    ALPHA = (core + halo) * brightness * COLOR.a * growth;
}
