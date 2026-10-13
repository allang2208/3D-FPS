// Opaque, unlit veil: dark billows cannot open holes into the spawn recess.
// Two packed-noise samples, no raymarch, SceneColor, depth sampling or WPO.
float2 firstUV=UV*float2(1.15,1.8)+Clock*float2(.012,-.023);
float2 warp=Texture2DSample(Density,DensitySampler,firstUV).rg;
float2 secondUV=UV*float2(2.3,2.1)+(warp-.5)*.19+Clock*float2(-.021,-.017);
float fine=Texture2DSample(Density,DensitySampler,secondUV).b;
float density=smoothstep(.24,.80,warp.r*.72+fine*.28);
float2 edge=smoothstep(float2(0,0),float2(.13,.10),UV)
           *smoothstep(float2(0,0),float2(.13,.10),1.-UV);
// Very low charcoal variation, not luminous grey/white smoke. The underlying
// lining stays exact black. Exposure compensation prevents room exposure from
// turning the veil bright; there is no light or emissive GI contribution.
float tone=.004*pow(density,2.2)*edge.x*edge.y;
return float3(tone,tone,tone)/max(Exposure,.0001);
