// Rest coordinates are baked into UV0, so these masks follow skinning and ragdoll.
struct OrganicNoise
{
    float Hash(float3 p)
    {
        p = frac(p * 0.1031);
        p += dot(p, p.yzx + 33.33);
        return frac((p.x + p.y) * p.z);
    }
    float Noise(float3 p)
    {
        float3 i = floor(p), f = frac(p);
        f = f * f * (3.0 - 2.0 * f);
        return lerp(lerp(lerp(Hash(i), Hash(i+float3(1,0,0)), f.x),
                         lerp(Hash(i+float3(0,1,0)), Hash(i+float3(1,1,0)), f.x), f.y),
                    lerp(lerp(Hash(i+float3(0,0,1)), Hash(i+float3(1,0,1)), f.x),
                         lerp(Hash(i+float3(0,1,1)), Hash(i+float3(1,1,1)), f.x), f.y), f.z);
    }
};
OrganicNoise organic;
float3 P = Rest * float3(50,210,115) + float3(-25,-115,-5);
float coarse = organic.Noise(P * .38 + Seed * .019);
float fine = organic.Noise(P * 1.8 + Seed * .071);
float irregularity = (coarse-.5)*.24 + (fine-.5)*.08;
float4 Centers[8] = {C0,C1,C2,C3,C4,C5,C6,C7};
float4 AxisU[8] = {U0,U1,U2,U3,U4,U5,U6,U7};
float4 AxisV[8] = {V0,V1,V2,V3,V4,V5,V6,V7};
float4 AxisN[8] = {N0,N1,N2,N3,N4,N5,N6,N7};
float exposed = 0, wound = 0;
[unroll] for (int i=0; i<8; ++i)
{
    float3 delta = P - Centers[i].xyz;
    float3 q = float3(dot(delta,AxisU[i].xyz)/max(AxisU[i].w,.1),
                      dot(delta,AxisV[i].xyz)/max(AxisV[i].w,.1),
                      dot(delta,AxisN[i].xyz)/max(AxisN[i].w,.1));
    float distance = length(q) + irregularity;
    float active = step(.01,Centers[i].w);
    exposed = max(exposed,(1-smoothstep(.9,1.35,distance))*active);
    wound = max(wound,(1-smoothstep(.25,.93,distance))*Centers[i].w);
}
// Keep the face, feet and tail outside the procedural wound field.
float body = (1-smoothstep(49,55,P.y))*smoothstep(20,28,P.z)*smoothstep(-48,-38,P.y);
exposed = max(exposed*body,FixedWound);
wound = max(wound*body,FixedWound*.9);
return float4(saturate(exposed),saturate(wound),fine,coarse);
