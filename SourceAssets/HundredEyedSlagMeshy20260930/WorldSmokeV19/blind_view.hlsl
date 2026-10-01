// Original in-smoke screen contamination, inspired by the requested vomit-screen presentation.
// No world-volume ray darkening: outside the smoke the player removes this layer entirely.
float strength = saturate(BlindStrength);
if (strength <= .0001) return SceneColor.rgb;
float2 uv = GetViewportUV(Parameters);
float2 invSize = View.ViewSizeAndInvSize.zw;
float n0 = Texture2DSampleLevel(NoiseTex, NoiseTexSampler,
    uv * float2(2.8, 2.1) + float2(Time * .009, -Time * .018), 1).r;
float n1 = Texture2DSampleLevel(NoiseTex, NoiseTexSampler,
    uv.yx * float2(4.1, 3.2) + float2(-Time * .014, Time * .006), 1).r;
float2 warpedUV = saturate(uv + float2(n0 - .5, n1 - .5) * .014 * strength);
float radius = (14.0 + n0 * 9.0) * strength;
float2 offsets[9] = {float2(0,0), float2(1,0), float2(-1,0), float2(0,1), float2(0,-1),
    float2(1,1), float2(-1,1), float2(1,-1), float2(-1,-1)};
float weights[9] = {4,2,2,2,2,1,1,1,1};
float3 blurred = 0;
[unroll] for (int i = 0; i < 9; ++i)
{
    float2 sampleUV = saturate(warpedUV + offsets[i] * invSize * radius);
    float2 sceneUV = ClampSceneTextureUV(ViewportUVToSceneTextureUV(sampleUV, 14), 14);
    blurred += SceneTextureLookup(sceneUV, 14, true).rgb * weights[i];
}
blurred /= 16.;
float luminance = dot(blurred, float3(.2126, .7152, .0722));
float3 murky = lerp(float3(luminance, luminance, luminance), blurred, .38) * .62;
float2 p = (uv - .5) * 2;
float rim = smoothstep(.35, 1.2, dot(p, p));
float grime = saturate(.20 + .68 * smoothstep(.28, .72, n0 * .6 + n1 * .4) + rim * .32);
float3 soot = float3(.018, .014, .012);
float3 stained = lerp(murky, soot, grime * .78);
return lerp(SceneColor.rgb, stained, strength);
