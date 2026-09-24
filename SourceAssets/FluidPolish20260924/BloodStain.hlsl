float age=max(0,Clock-Born);
float spread=lerp(.68,1,smoothstep(0,.32,age));
float2 p=(UV-.5)*2/spread;
float2 warp=float2(sin(p.y*11+Seed*19),cos(p.x*13+Seed*23))*.021;
float index=floor(saturate(Seed)*5.99);
float2 q=(p+warp+float2(.08,.02))/float2(.76,.64)*.5+.5;
float2 sampleUV=(float2(fmod(index,3),floor(index/3))+clamp(q,.01,.99))/float2(3,2);
float tex=Texture2DSample(Drops,DropsSampler,sampleUV).b;
float2 bounds=smoothstep(0,.035,q)*smoothstep(0,.035,1-q);
float core=smoothstep(.025,.60,tex)*bounds.x*bounds.y;
float satellites=0;
[unroll] for(int i=0;i<6;++i)
{
    float h=frac(sin((i+1)*43.17+Seed*31.3)*43758.5453);
    float angle=i*2.39996+Seed*6.283185;
    float2 center=float2(cos(angle),sin(angle))*(.48+h*.30);
    satellites=max(satellites,1-smoothstep(.72,1,length((p-center)/float2(.028+h*.06,.035+h*.075))));
}
float drip=0;
[unroll] for(int j=0;j<3;++j)
{
    float h=frac(Seed*13.13+j*.618);
    float x=(h-.5)*.72;
    // Decal local Z is world up; UE decal UV.x follows local Z, so gravity is -p.x.
    float lengthDown=(.15+.45*h)*smoothstep(0,2.1,age);
    float down=-p.x;
    float line=(1-smoothstep(.008,.024,abs(p.y-x)))*smoothstep(-.08,.05,down)
        *(1-smoothstep(lengthDown-.025,lengthDown+.025,down));
    drip=max(drip,line*Wall);
}
float2 edge=smoothstep(0,.04,UV)*smoothstep(0,.04,1-UV);
return saturate(max(max(core,satellites),drip)*edge.x*edge.y);
