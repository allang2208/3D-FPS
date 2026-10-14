// One bounded, pooled translucent sheet behind the hand. Only X4+ results enable it.
// Tier 1 = full house; tier 2 = four flame crowns; tier 3 = infernal horns + crown.
float2 p = float2((UV.x - 0.5) * 2.0, (0.5 - UV.y) * 2.0);
float t = Age;
float attack = smoothstep(0.0, 0.18, t);
float envelope = attack * exp(-max(0.0, t - 0.35) * 0.95) * Reveal;
float turbulence = 0.80 + 0.10 * sin(p.x * 29.0 - p.y * 15.0 + t * 8.0)
                        + 0.08 * sin(p.x * 57.0 + p.y * 33.0 - t * 11.0);
float flames = 0.0;
// Four narrow flames stay clear of the central letter cores and the crosshair.
[unroll] for (int j = 0; j < 4; ++j)
{
    float height = saturate((p.y + 0.55) / 1.08);
    float center = (j - 1.5) * 0.36 + sin(height * 7.0 - t * 4.0 + j * 1.7) * (0.024 + height * 0.035);
    float width = lerp(0.065, 0.004, height);
    float tongue = exp(-pow((p.x - center) / width, 2.0))
        * smoothstep(-0.60, -0.30, p.y) * (1.0 - smoothstep(0.30, 0.57, p.y));
    flames += tongue * turbulence * (Tier >= 1.5 ? 0.63 : 0.23);
}
float horns = 0.0;
float crown = 0.0;
if (Tier >= 2.5)
{
    float h = saturate((p.y + 0.02) / 0.86);
    float hornX = 0.27 + 0.40 * h - 0.18 * h * h + 0.011 * sin(h * 18.0 - t * 4.5);
    float hornWidth = lerp(0.056, 0.006, h);
    horns = exp(-pow((abs(p.x) - hornX) / hornWidth, 2.0))
        * smoothstep(-0.12, 0.03, p.y) * (1.0 - smoothstep(0.73, 0.90, p.y));
    float crownY = 0.07 + 0.24 * cos(p.x * 5.8) + 0.027 * sin(p.x * 36.0 - t * 5.0);
    crown = exp(-pow((p.y - crownY) / 0.034, 2.0)) * (1.0 - smoothstep(0.55, 0.79, abs(p.x)));
}
float embers = 0.0;
[unroll] for (int k = 0; k < 18; ++k)
{
    float seed = frac(sin((k + 1.0) * 78.233) * 43758.5453);
    float born = (k % 6) * 0.055;
    float age = max(0.0, t - born);
    float2 origin = float2((seed - 0.5) * 1.60, -0.57);
    float2 pos = origin + float2(sin(seed * 19.0) * age * 0.11, age * (0.42 + seed * 0.27));
    float2 q = (p - pos) / float2(0.006 + seed * 0.005, 0.018 + seed * 0.014);
    embers += exp(-dot(q, q)) * step(born, t) * saturate(1.0 - age / 2.3);
}
float frameFade = pow(saturate(1.0 - abs(p.x)), 0.35) * smoothstep(-1.0, -0.83, p.y)
    * (1.0 - smoothstep(0.88, 1.0, p.y));
float coverage = saturate((flames + horns * 0.58 + crown * 0.49 + embers) * envelope * frameFade);
float whiteHeat = saturate(horns * 0.5 + crown * 0.4 + embers);
float3 color = lerp(float3(1.45, 0.12, 0.012), float3(1.9, 0.76, 0.09), whiteHeat);
return float4(color, coverage);
