float2 p=(UV-.5)*2;
float2 warp=float2(sin(p.y*11+Seed*19),cos(p.x*13+Seed*23))*.021;
p+=warp;
float index=floor(saturate(Seed)*5.99);
float2 q=(p+float2(.08,.02))/float2(.76,.64)*.5+.5;
float2 sampleUV=(float2(fmod(index,3),floor(index/3))+clamp(q,.01,.99))/float2(3,2);
float tex=Texture2DSample(Drops,DropsSampler,sampleUV).b;
float2 bound=smoothstep(0,.035,q)*smoothstep(0,.035,1-q);
float core=smoothstep(.025,.60,tex)*bound.x*bound.y;
float specks=0;
[unroll] for(int i=0;i<9;++i)
{
    float h=frac(sin((i+1)*43.17+Seed*31.3)*43758.5453);
    float angle=i*2.39996+Seed*6.283;
    float2 c=float2(cos(angle),sin(angle))*(.45+h*.36);
    float2 radii=float2(.035+h*.07,.035+h*.10);
    float d=length((p-c)/radii);
    specks=max(specks,1-smoothstep(.72,1,d));
}
float grain=.93+.07*sin(p.x*91+sin(p.y*57))*cos(p.y*83);
return saturate(max(core,specks)*grain*.98);
