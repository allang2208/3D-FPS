// R6: restore the pre-R5 volume shape, refine only its emitted RGB.
// Deep-red cooler edges, red/orange body, restrained orange hot highlights.
// Continuous heat compression retains high-temperature variation instead of
// clipping the whole core to one color. No white or broad yellow endpoint.
// Extinction, density, source motion and exposure use the restored V8 baseline.
float heat = max(Temperature - ColorMin, 0.0) / max(ColorMax - ColorMin, 0.001);
float t = 1.0 - exp2(-heat * 1.5);

float3 c = lerp(float3(0, 0, 0), float3(0.28, 0.020, 0.006), smoothstep(0.0, 0.055, t));
c = lerp(c, float3(1.40, 0.170, 0.012), smoothstep(0.025, 0.30, t));
c = lerp(c, float3(2.30, 0.450, 0.025), smoothstep(0.22, 0.62, t));
c = lerp(c, float3(2.85, 0.820, 0.090), smoothstep(0.55, 0.88, t));
c = lerp(c, float3(3.10, 1.250, 0.200), smoothstep(0.88, 1.0, t));
return c;
