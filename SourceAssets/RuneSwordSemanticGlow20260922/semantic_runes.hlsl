// Existing blade-space projection and rune masks are preserved.
float3 axis = normalize(BladeAxis.xyz);
float3 offset = P.xyz - BladeOrigin.xyz;
float along = dot(offset, axis);
float3 widthAxis = cross(normalize(N.xyz), axis);
widthAxis *= rsqrt(max(dot(widthAxis, widthAxis), 0.0001));
float2 uv = float2(0.5 + dot(offset, widthAxis) / Dimensions.x,
                  1.0 - (along - Dimensions.y) / Dimensions.z);
float inside = step(0, uv.x) * step(uv.x, 1) * step(0, uv.y) * step(uv.y, 1);
inside *= 1 - smoothstep(Dimensions.x * .48, Dimensions.x * .56,
                        length(offset - along * axis));
inside *= step(-.5, RuneMode);
float2 artworkUV = float2(lerp(.30, .70, saturate(uv.x)), saturate(uv.y));

uint texWidth, texHeight;
RuneTexture.GetDimensions(texWidth, texHeight);
float2 haloStep = HaloRadiusTexels / max(float2(texWidth, texHeight), float2(1.0, 1.0));
float core = saturate(Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV).r * 1.2);
float halo = .25 * (
    Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV + float2(haloStep.x, 0)).r +
    Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV - float2(haloStep.x, 0)).r +
    Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV + float2(0, haloStep.y)).r +
    Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV - float2(0, haloStep.y)).r);

// GOLD-RUNE-V1: superseded by the complete semantic palette below.
// Keep variables declared before every branch; no source-text injection.
float time = PreviewTime >= 0 ? PreviewTime : T;
float pulse;
float3 baseTint;
float3 glowTint;
if (max(GoldenTint, step(2.5, RuneMode)) > .5)
{
    baseTint = GoldCoreColor;
    glowTint = GoldGlowColor;
    float phase = frac(time * .16);
    float edge = smoothstep(0.0, .06, phase) * (1.0 - smoothstep(.94, 1.0, phase));
    float wave = exp2(-pow(((1.0 - uv.y) - phase) / .085, 2.0) * 3.0) * edge;
    pulse = .78 + .07 * sin(time * 1.65) + .15 * wave;
}
else if (RuneMode < .5)
{
    baseTint = ResonanceCoreColor;
    glowTint = ResonanceGlowColor;
    // Broad, even breathing along the resonance rings.
    pulse = .80 + .20 * sin(time * 2.2 - along * .024);
}
else if (RuneMode < 1.5)
{
    baseTint = ErosionCoreColor;
    glowTint = ErosionGlowColor;
    // Offset bands flicker through the fissures, with a steady colored core.
    pulse = .68 + .20 * sin(time * 3.6 + along * .17)
                  + .12 * sin(time * 8.4 - along * .08);
}
else
{
    baseTint = ConductionCoreColor;
    glowTint = ConductionGlowColor;
    // Directed current moves from blade root toward the tip.
    pulse = .60 + .40 * pow(.5 + .5 * sin(along * .17 - time * 2.6), 3);
}

float coverage = saturate(core * RuneOpacity + halo * HaloOpacity);
float coreWeight = saturate(core / max(core + halo * HaloOpacity, .0001));
float3 coreColor = baseTint * BaseBrightness + glowTint * GlowStrength * pulse;
float3 haloColor = glowTint * GlowStrength * .65 * pulse;
float3 emission = lerp(haloColor, coreColor, coreWeight);
// Scale RGB together to retain hue instead of clipping channels to white.
float peak = max(emission.r, max(emission.g, emission.b));
emission *= min(1.0, EmissionPeak / max(peak, .0001));
return float4(emission, coverage * inside);
