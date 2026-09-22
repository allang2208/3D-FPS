// Keep the existing spirit composition and blade-space placement.
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
float2 haloStep = HaloRadiusTexels / max(float2(texWidth, texHeight), float2(1, 1));
float core = saturate(Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV).r * 1.2);
float halo = .25 * (
    Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV + float2(haloStep.x, 0)).r +
    Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV - float2(haloStep.x, 0)).r +
    Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV + float2(0, haloStep.y)).r +
    Texture2DSample(RuneTexture, RuneTextureSampler, artworkUV - float2(0, haloStep.y)).r);

// Soft ice-light beneath the crystal: rounded, fading echoes.
float time = PreviewTime >= 0 ? PreviewTime : T;
float lightBands = 0;
float softAura = 0;
float facets = 0;
float wake = 0;
float x = (uv.x - .5) * 2.55;
x += .012 * sin(uv.y * 49 + uv.x * 7);
[unroll]
for (int node = 0; node < 3; ++node)
{
    float y = (uv.y - (.18 + node * .30)) * 3.05;
    y += .010 * sin(uv.x * 21 + uv.y * 31);
    float crystalDistance = max(0, sqrt(x*x + .0049) + .92 * sqrt(y*y + .0049) - .1344);
    float phase = frac(time * BurstRate - node * .19);
    float life = smoothstep(.02, .24, phase) * (1 - smoothstep(.64, .98, phase));
    float charge = smoothstep(.02, .22, phase) * (1 - smoothstep(.28, .55, phase));
    float outline = exp2(-2 * pow((crystalDistance - .24) / EdgeSoftness, 2));
    float inner = exp2(-2 * pow(crystalDistance / .16, 2)) * charge;
    facets += inner * .55;
    lightBands += outline * life * .10;
    wake += exp2(-pow(crystalDistance / .58, 2)) * life;
    [unroll]
    for (int echo = 0; echo < 2; ++echo)
    {
        float progress = saturate((phase - .20 - echo * .10) / (.70 - echo * .05));
        float envelope = smoothstep(0, .22, progress) * (1 - smoothstep(.44, 1, progress));
        float radius = lerp(.18, .76, progress);
        float width = EdgeSoftness + .085 * progress;
        float distance = crystalDistance - radius;
        float strength = envelope * pow(1 - progress, .85) * (echo == 0 ? .65 : .42);
        float irregularity = .83 + .17 * sin(uv.y * 37 + uv.x * 19 + node * 1.7);
        lightBands += exp2(-1.7 * pow(distance / width, 2)) * strength * irregularity;
        softAura += exp2(-1.5 * pow(distance / (width * 2.2), 2)) * strength;
    }
}

float breath = smoothstep(.04, .96, .5 + .5 * sin(time * 1.07 - uv.y * 4.2));
float fracture = (core * .18 + halo * .82) * (.07 + .15 * breath + .12 * saturate(wake));
float body = fracture + lightBands + facets;
float aura = (softAura + halo * .05) * BurstHalo;
float coverage = (1 - exp2(-1.8 * (body + aura * .22))) * SpiritOpacity * (.72 + .28 * breath);
float innerWeight = saturate(facets / max(body, .0001)) * .50;
float3 tint = lerp(BurstColor, InnerColor, innerWeight);
tint = lerp(tint, AccentColor, .08 * saturate(aura / max(body + aura, .0001)));
float brightness = SpiritBrightness * (.62 + .38 * saturate(body)) * (.82 + .18 * breath);
float3 emission = tint * brightness;
float peak = max(emission.r, max(emission.g, emission.b));
emission *= min(1, 1.15 / max(peak, .0001));
float edgeFade = smoothstep(0, .09, uv.x) * (1 - smoothstep(.91, 1, uv.x));
float endFade = smoothstep(.02, .12, uv.y) * (1 - smoothstep(.87, .985, uv.y));
return float4(emission, coverage * RuneOpacity * inside * edgeFade * endFade);
