// Dedicated convergence material. Layer: 0 = dash/halo, 1 = real-cm helix,
// 2 = lingering column. Ordinary orange tracers keep their V13 material.
float facing = saturate(abs(dot(normalize(NormalWS), normalize(ViewVector))));
float along = saturate(LocalPosition.z * 0.01 + 0.5);
float alpha = 0.0;
float energy = 1.0;
if (Layer < 0.5)
{
    float body = smoothstep(0.0, 0.35, along);
    float cap = smoothstep(0.46, 0.495, abs(LocalPosition.z) * 0.01);
    float radial = saturate(length(LocalPosition.xy) * 0.02);
    float disc = exp2(-5.0 * radial * radial) * (1.0 - smoothstep(0.65, 1.0, radial));
    alpha = body * (1.0 - cap) * pow(facing, 1.0) + cap * disc * along;
    energy = lerp(0.65, 1.0, along);
}
else if (Layer < 1.5)
{
    // Mesh is authored in real centimetres with its head at z=0. Reveal the
    // travelled part without stretching the tube or rebuilding its vertices.
    float fromTail = LocalPosition.z + LengthCM;
    float toHead = -LocalPosition.z;
    alpha = smoothstep(0.0, min(24.0, LengthCM * 0.2), fromTail)
          * smoothstep(0.0, min(12.0, LengthCM * 0.1), toHead)
          * pow(facing, 0.65);
}
else
{
    // Both end fades are measured in centimetres, never a fraction of a km.
    // A soft transverse profile replaces the old cylinder's constant alpha floor.
    float fromTail = along * LengthCM;
    float toHead = (1.0 - along) * LengthCM;
    float nearFade = smoothstep(0.0, min(NearFadeCM, LengthCM * 0.35), fromTail);
    float farFade = smoothstep(0.0, min(24.0, LengthCM * 0.15), toHead);
    alpha = nearFade * farFade * pow(facing, 1.15);
}
// Pure tint: no warm-white interpolation, noise, flicker or opaque end discs.
// Densify the spatial profile before temporal opacity so the final fade stays smooth.
return float4(Tint.rgb * Emission * energy / max(Exposure, 0.001), saturate(alpha * 1.35) * Opacity);
