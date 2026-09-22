// Retain each rune's authored mask, palette and blade-space placement.
float3 axis = normalize(BladeAxis.xyz);
float3 offset = P.xyz - BladeOrigin.xyz;
float along = dot(offset, axis);
float3 widthAxis = cross(normalize(N.xyz), axis);
widthAxis *= rsqrt(max(dot(widthAxis, widthAxis), .0001));
float2 uv = float2(.5 + dot(offset, widthAxis) / Dimensions.x,
                  1.0 - (along - Dimensions.y) / Dimensions.z);
float inside = smoothstep(0, .018, uv.x) * (1 - smoothstep(.982, 1, uv.x));
inside *= smoothstep(0, .018, uv.y) * (1 - smoothstep(.982, 1, uv.y));
inside *= 1 - smoothstep(Dimensions.x * .48, Dimensions.x * .56,
                        length(offset - along * axis));
inside *= step(-.5, RuneMode);
float2 artworkUV = float2(lerp(.30, .70, saturate(uv.x)), saturate(uv.y));

uint texWidth, texHeight;
RuneTexture.GetDimensions(texWidth, texHeight);
float2 texel = HaloRadiusTexels / max(float2(texWidth, texHeight), float2(1, 1));
float ink = Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV).r;
float nearHalo = .25 * (
    Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV + float2(texel.x, 0)).r +
    Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV - float2(texel.x, 0)).r +
    Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV + float2(0, texel.y)).r +
    Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV - float2(0, texel.y)).r);
float farHalo = .25 * (
    Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV + texel * 2.6).r +
    Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV - texel * 2.6).r +
    Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV + texel * float2(2.6, -2.6)).r +
    Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV + texel * float2(-2.6, 2.6)).r);
// A narrow feather retains the glyph; the wider halo loses coverage as it fades.
float core = saturate(ink * .86 + nearHalo * .14);
float halo = saturate(nearHalo * .72 + farHalo * .28);
float time = PreviewTime >= 0 ? PreviewTime : T;
float breath;
float3 baseTint;
float3 glowTint;
if (max(GoldenTint, step(2.5, RuneMode)) > .5)
{
    baseTint = GoldCoreColor;
    glowTint = GoldGlowColor;
    breath = .5 + .5 * sin(time * 1.12 - along * .028);
}
else if (RuneMode < .5)
{
    baseTint = ResonanceCoreColor;
    glowTint = ResonanceGlowColor;
    // Slow resonance with a small length offset, never a whole-blade flash.
    breath = .5 + .5 * sin(time * 1.16 - along * .032);
}
else if (RuneMode < 1.5)
{
    baseTint = ErosionCoreColor;
    glowTint = ErosionGlowColor;
    // Uneven fissures wake gently; no rapid flicker or scrolling geometry.
    breath = .5 + .5 * sin(time * 1.32 + along * .065 + .65 * sin(along * .09));
}
else
{
    baseTint = ConductionCoreColor;
    glowTint = ConductionGlowColor;
    // A broad blue current travels from hilt to tip and dissolves behind it.
    breath = .5 + .5 * sin(along * .095 - time * 1.45);
}
float life = smoothstep(.04, .96, breath);
float haloLife = smoothstep(.02, .98, .5 + .5 * sin(time * .91 - along * .04));
float pulse = lerp(.52, .88, life);
float coreCoverage = core * RuneOpacity * lerp(.48, .95, life);
float haloCoverage = halo * HaloOpacity * lerp(.30, .82, life) * (.78 + .22 * haloLife);
float coverage = saturate(coreCoverage + haloCoverage);
float coreWeight = saturate(coreCoverage / max(coreCoverage + haloCoverage, .0001));
float3 coreColor = baseTint * BaseBrightness * (.76 + .24 * life) + glowTint * GlowStrength * pulse;
float3 haloColor = glowTint * GlowStrength * .40 * pulse;
float3 emission = lerp(haloColor, coreColor, coreWeight);
float peak = max(emission.r, max(emission.g, emission.b));
emission *= min(1.0, EmissionPeak / max(peak, .0001));
return float4(emission, coverage * inside);
