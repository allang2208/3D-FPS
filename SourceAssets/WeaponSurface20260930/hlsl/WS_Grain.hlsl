// Triplanar grain in undeformed local centimetres: follows the skinned gun, no UV dependence.
// Tex: T_WS_Grain (R fine grain, G mottling, B hairline scratches, A stipple).
float3 w=pow(abs(normalize(N)),float3(4,4,4));
w/=max(dot(w,float3(1,1,1)),.0001);
float3 q=P/max(TileCm,.01);
float4 a=Texture2DSample(Tex,TexSampler,q.yz);
float4 b=Texture2DSample(Tex,TexSampler,q.xz+float2(.37,.61));
float4 c=Texture2DSample(Tex,TexSampler,q.xy+float2(.71,.13));
return a*w.x+b*w.y+c*w.z;
