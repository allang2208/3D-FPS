shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;
uniform sampler2D coating_albedo : source_color, filter_linear_mipmap, repeat_enable;
uniform bool region_mask = false;
void fragment() {
    float polymer = region_mask ? COLOR.r : 0.0;
    // The user's selected reference is clean, smooth coated metal, not worn cast metal.
    float grain = texture(coating_albedo, UV * 3.0).r;
    float variation = clamp((grain - 0.035) * 0.35, -0.012, 0.012);
    vec3 coat = vec3(0.14,0.145,0.15);
    vec3 plastic = vec3(0.065,0.067,0.069);
    ALBEDO = mix(coat,plastic,polymer) * (1.0 + variation);
    if (!OUTPUT_IS_SRGB) {
        ALBEDO = mix(pow((ALBEDO+vec3(0.055))/1.055,vec3(2.4)),ALBEDO/12.92,lessThanEqual(ALBEDO,vec3(0.04045)));
    }
    ROUGHNESS = mix(0.36,0.74,polymer) + variation;
    METALLIC = mix(0.38,0.0,polymer);
    SPECULAR = mix(0.42,0.26,polymer);
    // Preserve the actual model's normals. No generated bumps or edge-wear overlay.
}
