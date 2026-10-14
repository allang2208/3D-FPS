// Dragon Breath volume: color-only thermal mapping, independent of extinction.
// The scalar grid stores temperature in G; peak injection is approximately 150.
// RGB values are linear HDR, followed by the existing FireGain and ONE exposure
// inverse. The highest band remains warm instead of converging to neutral white.
float t = saturate((Temperature - ColorMin) / max(ColorMax - ColorMin, 0.001));
float3 c = lerp(float3(0, 0, 0), float3(0.65, 0.018, 0.001), smoothstep(0.0, 0.06, t));
c = lerp(c, float3(2.10, 0.17, 0.006), smoothstep(0.06, 0.30, t));
c = lerp(c, float3(3.00, 0.64, 0.025), smoothstep(0.30, 0.72, t));
c = lerp(c, float3(3.50, 1.25, 0.120), smoothstep(0.72, 0.90, t));
c = lerp(c, float3(3.80, 2.10, 0.650), smoothstep(0.90, 1.00, t));
return c;
