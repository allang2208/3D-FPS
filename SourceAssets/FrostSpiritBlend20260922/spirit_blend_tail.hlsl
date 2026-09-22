// Soft ice-light beneath the crystal: no hard cell seams or permanent outlines.
float time = PreviewTime >= 0 ? PreviewTime : T;
float lightBands = 0.0;
float softAura = 0.0;
float facets = 0.0;
float wake = 0.0;
float x = (uv.x - .5) * 2.55;
// Static, gentle irregularity follows the blade rather than swimming over it.
x += .012 * sin(uv.y * 49.0 + uv.x * 7.0);
[unroll]
for (int node = 0; node < 3; ++node)
{
    float y = (uv.y - (.18 + node * .30)) * 3.05;
    y += .010 * sin(uv.x * 21.0 + uv.y * 31.0);
    // Smooth absolute values round the diamond's four corners.
    float crystalDistance = max(0.0, sqrt(x*x + .0049) + .92 * sqrt(y*y + .0049) - .1344);
    float phase = frac(time * BurstRate - node * .19);
    // Both ends approach zero before phase wraps; brightness and opacity fade together.
    float life = smoothstep(.02, .20, phase) * (1.0 - smoothstep(.70, .98, phase));
    float charge = smoothstep(.02, .22, phase) * (1.0 - smoothstep(.28, .55, phase));
    float outline = exp2(-2.0 * pow((crystalDistance - .24) / EdgeSoftness, 2.0));
    float inner = exp2(-2.0 * pow(crystalDistance / .16, 2.0)) * charge;
    facets += inner * .55;
    lightBands += outline * life * .13;
    wake += exp2(-pow(crystalDistance / .58, 2.0)) * life;
    [unroll]
    for (int echo = 0; echo < 2; ++echo)
    {
        float progress = saturate((phase - .20 - echo * .10) / (.70 - echo * .05));
        float envelope = smoothstep(.0, .18, progress) * (1.0 - smoothstep(.48, 1.0, progress));
        float radius = lerp(.18, .76, progress);
        float width = EdgeSoftness + .075 * progress;
        float distance = crystalDistance - radius;
        // Expansion broadens the band and reduces its coverage rather than drawing a sharp line.
        float strength = envelope * pow(1.0 - progress, .85) * (echo == 0 ? .65 : .42);
        float irregularity = .83 + .17 * sin(uv.y * 37.0 + uv.x * 19.0 + node * 1.7);
        lightBands += exp2(-1.7 * pow(distance / width, 2.0)) * strength * irregularity;
        softAura += exp2(-1.5 * pow(distance / (width * 2.2), 2.0)) * strength;
    }
}

float fractureBreath = .5 + .5 * sin(time * 1.35 - uv.y * 5.0);
// Mostly use the existing softened mask; fine crack strokes remain a faint memory in the ice.
float fracture = (core * .22 + halo * .78) * (.10 + .14 * fractureBreath + .12 * saturate(wake));
float body = fracture + lightBands + facets;
float aura = (softAura + halo * .05) * BurstHalo;
float coverage = (1.0 - exp2(-1.8 * (body + aura * .22))) * SpiritOpacity;
float innerWeight = saturate(facets / max(body, .0001)) * .50;
float3 tint = lerp(BurstColor, InnerColor, innerWeight);
// A restrained blue-violet accent appears only at the dim retreating edge.
tint = lerp(tint, AccentColor, .08 * saturate(aura / max(body + aura, .0001)));
float brightness = SpiritBrightness * (.62 + .38 * saturate(body));
float3 emission = tint * brightness;
float peak = max(emission.r, max(emission.g, emission.b));
emission *= min(1.0, 1.15 / max(peak, .0001));
float edgeFade = smoothstep(.0, .09, uv.x) * (1.0 - smoothstep(.91, 1.0, uv.x));
float endFade = smoothstep(.02, .12, uv.y) * (1.0 - smoothstep(.87, .985, uv.y));
return float4(emission, coverage * RuneOpacity * inside * edgeFade * endFade);
