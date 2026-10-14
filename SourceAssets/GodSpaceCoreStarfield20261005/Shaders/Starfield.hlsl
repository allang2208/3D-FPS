// Opaque, two texture samples: independently controlled nebula and sharp stars.
float3 N=normalize(P-C);
float3 Vn=normalize(V);
float3 ray=-Vn;
float b=dot(N,ray);
float disc=b*b-(1.0-0.92*0.92);
float travel=max(0.0,-b-sqrt(max(disc,0.0)));
float3 inner=normalize(N+ray*travel);
float3 direction=normalize(lerp(N,inner,smoothstep(0.0,0.10,disc)*Depth));
float2 uv=float2(atan2(direction.y,direction.x)*0.1591549431+0.5,acos(clamp(direction.z,-1.0,1.0))*0.3183098862);
// Unwrap screen derivatives so the longitude seam does not select a blurred mip.
float2 gx=ddx(uv),gy=ddy(uv);
gx.x-=round(gx.x);gy.x-=round(gy.x);
float3 sky=Texture2DSampleGrad(Tex,TexSampler,uv,gx,gy).rgb;
float3 stars=Texture2DSampleGrad(Stars,StarsSampler,uv,gx,gy).rgb;
float rim=pow(saturate(1.0-dot(N,Vn)),10.0);
return sky*Strength+stars*StarStrength+float3(0.009,0.065,0.24)*rim*Rim;
