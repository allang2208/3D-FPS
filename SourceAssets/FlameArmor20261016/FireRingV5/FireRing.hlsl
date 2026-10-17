// V5: a broader, taller flame silhouette readable from the F6 camera.
// UV.x is a full turn. UV.y >= 0 is wall height; UV.y <= -1 is the floor band.
// All angular noise inputs are periodic so the 0/1 seam cannot split the ring.
float angle = UV.x * 6.283185307;
float2 direction = float2(cos(angle), sin(angle));
float floorBand = step(UV.y, -0.5);
float h = saturate(UV.y);
float radial = saturate(-UV.y - 1.0);
float2 flowUV = direction * (2.2 + h * .18) + float2(Clock * .13, h * 1.7 - Clock * .56);
float n1 = Texture2DSample(Noise, NoiseSampler, flowUV).r;
float n2 = Texture2DSample(Noise, NoiseSampler,
    direction * 4.6 + float2(-Clock * .21, h * 2.9 - Clock * .86)).r;

// Reuse the actual fireball's packed Mantaflow flame / temperature / soot field.
float frame = frac(Clock * (18.0 / 64.0)) * 64.0;
float first = floor(frame);
float second = fmod(first + 1.0, 64.0);
float2 localUV = clamp(.5 + direction * (.14 + .22 * h), 4.5 / 256.0, 251.5 / 256.0);
float2 tileA = float2(fmod(first, 8.0), floor(first / 8.0));
float2 tileB = float2(fmod(second, 8.0), floor(second / 8.0));
float3 a = Texture2DSampleLevel(Atlas, AtlasSampler, (tileA + localUV) / 8.0, 0).rgb;
float3 b = Texture2DSampleLevel(Atlas, AtlasSampler, (tileB + localUV) / 8.0, 0).rgb;
float3 combustion = lerp(a, b, frac(frame));

float rolling = .5 + .5 * sin(angle * 7.0 - Clock * 1.7 + n1 * 2.5);
float crest = .50 + .24 * rolling + .20 * n1 + .06 * combustion.r;
float top = 1.0 - smoothstep(crest - .15, crest, h);
float root = 1.0 - smoothstep(.18, .36, h);
float sheets = saturate(.65 + .35 * n1 + .24 * n2 + .18 * combustion.r - h * .24);
float wallAlpha = top * lerp(sheets, .97, root);
float floorEdge = smoothstep(0.0, .10, radial) * (1.0 - smoothstep(.90, 1.0, radial));
float floorAlpha = floorEdge * (.94 + .05 * n1);
float alpha = lerp(wallAlpha, floorAlpha, floorBand);

float heat = saturate(.42 + .30 * (1.0 - h) + .25 * combustion.r + .14 * combustion.g + .10 * n2);
float3 rgb = lerp(float3(1,.060,.002), float3(1,.25,.012), smoothstep(.20,.62,heat));
rgb = lerp(rgb, float3(1,.64,.10), smoothstep(.66,.99,heat));
rgb *= 1.0 - .18 * combustion.b * (1.0 - combustion.r);
return float4(rgb, saturate(alpha));
