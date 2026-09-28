// Smooth world-space variation without an additional texture or simulation.
// The analytic gradient keeps displaced wave heights and normals consistent.
struct GodSpaceOceanNoise
{
    float hash(float2 p)
    {
        float3 q = frac(float3(p.x, p.y, p.x) * .1031);
        q += dot(q, q.yzx + 33.33);
        return frac((q.x + q.y) * q.z);
    }
    float3 value_gradient(float2 p)
    {
        float2 cell = floor(p), f = frac(p);
        float a = hash(cell), b = hash(cell + float2(1, 0));
        float c = hash(cell + float2(0, 1)), d = hash(cell + 1);
        float2 w = f*f*f*(f*(f*6-15)+10);
        float2 dw = 30*f*f*(f-1)*(f-1);
        float crossTerm = a-b-c+d;
        return float3(a+(b-a)*w.x+(c-a)*w.y+crossTerm*w.x*w.y,
            ((b-a)+crossTerm*w.y)*dw.x,
            ((c-a)+crossTerm*w.x)*dw.y);
    }
};
