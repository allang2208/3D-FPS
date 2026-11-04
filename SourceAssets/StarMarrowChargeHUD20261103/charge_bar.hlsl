// Production cutout: 2172x724. Keep metal rails fixed while flame/energy UVs flow.
float2 p=(UV-float2(.5,.545))*float2(3.,1.);
float innerD=length(float2(max(abs(p.x)-1.280,0.),p.y))-.064;
float outerD=length(float2(max(abs(p.x)-1.282,0.),p.y))-.105;
float aa=max(fwidth(innerD),.0012);
float interior=1.-smoothstep(-aa,aa,innerD);
float flameRegion=smoothstep(.002,.028,outerD);
float bodyRegion=1.-smoothstep(-.035,-.005,innerD);
float2 flow=UV;
// Several travelling scales bend the extracted flame tongues, never the frame.
flow.x+=flameRegion*(.0045*sin(UV.x*69.-T*3.9)+.002*sin(UV.x*143.+T*5.1));
flow.y+=flameRegion*(.012*sin(UV.x*55.-T*4.3)+.006*sin(UV.x*119.+T*6.4));
flow.x+=bodyRegion*.004*sin(UV.y*77.+UV.x*31.-T*1.7);
flow.y+=bodyRegion*.006*sin(UV.x*45.-T*2.3);
float4 art=Texture2DSample(ArtTexture,ArtTextureSampler,saturate(flow));
float coverage=art.a;
float3 color=art.rgb;
float end=lerp(.052,.948,saturate(Progress));
float energy=(1.-smoothstep(end-.001,end+.001,UV.x))*step(.00001,Progress);
float empty=interior*(1.-energy);
// The empty region retains the dark sapphire well, with no full-length blue fill.
color=lerp(color,float3(.002,.009,.026),empty);
coverage=lerp(coverage,.97,empty);
float stream=pow(.5+.5*sin(UV.x*57.-T*2.8+sin(UV.y*42.+T)),10.);
color+=float3(.015,.09,.15)*stream*interior*energy;
float edge=exp(-abs(UV.x-end)*480.)*interior*step(.002,Progress)*(1.-step(.998,Progress));
color+=float3(.12,.65,1.)*edge;
color*=lerp(1.,.83+.17*sin(UV.x*87.-T*7.)*.5+.13*sin(UV.x*151.+T*9.2),flameRegion);
// A bounded handful of rising sparks, composited with true alpha.
float sparks=0.;
[unroll] for(int i=0;i<9;++i)
{
    float seed=frac((i+1)*.61803399);
    float life=frac(T*(.35+.12*seed)+seed);
    float2 sparkPosition=float2(.065+.87*seed+.006*sin(life*6.+i),.43-life*.24);
    float2 d=(UV-sparkPosition)*float2(3.,1.);
    float spark=exp(-dot(d*float2(260.,150.),d*float2(260.,150.)))*sin(life*3.14159);
    sparks+=spark;
}
float a=saturate(sparks)*flameRegion;
float outA=coverage+a*(1.-coverage);
float3 outRGB=(color*coverage+float3(.12,.6,1.)*a*(1.-coverage))/max(outA,.0001);
return float4(outRGB,outA);
