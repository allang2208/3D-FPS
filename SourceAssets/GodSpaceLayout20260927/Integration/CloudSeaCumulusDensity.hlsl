// Bounded shape/detail erosion adapted from @takram/three-clouds, clouds.glsl.
// Copyright (c) 2024 Shota Matsuda. MIT license: ThirdParty/TakramClouds/LICENSE.
// Existing UE Perlin-Worley data is sampled as linear density, with authored mips.
if (Support.x<=0 || Support.y<=0) return 0;
float2 moved = (P.xy-float2(-2400,-1300))*.01 + Placement.xy*LayoutScale*1000;
float3 p = float3(.920505*moved.x-.390731*moved.y,
                 .390731*moved.x+.920505*moved.y,P.z*.01);
float distanceM = length(P-Camera)*.01;
// Keep the same 3-D shape all the way to the horizon; only filter frequencies.
// The old version switched off this shape at distance and exposed a flat sheet.
float shapeMip = clamp(log2(max(distanceM/9000,1)),0,3);
float3 shapeUV = p/float3(1700,2300,850)
    + Clock*float3(.00017,.000073,-.000047);
float shape = saturate(Texture3DSampleLevel(Noise,NoiseSampler,shapeUV,shapeMip).r);
// Multiplication retains volume variation even at the height-profile maximum.
// The previous remap produced exactly one when Support.y was one, independent
// of the 3-D noise. Broad, persistent lobes now vary the actual cloud surface.
float matter = max(0,(shape*Support.y-.22)/.78);
if (matter<=0) return 0;
// One extra volume fetch only in the foreground. Erosion vanishes continuously
// and cannot create matter in an empty location or a separate far cloud layer.
float detailWeight = 1-smoothstep(2500,6500,distanceM);
[branch] if (detailWeight>.001 && ShadowDistance<=0)
{
    float3 uv = p/float3(520,730,410)+float3(3.71,7.13,1.97)
        + Clock*float3(-.00021,.00013,.000071);
    float detail = saturate(Texture3DSampleLevel(Noise,NoiseSampler,uv,1).r);
    float edge = 1-smoothstep(.10,.45,matter);
    float erosion = (1-detail)*.18*detailWeight*edge;
    matter = max(0,matter-erosion);
}
// Soft vertical boundaries are wider than the primary ray step. Smooth density
// removes hard clipping without adding another screen-space dither pattern.
float profile = smoothstep(0,.14,Support.z)*(1-smoothstep(.78,1,Support.z));
// Never remap dense interiors to a constant slab; soft threshold removes
// abrupt cuts without adding spatial dither or raising ray-march samples.
matter = matter*smoothstep(0,.10,matter)*profile;
float density = clamp(Density,.001,.02)*lerp(1,1.35,saturate(Weather));
return Support.x*matter*density;
