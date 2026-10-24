float2 Foot=max(abs(ddx(UV))+abs(ddy(UV)),.0001);float Lod=clamp(log2(max(max(Foot.x*Aspect/16*2048,Foot.y*128),1)),0,3);float Brightness=lerp(.55,2.6,Night);float3 Color=0;
float2 q=float2(UV.x*Aspect/16+T*.028,(clamp(UV.y,.035,.965)+Slot)*.25);
float edge=smoothstep(0,.035,UV.x)*(1-smoothstep(.965,1,UV.x));
Color=Texture2DSampleLevel(Ticker,TickerSampler,q,Lod).rgb*Brightness*edge;
return Color;