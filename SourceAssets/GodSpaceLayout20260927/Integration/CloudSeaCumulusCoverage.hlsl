// Height shaping adapted from @takram/three-clouds, clouds.glsl.
// Copyright (c) 2024 Shota Matsuda. MIT license: ThirdParty/TakramClouds/LICENSE.
// UE retains its own ray marcher, lighting, conservative skip and reconstruction.
float distanceM = length(P-Camera)*.01;
float2 uv = (P.xy-float2(-2400,-1300))/max(LayoutScale*100000,1)
    + Placement.xy + float2(.347,.619);
// Filter the weather footprint continuously instead of showing mip-zero noise
// at the horizon. The authored 20th-percentile threshold is a footprint target,
// not a promise of 80% opaque pixels after volumetric erosion/perspective.
float weatherMip = clamp(log2(max(distanceM/12000,1)),0,3);
float3 weather = Texture2DSampleLevel(Pattern,PatternSampler,uv,weatherMip).rgb;
float field = dot(weather,float3(.55,.30,.15));
float coverage = smoothstep(Threshold,Threshold+max(Feather,.002),field);
float top = .44 + .50*sqrt(saturate(dot(weather,float3(.30,.55,.15))));
float bottom = .04 + .035*saturate(weather.b);
float h = saturate((H-bottom)/max(top-bottom,.1));
// Cumulus cross-section tapers as height rises; no constant-height opaque slab.
float centeredHeight = 2*pow(h,.62)-1;
// HLSL pow on a negative base is undefined, even with an integer exponent.
float rounded = 1-centeredHeight*centeredHeight;
// Do not clamp a broad region to one: that erased all 3-D shape in the old
// density remap. Retain a continuous rounded profile for the noise product.
float body = pow(max(rounded,0),1.15)*lerp(.72,1,coverage);
float horizon = 1-smoothstep(10000000,15000000,length(P.xy-Camera.xy));
float occupied = (H>bottom && H<top) ? coverage*horizon : 0;
return float3(occupied,body,h);
