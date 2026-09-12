// Object UVs follow the skinned gun. No world-space projection or added decals.
float2 slope=0;float beads=0;
[unroll] for(int layer=0;layer<2;layer++)
{
    float2 q=UV*(layer==0?float2(78,78):float2(31,31));
    float2 id=floor(q);
    float3 h=frac(sin(float3(dot(id,float2(127.1,311.7)),dot(id,float2(269.5,183.3)),dot(id,float2(419.2,371.9)))+layer*11)*43758.5453);
    float2 p=frac(q)-lerp(.24,.76,h.xy);
    float radius=lerp(.085,.19,h.z);
    float2 shape=p/float2(radius,radius*lerp(1,1.3,h.x));
    float r2=dot(shape,shape);
    float birth=smoothstep(h.z-.08,h.z+.08,saturate(Wet)*.92);
    float bead=(1-smoothstep(.7,1,r2))*birth;
    slope+=shape*sqrt(saturate(1-r2))*bead*.50;
    beads=max(beads,bead);
}
return float4(slope,beads,saturate(Wet));
