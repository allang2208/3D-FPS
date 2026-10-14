// Glyph-only English results: an original spear-serif metal face with animated flame anchors.
float idx = floor(clamp(CardIndex, 0.0, 8.0));
float2 cell = float2(fmod(idx, 3.0), floor(idx / 3.0));
float2 local = clamp(UV, 0.006, 0.994);
float2 atlasUV = (cell + local) / 3.0;
float4 mask = Texture2DSample(Atlas, AtlasSampler, atlasUV);
float t = Age;
float ripple = sin(local.x * 59.0 + t * 5.7 + idx) * 0.010
             + sin(local.x * 113.0 - t * 3.9) * 0.005;
float2 flameUV = clamp(local + float2(ripple, sin(local.x * 39.0 - t * 5.4) * 0.024), 0.006, 0.994);
float plume = Texture2DSample(Atlas, AtlasSampler, (cell + flameUV) / 3.0).b;
float flicker = 0.76 + 0.12 * sin(t * 8.4 + local.x * 32.0) + 0.10 * sin(t * 13.1 - local.y * 36.0);
float heat = saturate(1.0 - local.y);
float fissure = pow(saturate(sin(local.x * 99.0 + sin(local.y * 41.0) * 2.8)), 19.0) * mask.r;
float3 metal = lerp(float3(0.16, 0.025, 0.012), float3(0.72, 0.24, 0.045), heat);
float3 bevel = float3(1.30, 0.74, 0.24) * mask.g;
float3 flame = lerp(float3(1.45, 0.09, 0.006), float3(2.0, 0.67, 0.055), saturate(plume * flicker));
float highHeat = 1.0 + Tier * 0.14;
float fireAlpha = plume * flicker * (0.52 + Tier * 0.055);
float3 glyph = metal + bevel + fissure * float3(0.8, 0.14, 0.01) * flicker;
float alpha = saturate(max(mask.r, max(fireAlpha, mask.a * 0.22))) * Reveal;
float3 rgb = lerp(flame, glyph, saturate(mask.r * 1.4)) * highHeat;
return float4(rgb, alpha);
