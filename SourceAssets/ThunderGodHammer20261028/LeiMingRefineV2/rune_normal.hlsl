float along=P.z+35.5;
float2 radial=P.xy-float2(-.0445214100,.1056659501);
float radius=max(length(radial),.001);
float angle=atan2(radial.x,-radial.y);
angle-=3.14159265359*floor((angle+1.57079632679)/3.14159265359);
float2 uv=saturate(float2(.5+angle*radius/(33.5*.25),1-along/33.5));
float2 xy=Texture2DSample(RuneNormal,RuneNormalSampler,uv).rg*2-1;
float nz=sqrt(saturate(1-dot(xy,xy)));
float3 radialN=normalize(float3(radial,0));
float3 tangent=float3(-radialN.y,radialN.x,0);
// Authored DirectX green stores +dH/d(image V); image V runs along local -Z.
return normalize(tangent*xy.x+float3(0,0,1)*xy.y+radialN*nz);