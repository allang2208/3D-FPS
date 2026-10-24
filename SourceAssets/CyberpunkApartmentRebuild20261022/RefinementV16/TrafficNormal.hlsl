float now=frac(UV.x+Clock*Speed/RouteLength);
float2 a=normalize(Texture2DSampleLevel(Path,PathSampler,float2(frac(UV.x)+.5/2048,.5),0).zw);
float2 b=normalize(Texture2DSampleLevel(Path,PathSampler,float2(now+.5/2048,.5),0).zw);
float cs=dot(a,b),sn=a.x*b.y-a.y*b.x;
return normalize(float3(cs*N.x-sn*N.y,sn*N.x+cs*N.y,N.z));
