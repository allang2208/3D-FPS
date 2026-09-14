// Project-authored low-contrast density, shared in world space across smoke layers.
// Avoid atlas puff silhouettes; the same moving field passes through overlapping sprites.
struct FGunSmokeField
{
    float Hash(float3 p)
    {
        p = frac(p * 0.1031);
        p += dot(p, p.yzx + 33.33);
        return frac((p.x + p.y) * p.z);
    }
    float Noise(float3 p)
    {
        float3 cell = floor(p);
        float3 f = frac(p);
        f = f * f * (3.0 - 2.0 * f);
        float n0 = lerp(lerp(Hash(cell), Hash(cell + float3(1,0,0)), f.x),
                        lerp(Hash(cell + float3(0,1,0)), Hash(cell + float3(1,1,0)), f.x), f.y);
        float n1 = lerp(lerp(Hash(cell + float3(0,0,1)), Hash(cell + float3(1,0,1)), f.x),
                        lerp(Hash(cell + float3(0,1,1)), Hash(cell + float3(1,1,1)), f.x), f.y);
        return lerp(n0, n1, f.z);
    }
};
FGunSmokeField field;
float3 p = PositionWS * 0.055 + float3(Clock * 0.12, -Clock * 0.09, -Clock * 0.25);
float coarse = field.Noise(p);
float detail = field.Noise(p * 2.05 + coarse * 0.7);
float density = lerp(0.48, 0.95, smoothstep(0.1, 0.9, coarse * 0.72 + detail * 0.28));
float2 q = (SpriteUV - 0.5) * 2.0;
float radius = length(q);
float feather = exp2(-2.4 * radius * radius) * (1.0 - smoothstep(0.58, 1.0, radius));
return saturate(density * feather);
