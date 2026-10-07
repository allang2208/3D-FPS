// Azure Dragon arm-end fire (V10.8): ONE big realistic flame burning where each forearm dissolves.
// Two stacked camera-facing cards per claw built in C++: layer 0 = rolling fire mass (FireMass,
// Realistic Vol2 T_Fire_F, 6x6 RGB on black), layer 1 = rising tongues (FireTongue, T_Fire_D, 8x4
// RGBA). Real flame sequences, recoloured from their brightness into the dragon's cyan.
// V10.9: alpha-blended (float4 = emissive, opacity) so the flame keeps its deep-blue body and white
// core against bright sky and floors; the V10.8 additive blend washed out to faint haze there.
// UV.x = card index + across (card = claw * 2 + layer), UV.y = 0 at the arm, 1 at the flame top.
float id = floor(UV.x);
float layer = fmod(id, 2.0);
float clawId = floor(id * 0.5);
float2 q = float2(frac(UV.x), saturate(UV.y));
float seed = frac(sin(clawId * 12.9898 + 4.1) * 43758.5453);
float edge = smoothstep(0.0, 0.08, q.x) * smoothstep(1.0, 0.92, q.x) * smoothstep(1.0, 0.90, q.y) * smoothstep(0.0, 0.05, q.y);
float2 cellUV = float2(q.x, 1.0 - q.y);

// Rolling mass: 36 frames, neighbouring frames blended.
float fm = Age * 15.0 + seed * 36.0;
float m0 = fmod(floor(fm), 36.0), m1 = fmod(m0 + 1.0, 36.0), mb = frac(fm);
float2 uvm0 = (float2(fmod(m0, 6.0), floor(m0 / 6.0)) + cellUV) / 6.0;
float2 uvm1 = (float2(fmod(m1, 6.0), floor(m1 / 6.0)) + cellUV) / 6.0;
float3 mass = lerp(Texture2DSample(FireMass, FireMassSampler, uvm0).rgb, Texture2DSample(FireMass, FireMassSampler, uvm1).rgb, mb);

// Rising tongues: 32 frames (8 x 4).
float ft = Age * 19.0 + seed * 32.0;
float t0 = fmod(floor(ft), 32.0), t1 = fmod(t0 + 1.0, 32.0), tb = frac(ft);
float2 uvt0 = (float2(fmod(t0, 8.0), floor(t0 / 8.0)) + cellUV) / float2(8.0, 4.0);
float2 uvt1 = (float2(fmod(t1, 8.0), floor(t1 / 8.0)) + cellUV) / float2(8.0, 4.0);
float4 tongue = lerp(Texture2DSample(FireTongue, FireTongueSampler, uvt0), Texture2DSample(FireTongue, FireTongueSampler, uvt1), tb);

float massLum = dot(mass, float3(0.35, 0.50, 0.15));
float tongueLum = dot(tongue.rgb, float3(0.35, 0.50, 0.15)) * tongue.a;
float lum = layer < 0.5 ? massLum * 1.15 : tongueLum * 1.35;
float3 deep  = float3(0.02, 0.12, 0.65);
float3 cyan  = float3(0.20, 0.85, 1.00);
float3 white = float3(0.85, 1.00, 1.00);
float3 col = lerp(deep, cyan, smoothstep(0.04, 0.40, lum));
col = lerp(col, white, smoothstep(0.50, 0.92, lum));
col *= 0.8 + 2.2 * lum;   // hot cores glow, the thin outer flame stays deep blue
float nearHide = (SceneDepth.r < PixelDepth - 5.0 && SceneDepth.r < NearOcclusion) ? 1.0 : 0.0;
return float4(col, saturate(lum * 1.9) * edge * Fade * (1.0 - nearHide));
