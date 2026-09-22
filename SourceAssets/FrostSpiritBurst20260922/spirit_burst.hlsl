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

// Three amethyst nodes: charge, paired expanding diamond waves, then settle.
float time = PreviewTime >= 0 ? PreviewTime : T;
float nodeIndex = floor(uv.y * 3.0);
float y = frac(uv.y * 3.0) - .5;
float x = (uv.x - .5) * 2.8;
float diamond = abs(x) + abs(y) * 1.35;
float phase = frac(time * BurstRate - nodeIndex * .10);
float charge = smoothstep(.0, .28, phase) * (1.0 - smoothstep(.30, .60, phase));
float release = smoothstep(.24, .35, phase) * (1.0 - smoothstep(.75, 1.0, phase));
float radius = lerp(.24, .82, smoothstep(.28, .96, phase));
float outlineDistance = abs(diamond - .24);
float waveDistance = min(abs(diamond - radius), abs(diamond - max(.24, radius - .16)));
float nodeLine = 1.0 - smoothstep(.014, .032, outlineDistance);
float waveLine = (1.0 - smoothstep(.014, .032, waveDistance)) * release;
float nodeHalo = 1.0 - smoothstep(.030, .085, outlineDistance);
float waveHalo = (1.0 - smoothstep(.030, .095, waveDistance)) * release;
float facet = (1.0 - smoothstep(.02, .15, diamond)) * (.35 + .65 * charge);
float fracture = core * (.42 + .36 * charge + .22 * release);
float glyph = max(fracture, max(nodeLine, max(waveLine, facet)));
float aura = max(halo * .4, max(nodeHalo, waveHalo)) * BurstHalo;
float weight = saturate(glyph / max(glyph + aura * .25, .0001));
float3 violet = BurstColor * (BaseBrightness + GlowStrength * (.65 + .35 * charge));
float3 center = lerp(violet, InnerColor * 1.3, saturate(facet * .45));
float3 emission = lerp(BurstColor * (.65 + .35 * release), center, weight);
float peak = max(emission.r, max(emission.g, emission.b));
emission *= min(1.0, 1.7 / max(peak, .0001));
float endFade = smoothstep(.015, .065, uv.y) * (1.0 - smoothstep(.94, .985, uv.y));
return float4(emission, saturate(glyph * RuneOpacity + aura * .25) * inside * endFade);
