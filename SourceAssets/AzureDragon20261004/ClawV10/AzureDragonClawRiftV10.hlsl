// Azure Dragon talon rift scars (V10.8), after the game's Rift Slash (裂空) V4 look: a slit-like
// double-pointed outline filled with luminous blue-white energy, lengthwise currents, broad feathered
// sides, no void or torn lips. One ribbon per talon spans the whole sweep path (C++ already tapers
// its width to points at both ends); after the rake it holds, then erodes away with Dissolve.
// V10.9: alpha-blended like Rift Slash itself (float4 = emissive, opacity); the V10.8 additive blend
// vanished against bright sky and floors.
// UV.x = 0..1 along the path (start -> talon), UV.y = across.
float along = saturate(UV.x);
float across = UV.y * 2.0 - 1.0;
float flow = Age * 2.8;
float drift = 0.035 * sin(along * 17.0 - flow * 2.4) + 0.014 * sin(along * 41.0 + flow * 1.6);
float lateral = abs(across - drift);
float tips = smoothstep(0.0, 0.06, along) * (1.0 - smoothstep(0.94, 1.0, along));
float feather = 1.0 - smoothstep(0.26, 0.98, lateral);
float fill = exp(-pow(lateral * 2.1, 2.0));
float stream = 0.5 + 0.5 * sin((across - drift) * 34.0 + along * 50.0 - flow * 4.0);
float ribbons = pow(stream, 7.0);
float fine = pow(0.5 + 0.5 * sin((across - drift) * 83.0 + along * 90.0 - flow * 7.0), 11.0);
float swell = 0.5 + 0.5 * sin(along * 15.0 - flow * 2.6);
float spine = exp(-pow(lateral * 11.0, 2.0));
float erosion = smoothstep(Dissolve - 0.14, Dissolve + 0.18, 0.66 + 0.20 * swell + 0.12 * stream);

float3 body = lerp(float3(0.018, 0.15, 0.78), float3(0.28, 0.62, 1.0), fill * 0.86);
float3 light = body * (1.25 + fill * 0.78 + swell * 0.18);
light += float3(0.16, 0.43, 0.85) * (ribbons * 0.36 + fine * 0.12) * feather;
light += float3(0.35, 0.62, 0.85) * spine * 0.27;
float alpha = feather * (0.83 + 0.10 * fill + 0.06 * swell);
float nearHide = (SceneDepth.r < PixelDepth - 5.0 && SceneDepth.r < NearOcclusion) ? 1.0 : 0.0;
return float4(light, saturate(alpha * tips * erosion * Fade * (1.0 - nearHide)));
