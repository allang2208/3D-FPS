// StormDomainV4 Mantaflow 8x8 rolling storm smoke + subsurface lightning scatter.
// Reuses the approved 64-frame Mantaflow smoke atlas (R channel density) with
// per-particle rotation, horizontal flip, phase staggering, internal UV curl,
// soft wispy age erosion, and silver-lining electric flash glow.
float age = saturate(Age);
float Seed = Dynamic.x;
float Phase = Dynamic.y;
float Flash = Dynamic.z;
float2 p = UV - 0.5;
float turn = (Seed - 0.5) * 0.58 + sin(age * 3.4 + Seed * 6.2831853 + Phase * 3.1415926) * 0.095;
float cs = cos(turn), sn = sin(turn);
p = mul(float2x2(cs, -sn, sn, cs), p);
// Internal turbulent fluid curl keeps each puff visibly churning even at close range.
p += float2(
    sin(p.y * 10.5 + age * 3.6 + Seed * 13.7 + Phase * 6.2831853),
    cos(p.x * 9.5 - age * 3.1 + Seed * 9.3 + Phase * 6.2831853)
) * 0.024;
float2 q = p + 0.5;
q.x = lerp(q.x, 1.0 - q.x, step(0.5, Seed));

// Advance smoothly across the 64-frame Mantaflow fluid sequence with per-particle phase offset.
float seq = frac(Phase * 0.42 + 0.03 + age * 0.86);
float frame = min(62.99, seq * 63.0);
float first = floor(frame);
float second = min(first + 1.0, 63.0);
float2 safeUV = clamp(q, float2(0.5 / 256.0, 0.5 / 256.0), float2(255.5 / 256.0, 255.5 / 256.0));
float2 tileA = float2(fmod(first, 8.0), floor(first / 8.0));
float2 tileB = float2(fmod(second, 8.0), floor(second / 8.0));
float a = Texture2DSampleLevel(Atlas, AtlasSampler, (tileA + safeUV) / 8.0, 0).r;
float b = Texture2DSampleLevel(Atlas, AtlasSampler, (tileB + safeUV) / 8.0, 0).r;
float density = lerp(a, b, frac(frame));

// Soft feathered silhouette + late-life wispy erosion (no hard sticker cutoffs).
float edge = min(min(UV.x, 1.0 - UV.x), min(UV.y, 1.0 - UV.y));
float sampleEdge = min(min(q.x, 1.0 - q.x), min(q.y, 1.0 - q.y));
float border = smoothstep(0.015, 0.11, edge) * smoothstep(0.015, 0.09, sampleEdge);
float radial = 1.0 - smoothstep(0.64, 0.99, length((UV - 0.5) * 2.0));
float erosion = lerp(0.012, 0.135, smoothstep(0.46, 1.0, age));
float coverage = smoothstep(erosion, erosion + 0.44, density);
float mask = saturate(coverage * border * radial);
float opacity = saturate(mask * Alpha);

// Internal lightning subsurface glow: strongest through wispy edges + deep translucent core.
float scatter = mask * saturate(Flash) * (0.38 + 1.15 * saturate(1.0 - coverage * 0.62));
return float2(opacity, scatter);
