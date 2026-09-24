float2 direction=normalize(Flow.rg*2-1+float2(.00001,0));
float2 uv=Position.xy/160-direction*Clock*Flow.b*.20;
float noise=Texture2DSample(FoamTexture,FoamTextureSampler,uv).r;
float detail=Texture2DSample(FoamTexture,FoamTextureSampler,uv*2.17+3.71).r;
float shore=smoothstep(.8,5,Depth)*(1-smoothstep(12,34,Depth));
float broken=smoothstep(.42,.78,noise)*smoothstep(.24,.68,detail);
float flowPatch=.5+.5*sin(Position.x*.005+Position.y*.003-Clock*.6);
float current=smoothstep(.40,.8,Flow.b)*smoothstep(12,40,Depth)*flowPatch;
// Reuse the existing two samples for broken, short-lived impact foam.
return saturate(shore*broken*.48+current*broken*.12+Ripple.z*(.14+broken*.36));
