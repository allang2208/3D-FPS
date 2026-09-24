// Packed Mantaflow fields: R flame, G temperature, B soot. Linear data.
// The 64-frame texture includes an offline overlap at the loop seam.
float frame = frac(Clock * (18.0 / 64.0)) * 64.0;
float first = floor(frame);
float second = fmod(first + 1.0, 64.0);
float2 p = (UV - 0.5) * 2.0;
float thickness = sqrt(saturate(1.0 - dot(p, p)));
float2 localUV = clamp(0.5 + p * (0.38 + 0.07 * thickness), 4.5 / 256.0, 251.5 / 256.0);
float2 tileA = float2(fmod(first, 8.0), floor(first / 8.0));
float2 tileB = float2(fmod(second, 8.0), floor(second / 8.0));
float3 a = Texture2DSampleLevel(Atlas, AtlasSampler, (tileA + localUV) / 8.0, 0).rgb;
float3 b = Texture2DSampleLevel(Atlas, AtlasSampler, (tileB + localUV) / 8.0, 0).rgb;
return lerp(a, b, frac(frame));
