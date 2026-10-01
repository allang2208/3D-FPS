// Factory-magazine sideplate UV islands from its existing dedicated UV0 atlas.
// Replace the inflated crosshatch only; rolled lips and all other islands retain N.
float fade = .005;
float left = smoothstep(.007961, .007961 + fade, UV.x)
    * (1 - smoothstep(.256545 - fade, .256545, UV.x));
float right = smoothstep(.272467, .272467 + fade, UV.x)
    * (1 - smoothstep(.521018 - fade, .521018, UV.x));
float vertical = smoothstep(.797, .810, UV.y)
    * (1 - smoothstep(.976, .987, UV.y));
float region = saturate(max(left, right) * vertical);
float origin = UV.x < .264 ? .007961 : .272467;
float2 gradient = 0;
// Three shallow rounded longitudinal pressings, no transverse crossing bars.
[unroll] for (int i = 0; i < 3; ++i)
{
    float cx = origin + .248567 * (.205 + .295 * i);
    float2 d = float2(UV.x - cx, UV.y - clamp(UV.y, .825, .953)) * UVToMM;
    float distanceMM = length(d);
    float radiusMM = max(RadiusMM, .1);
    float t = saturate(distanceMM / radiusMM);
    float slope = -HeightMM * 3.14159265 / (2 * radiusMM) * sin(t * 3.14159265);
    gradient += slope * d / max(distanceMM, .0001);
}
// UE tangent-space normal; texture UV v increases downwards.
float3 pressing = normalize(float3(-gradient, 1));
return float4(normalize(lerp(N, pressing, region)), region);
