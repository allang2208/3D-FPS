// UV0.x is the axial sample; UV0.y encodes the authored branch ID after FBX V flip.
// All six vertices of each tube ring receive identical displacement.
float branch = floor((1.0 - UV.y) * 16.0 + 0.5);
float t = saturate(UV.x);
float stepIndex = floor(t * 10.0 + 0.5);
float clock = Clock * 12.0 + branch * 0.137;
float tick = floor(clock);
float mixTime = smoothstep(0.80, 1.0, frac(clock));
float3 next0 = frac(sin(float3(17.13, 53.27, 91.91) *
    (tick + branch * 8.31 + stepIndex * 3.77 + 1.0)) * 43758.5453) * 2.0 - 1.0;
float3 next1 = frac(sin(float3(17.13, 53.27, 91.91) *
    (tick + branch * 8.31 + stepIndex * 3.77 + 2.0)) * 43758.5453) * 2.0 - 1.0;
float3 jitter = lerp(next0, next1, mixTime);
float envelope = 0.18 + 0.82 * sin(t * 3.14159265);
// Slow endpoint motion prevents a static star silhouette; sharp internal kinks restrike at 12 Hz.
float3 drift = float3(sin(Clock * 2.9 + branch * 2.4 + t * 2.5),
                     cos(Clock * 3.6 + branch * 1.7 + t * 1.3),
                     sin(Clock * 2.2 + branch * 3.1 - t * 2.0)) * 0.34;
return jitter * envelope * 0.47 + drift;
