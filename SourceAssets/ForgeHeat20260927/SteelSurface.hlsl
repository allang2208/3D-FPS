// Object-space centimeters: fine fractured scale, hammer pits and rolled grain.
// Stable on all three blank meshes; independent of their smart-projected UVs.
struct ForgeNoise
{
    float hash(float3 p) { return frac(sin(dot(p,float3(127.1,311.7,74.7)))*43758.5453); }
    float noise(float3 p)
    {
        float3 i=floor(p),f=frac(p);f=f*f*(3-2*f);
        return lerp(lerp(lerp(hash(i),hash(i+float3(1,0,0)),f.x),
                         lerp(hash(i+float3(0,1,0)),hash(i+float3(1,1,0)),f.x),f.y),
                    lerp(lerp(hash(i+float3(0,0,1)),hash(i+float3(1,0,1)),f.x),
                         lerp(hash(i+float3(0,1,1)),hash(i+float3(1,1,1)),f.x),f.y),f.z);
    }
};
ForgeNoise n;
float coarse=n.noise(P*float3(.7,1.2,1.1));
float chips=n.noise(P*5.2+coarse*2.1);
float grain=n.noise(P*float3(4,36,19));
float cracks=1-smoothstep(.02,.095,abs(chips-.5));
float oxide=smoothstep(.51,.7,coarse*.38+chips*.62)*(1-cracks*.65);
float pits=pow(saturate(1-n.noise(P*float3(2.2,3.5,3.5))),3);
float height=(grain-.5)*.007-pits*.035+oxide*.014;
float temperature=n.noise(P*float3(.17,.35,.4));
return float4(oxide,grain,height,temperature);
