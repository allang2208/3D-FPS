// Keep the installed blade-space projection and all three existing rune masks.
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

float time = PreviewTime >= 0 ? PreviewTime : T;
float pulse;
if (RuneMode < .5)
    pulse = .88 + .12 * sin(time * 2.2 - along * .024);
else if (RuneMode < 1.5)
    pulse = .86 + .09 * sin(time * 3.6 + along * .17)
                  + .05 * sin(time * 8.4 - along * .08);
else
    pulse = .83 + .17 * pow(.5 + .5 * sin(along * .17 - time * 2.0), 3);

// A steady pearl-silver core stays visible at the dimmest point of the pulse.
// Only the ice-blue fluorescence breathes; the rune never pulses to black.
float coverage = saturate(core * RuneOpacity + halo * HaloOpacity);
float coreWeight = saturate(core / max(core + halo * HaloOpacity, .0001));
float3 coreColor = RuneBaseColor * BaseBrightness + RuneGlowColor * GlowStrength * pulse;
float3 haloColor = RuneGlowColor * GlowStrength * .55 * pulse;
return float4(lerp(haloColor, coreColor, coreWeight), coverage * inside);
