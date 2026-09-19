// V5.1: larger, wider injuries; the UV0 atlas still roots fur to the skin.
struct WoundNoise
{
    float Hash(float3 p)
    {
        p=frac(p*.1031); p+=dot(p,p.yzx+33.33); return frac((p.x+p.y)*p.z);
    }
    float Noise(float3 p)
    {
        float3 i=floor(p), f=frac(p); f=f*f*(3-2*f);
        return lerp(lerp(lerp(Hash(i),Hash(i+float3(1,0,0)),f.x),
            lerp(Hash(i+float3(0,1,0)),Hash(i+float3(1,1,0)),f.x),f.y),
            lerp(lerp(Hash(i+float3(0,0,1)),Hash(i+float3(1,0,1)),f.x),
            lerp(Hash(i+float3(0,1,1)),Hash(i+float3(1,1,1)),f.x),f.y),f.z);
    }
};
WoundNoise noise;
float3 P=Rest*float3(50,210,115)+float3(-25,-115,-5);
float4 Centers[8]={C0,C1,C2,C3,C4,C5,C6,C7};
float4 AxisU[8]={U0,U1,U2,U3,U4,U5,U6,U7};
float4 AxisV[8]={V0,V1,V2,V3,V4,V5,V6,V7};
float4 AxisN[8]={N0,N1,N2,N3,N4,N5,N6,N7};
float4 Styles[8]={S0,S1,S2,S3,S4,S5,S6,S7};
float4 layers=0;
float best=0;
Relief=0; Healing=0; Fibres=.5; FurRemoval=0;
[unroll] for(int i=0;i<8;++i)
{
    // This condition is uniform across a dog's draw, so implicit texture
    // gradients remain valid. Disabled slots perform no atlas lookups.
    if(Centers[i].w>.001)
    {
        float3 delta=P-Centers[i].xyz;
        float lengthScale=i==0 ? 1.65 : 1.75;
        float2 q=float2(dot(delta,AxisU[i].xyz)/max(AxisU[i].w*lengthScale,.1),
                       dot(delta,AxisV[i].xyz)/max(AxisV[i].w*2.0,.1));
        float depth=abs(dot(delta,AxisN[i].xyz))/max(AxisN[i].w*1.30,.1);
        float coverage=(1-smoothstep(.55,1.0,depth))*saturate(Centers[i].w*1.22);
        float style=clamp(floor(Styles[i].x+.5),0,3);
        float healing=saturate(Styles[i].y);
        // Keep a few old scars; most former hairline marks become visible
        // abrasions or patches. This choice is identical on skin and fur.
        float choice=frac(Seed*.381966+i*.618034);
        if(style==2 && (i<3 || choice>.20))
        {
            style=i<3 || choice>.65 ? 3 : 1;
            healing=min(healing,.38);
        }
        if(i<3 && style==1) style=3;
        // Blender atlas tile 0 is bottom left, while texture V grows downward.
        float2 cell=float2(fmod(style,2),1-floor(style*.5));
        float2 uv=(cell+clamp(float2(q.x,-q.y)*.5+.5,.002,.998))*.5;
        float3 m=Texture2DSample(Masks,MasksSampler,uv).rgb;
        float3 d=Texture2DSample(Detail,DetailSampler,uv).rgb;
        float4 local=float4(m.g,m.r,m.b,d.g)*coverage;
        layers=max(layers,local);
        float score=max(local.y,local.z)+local.x*.1;
        if(score>best)
        {
            best=score;
            Relief=(d.r-.5)*Styles[i].z*coverage;
            Healing=healing;
            Fibres=d.b;
        }
    }
}
float body=(1-smoothstep(49,55,P.y))*smoothstep(20,28,P.z)*smoothstep(-48,-38,P.y);
layers*=body; Relief*=body;
// A dry, subdued cap on the existing physical ear cut.
layers=lerp(layers,float4(1,.18,.7,.12),FixedWound);
Relief*=1-FixedWound; Healing=lerp(Healing,.88,FixedWound);
float clumps=noise.Noise(P*1.7+Seed*.019);
float fringe=saturate(layers.x-layers.y);
float brokenEdge=layers.x+(clumps-.5)*.30*fringe;
FurRemoval=max(smoothstep(.22,.88,brokenEdge),smoothstep(.18,.6,layers.y));
return saturate(layers);
