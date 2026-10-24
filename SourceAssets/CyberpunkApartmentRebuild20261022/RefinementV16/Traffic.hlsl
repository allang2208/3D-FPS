// One-row RGBA32F path: XY position in metres, ZW tangent. No vertical UV convention.
float start=UV.x;
float now=frac(start+Clock*Speed/RouteLength);
float4 s0=Texture2DSampleLevel(Path,PathSampler,float2(frac(start)+.5/2048,.5),0);
float4 s1=Texture2DSampleLevel(Path,PathSampler,float2(now+.5/2048,.5),0);
float3 p0=float3(s0.xy*100,-10570),p1=float3(s1.xy*100,-10570);
float2 a=normalize(s0.zw),b=normalize(s1.zw);
float cs=dot(a,b),sn=a.x*b.y-a.y*b.x;
float3 v=Position-p0;
float3 moved=float3(cs*v.x-sn*v.y,sn*v.x+cs*v.y,v.z)+p1;
return moved-Position;
