// Same 11 custom-node inputs: constants preserve live graph links.
float BlueGlowStrength=2.8;
float BlueRimStrength=2.4;
// V5 blue glow: five bounded texture samples. Normal mip chains; no global LOD override.
float3 N=normalize(P-C);
float3 Vn=normalize(V);
float3 ray=-Vn;
float b=dot(N,ray);
float disc=b*b-(1.0-0.92*0.92);
float travel=max(0.0,-b-sqrt(max(disc,0.0)));
float3 inner=normalize(N+ray*travel);
float3 direction=normalize(lerp(N,inner,smoothstep(0.0,0.10,disc)*Depth));
float2 uv=float2(atan2(direction.y,direction.x)*0.1591549431+0.5,acos(clamp(direction.z,-1.0,1.0))*0.3183098862);
float2 gx=ddx(uv),gy=ddy(uv);
gx.x-=round(gx.x);gy.x-=round(gy.x);
float3 sky=Texture2DSampleGrad(Tex,TexSampler,uv,gx,gy).rgb;
float stars=Texture2DSampleGrad(Stars,StarsSampler,uv,gx,gy).r;
// Direction-space triplanar fine structure remains defined at both spherical poles.
float3 weights=pow(abs(direction),4.0);weights/=max(dot(weights,1.0),0.0001);
float3 q=direction*18.0;
float3 detail=Texture2DSample(Detail,DetailSampler,q.yz).rgb*weights.x;
detail+=Texture2DSample(Detail,DetailSampler,q.xz).rgb*weights.y;
detail+=Texture2DSample(Detail,DetailSampler,q.xy).rgb*weights.z;
float broadCloud=pow(saturate((max(sky.r,max(sky.g,sky.b))-0.012)/0.208),0.8);
float cloudMask=smoothstep(0.012,0.13,max(sky.r,max(sky.g,sky.b)));
float structure=1.0+((detail.r-0.5)*0.90+(detail.g-0.5)*0.32)*DetailStrength*cloudMask;
sky*=max(0.35,structure);
float rim=pow(saturate(1.0-dot(N,Vn)),10.0);
float wideRim=pow(saturate(1.0-dot(N,Vn)),3.0);
float3 blueGlow=float3(0.018,0.24,1.0)*(broadCloud*BlueGlowStrength+wideRim*BlueRimStrength);
return sky*Strength+stars*float3(0.78,0.89,1.0)*StarStrength+float3(0.009,0.065,0.24)*rim*Rim+blueGlow;
