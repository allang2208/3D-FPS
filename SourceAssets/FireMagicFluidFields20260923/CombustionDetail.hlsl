// Keep each native flame atlas and its original silhouette/opacity. Niagara
// UV0 already contains the native SubImage tile transform; recover local UV
// before sampling the independent 8x8 Mantaflow field atlas.
float2 localUV = frac(NativeUV * NativeGrid);
float2 fieldUV = clamp(0.16 + 0.68 * localUV, 4.5 / 256.0, 251.5 / 256.0);

// Profile: frames/sec, phase offset, detail blend, one-shot flag.
// Staggered particle ages prevent a whole field from pulsing in lockstep.
float cycle = frac((Clock * Profile.x + ParticleAge * 9.0) / 64.0 + Profile.y) * 64.0;
float frame = lerp(cycle, saturate(ParticleAge) * 63.0, Profile.w);
float first = floor(frame);
float second = lerp(fmod(first + 1.0, 64.0), min(first + 1.0, 63.0), Profile.w);
float2 tileA = float2(fmod(first, 8.0), floor(first / 8.0));
float2 tileB = float2(fmod(second, 8.0), floor(second / 8.0));
float3 a = Texture2DSampleLevel(Atlas, AtlasSampler, (tileA + fieldUV) / 8.0, 0).rgb;
float3 b = Texture2DSampleLevel(Atlas, AtlasSampler, (tileB + fieldUV) / 8.0, 0).rgb;
float3 combustion = saturate(lerp(a, b, frac(frame)));

float flame = combustion.r;
float temperature = combustion.g;
float soot = combustion.b;
float heat = smoothstep(0.20, 0.86, flame * 0.70 + temperature * 0.30);
float3 thermalTint = lerp(float3(1.03, 0.72, 0.65), float3(1.03, 1.13, 1.18), heat);
float densityLight = lerp(0.82, 1.13, heat) * (1.0 - 0.14 * soot * (1.0 - flame));
float3 response = lerp(float3(1.0, 1.0, 1.0), thermalTint * densityLight, Profile.z);
// Multiplication preserves black/transparent edges and the native HDR palette.
// This runs before the existing exposure compensation, not on scene exposure.
return NativeEmission * response;
