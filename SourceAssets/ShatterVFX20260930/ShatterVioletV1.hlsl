// LocalPosition is pre-skinned mesh position, interpolated explicitly so every
// ISM slot has its own 100 cm authoring space. Layer: core / halo / flash / crystal.
float facing = saturate(abs(dot(normalize(NormalWS), normalize(ViewVector))));
float3 color = Tint.rgb;
float alpha = 0.0;
float energy = 1.0;
if (Layer < 1.5)
{
    float along = saturate(LocalPosition.z * 0.01 + 0.5);
    float edge = max(0.006, min(0.15, 3.0 / max(LengthCM, 1.0)));
    float ends = smoothstep(0.0, edge, along) * smoothstep(0.0, edge, 1.0 - along);
    alpha = ends * pow(facing, Layer < 0.5 ? 0.8 : 1.65);
    energy = lerp(0.58, 1.0, along);
    if (Layer < 0.5)
        color = lerp(Tint.rgb, float3(0.78, 0.53, 1.0), pow(facing, 7.0) * 0.72);
}
else if (Layer < 2.5)
{
    float2 p = LocalPosition.xy * 0.02;
    float r = length(p);
    float edge = 1.0 - smoothstep(0.65, 1.0, r);
    float glow = exp2(-8.5 * r * r) * edge;
    float rayX = exp2(-95.0 * abs(p.y) - 5.0 * abs(p.x));
    float rayY = exp2(-105.0 * abs(p.x) - 8.0 * abs(p.y));
    float diamond = exp2(-42.0 * abs(abs(p.x) - abs(p.y)) - 9.0 * r);
    float peak = exp2(-Age * 32.0);
    alpha = saturate(glow * 0.62 + (rayX + rayY + diamond * 0.28) * peak) * edge;
    color = lerp(Tint.rgb, float3(0.88, 0.7, 1.0), exp2(-r * r * 34.0) * peak);
}
else
{
    // Hard geometry and per-face normal provide crystal facets, without a texture.
    float facet = saturate(dot(normalize(NormalWS), normalize(float3(0.35, -0.2, 0.92))) * 0.5 + 0.5);
    color = lerp(Tint.rgb * 0.62, float3(0.76, 0.47, 1.0), facet * facet * 0.8);
    energy = lerp(0.62, 1.12, facet);
    alpha = 0.88;
}
return float4(color * Emission * energy / max(Exposure, 0.001), saturate(alpha * Opacity));
