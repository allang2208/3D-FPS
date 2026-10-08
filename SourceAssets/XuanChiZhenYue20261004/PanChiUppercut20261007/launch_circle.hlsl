// Guard-derived production art: twin chi, spread cloud wings, mountain crest,
// and a restrained jade heart. Alpha gaps expose the real ground beneath it.
float2 p=(UV-.5)*2.;
float r=length(p),a=atan2(p.y,p.x),t=Seconds;
// Mesh U follows player-forward. Keep the guard wings on the left/right axis.
float2 sealUV=float2(UV.y,1.-UV.x);
float4 art=Texture2DSample(Seal,SealSampler,sealUV);
float luma=dot(art.rgb,float3(.2126,.7152,.0722));
float peak=max(max(art.r,art.g),max(art.b,.08));
float3 pigment=art.rgb/peak;
float carved=smoothstep(.028,.34,luma);
// Recesses stay translucent; the asset reads as a projected seal, not a plate.
float ink=art.a*(.13+.77*carved);
float halo=0.;
halo+=Texture2DSample(Seal,SealSampler,sealUV+float2(.006,0)).a;
halo+=Texture2DSample(Seal,SealSampler,sealUV-float2(.006,0)).a;
halo+=Texture2DSample(Seal,SealSampler,sealUV+float2(0,.006)).a;
halo+=Texture2DSample(Seal,SealSampler,sealUV-float2(0,.006)).a;
halo=saturate(halo*.25-art.a*.75)*.11;
float edge=1.-smoothstep(.88,1.01,r);
float sweep=pow(saturate(.5+.5*cos(a*2.-t*3.8+r*5.)),5.);
float pulse=.94+.06*sin(t*8.-r*5.);
float jade=saturate((pigment.g-pigment.r)*7.)*(1.-smoothstep(.10,.22,r));
float3 gold=lerp(float3(1.,.38,.04),float3(1.,.77,.27),carved);
float3 color=lerp(gold,lerp(pigment,float3(.70,1.,.78),.18),jade*.8);
float energy=(1.65+1.35*carved+.42*sweep+.10*Charge)*pulse;
float coverage=saturate(ink+halo)*edge*Opacity;
return float4(color*energy,coverage);
