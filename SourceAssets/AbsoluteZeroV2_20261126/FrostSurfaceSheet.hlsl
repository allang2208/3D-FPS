// Shared terrain-conforming crystalline frost surface shader for Blizzard & AbsoluteZero.
// Samples approved T_IceSurfaceColor at two world-space scales (zero UV stretch on ellipses,
// slopes, or wall-clamped perimeters), driven by VertexColor (R=NormRadius, G=EdgeNoise,
// B=SlopeMask, A=SurfaceMask) and dynamic scalars (Fade, RevealRadius, FrostDensity, EmissiveBoost).
float2 wp = WorldPos.xy;
float2 uvMacro = wp / 380.0;
float2 uvDetail = float2(wp.x * 0.866 - wp.y * 0.5, wp.x * 0.5 + wp.y * 0.866) / 135.0;
float3 cMacro = Texture2DSample(IceTex, IceTexSampler, uvMacro).rgb;
float3 cDetail = Texture2DSample(IceTex, IceTexSampler, uvDetail).rgb;

float lumMacro = saturate(cMacro.r * 0.55 + cMacro.g * 0.35 + cMacro.b * 0.10);
float lumDetail = saturate(cDetail.r * 0.55 + cDetail.g * 0.35 + cDetail.b * 0.10);
float crystal = saturate(lumMacro * 0.62 + lumDetail * 0.38);

// VertexColor channels: VRGB.r = normalized radius [0..1], VRGB.g = organic rim modulation [0..1], VA = geometry validity [0..1].
float rNorm = VRGB.r;
float rimMod = lerp(0.84, 1.00, VRGB.g);
float outerFeather = 1.0 - smoothstep(rimMod - 0.15, rimMod, rNorm);

// Expanding freezing wavefront unmask (Blizzard sets RevealRadius=1.25; AbsoluteZero sweeps 0->1.08).
float waveMask = 1.0 - smoothstep(RevealRadius - 0.11, RevealRadius + 0.015, rNorm);
float waveBand = exp(-pow((rNorm - (RevealRadius - 0.03)) / 0.055, 2.0)) * saturate(1.0 - smoothstep(0.95, 1.12, RevealRadius));

// Rich frosty coverage: solid bright white-ice core with subtle crystalline fracture depth.
float frostPatch = saturate(0.56 + 0.44 * smoothstep(0.18, 0.78, crystal));
float opacity = saturate(VA * outerFeather * waveMask * frostPatch * FrostDensity * Fade);
// Boost opacity right on the active freezing crest so the advancing frost line snaps cleanly.
opacity = saturate(opacity + VA * outerFeather * waveBand * 0.38 * Fade * saturate(EmissiveBoost));

// Bright snow-ice white with cool glacier-blue fracture troughs.
float3 baseCol = lerp(float3(0.66, 0.83, 0.94), float3(0.96, 0.985, 1.00), smoothstep(0.16, 0.82, crystal));

return float4(baseCol, opacity);
