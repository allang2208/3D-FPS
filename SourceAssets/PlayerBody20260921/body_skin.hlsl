// Authored for the player's full body. Procedural detail, not a scanned texture.
// Kept independent of the first-person glove/sleeve masks and mannequin normals.
struct BodySkinFields
{
    float hash(float2 p)
    {
        return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453);
    }
    float noise(float2 p)
    {
        float2 i = floor(p);
        float2 f = frac(p);
        f = f * f * (3.0 - 2.0 * f);
        return lerp(lerp(hash(i), hash(i + float2(1, 0)), f.x),
                    lerp(hash(i + float2(0, 1)), hash(i + 1), f.x), f.y);
    }
};
BodySkinFields field;
float pixelUV = max(length(ddx(UV)), length(ddy(UV)));
float blotch = field.noise(UV * 42.0) - 0.5;
float fine = field.noise(UV * 170.0) - 0.5;
float3 color = SkinTint * (1.0 + blotch * ToneVariation + fine * 0.018);

// Smooth pore depressions. Fade the detail when it falls below pixel size.
float2 poreUV = UV * PoreTiling;
float2 cell = floor(poreUV);
float2 center = 0.36 + 0.28 * float2(field.hash(cell), field.hash(cell + 67.3));
float2 offset = frac(poreUV) - center;
float shape = saturate(1.0 - dot(offset, offset) / 0.055);
float poreVisibility = saturate(1.0 - pixelUV * PoreTiling);
float2 gradient = (6.0 / 0.055) * shape * shape * offset;
OutNormal = normalize(float3(-gradient * SkinDetailStrength * poreVisibility, 1.0));
OutRoughness = clamp(SkinRoughness + blotch * 0.045 + fine * 0.025, 0.32, 0.7);
return saturate(color);
