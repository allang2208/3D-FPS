// Undeformed centimetre coordinates retain the existing geometry/UV channels.
float3 w=pow(abs(normalize(N)),4);
w/=max(dot(w,float3(1,1,1)),.0001);
float3 q=P/4.;
return Texture2DSample(T,TSampler,q.yz)*w.x+
    Texture2DSample(T,TSampler,q.xz+float2(.37,.61))*w.y+
    Texture2DSample(T,TSampler,q.xy+float2(.71,.13))*w.z;
