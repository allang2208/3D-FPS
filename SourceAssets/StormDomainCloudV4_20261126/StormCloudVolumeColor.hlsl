// StormDomainV4 volumetric cloud internal lightning scatter RGB ramp.
// Samples the Grid3D_Gas RG16F Temperature channel (G) injected near active
// NS_StormCloudArc discharges, turning dark brooding volumetric storm smoke
// luminously violet-blue from the inside without washing out unlit clouds.
float energy = max(Temperature - ColorMin, 0.0) / max(ColorMax - ColorMin, 0.001);
float t = 1.0 - exp2(-energy * 2.2);

float3 c = lerp(float3(0.0, 0.0, 0.0), float3(0.11, 0.16, 0.58), smoothstep(0.0, 0.08, t));
c = lerp(c, float3(0.36, 0.50, 1.68), smoothstep(0.06, 0.34, t));
c = lerp(c, float3(0.84, 1.02, 2.75), smoothstep(0.28, 0.68, t));
c = lerp(c, float3(1.55, 1.82, 3.85), smoothstep(0.64, 1.00, t));
return c;
