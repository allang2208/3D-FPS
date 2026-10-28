// Local screen border only: translucent red tongues, soft heat and sparse embers.
struct FlameField
{
    float Hash(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
    float Noise(float2 p)
    {
        float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);
        return lerp(lerp(Hash(i),Hash(i+float2(1,0)),f.x),
            lerp(Hash(i+float2(0,1)),Hash(i+1),f.x),f.y);
    }
    float Tongue(float along,float inward,float t,float seed)
    {
        float2 q=float2(along*13+seed,inward*5-t*1.3);
        float n=Noise(q)*.64+Noise(q*2.1+float2(t*.16,3.7))*.36;
        float warp=Noise(float2(along*6+seed,t*.45))*2-1;
        float crest=.26+.53*n+.11*sin(along*31+t*1.5+warp*3);
        float shape=1-smoothstep(crest-.17,crest+.08,inward);
        float root=exp(-inward*4.5)*.32;
        float filament=pow(saturate(n+.19-inward*.38),3.4)*shape;
        return saturate((shape*.43+filament*.64+root)*(1-smoothstep(.68,1.05,inward)));
    }
};
FlameField F;
float2 d=min(UV,1-UV);
// No shader work or tint within the clear central viewport.
if(d.x>.17&&d.y>.18)return float4(0,0,0,0);
float t=Age;
float left=F.Tongue(1-UV.y,UV.x/.15,t,4.1);
float right=F.Tongue(1-UV.y,(1-UV.x)/.15,t+1.7,19.4);
float bottom=F.Tongue(UV.x,(1-UV.y)/.18,t,31.7);
float top=F.Tongue(1-UV.x,UV.y/.105,t*.76,47.1)*.65;
float flame=max(max(left,right),max(bottom,top));
float halo=exp(-min(d.x/.067,d.y/.065)*3)*.12;
float breath=.93+.07*sin(t*2.2);
float a=saturate((flame*.30+halo)*Strength*breath*(1+.45*EntryBurst));
float core=saturate(flame*1.25);
float3 red=lerp(float3(.34,.002,.012),float3(1,.035,.045),core);
return float4(red,a);
