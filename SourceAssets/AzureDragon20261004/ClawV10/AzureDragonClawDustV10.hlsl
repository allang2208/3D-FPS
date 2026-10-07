// Azure Dragon expiry motes (V10.14): one soft glowing grain per camera-facing quad. C++ moves and
// sizes the quads (they shrink to nothing as each mote dies); the shader only shapes the grain.
// UV.x = 2 * mote + corner x, UV.y = corner y. Age = seconds since the dissolve began.
float mote = floor(UV.x * 0.5);
float2 c = float2(UV.x - mote * 2.0, UV.y) * 2.0 - 1.0;
float seed = frac(sin(mote * 12.9898) * 43758.5453);
float r2 = dot(c, c);
float core = exp(-r2 * 10.0);
float glow = exp(-r2 * 3.4);
float twinkle = 0.72 + 0.28 * sin(Age * (8.0 + seed * 7.0) + seed * 40.0);
// White-cyan as it breaks off, cooling to deep blue as the dust drifts away.
float cool = saturate(Age * 0.5 + seed * 0.3 - 0.15);
float3 col = lerp(float3(0.78, 1.0, 1.0), float3(0.06, 0.42, 1.0), cool) * (core * 2.4 + glow * 0.7) * twinkle;
float alpha = saturate(core * 1.15 + glow * 0.35) * twinkle;
float nearHide = (SceneDepth.r < PixelDepth - 5.0 && SceneDepth.r < NearOcclusion) ? 1.0 : 0.0;
return float4(col, saturate(alpha * Fade * (1.0 - nearHide)));
