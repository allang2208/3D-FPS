// Four 32-frame impulses, 8 columns x 16 rows. Each hit plays one full impulse.
float frame = saturate(Age) * 31;
float first = floor(frame);
float variantIndex = min(floor(Variant * 4), 3);
float endFrame = EndFrames[(int)variantIndex];
float sequence = variantIndex * 32;
// The FLIP source is empty after this frame. Do not sample a lower mip that
// might blend a neighbouring tile back into a completed splash.
if (first >= endFrame)
{
#if PIXELSHADER
    clip(-1);
#endif
    return float4(.5,.5,0,0);
}
float i0 = sequence + first;
float i1 = sequence + min(first + 1, 31);
float mirror = frac(Variant * 17.31) > .5 ? -1 : 1;
float2 localUV = UV;
localUV.x = .5 + (localUV.x - .5) * mirror;
localUV = clamp(localUV, .5 / 128, 127.5 / 128);
float2 uv0 = (float2(fmod(i0, 8), floor(i0 / 8)) + localUV) / float2(8, 16);
float2 uv1 = (float2(fmod(i1, 8), floor(i1 / 8)) + localUV) / float2(8, 16);
float4 a = Texture2DSample(Atlas, AtlasSampler, uv0);
float4 b = first + 1 < endFrame ? Texture2DSample(Atlas, AtlasSampler, uv1) : float4(.5,.5,0,0);
// Coverage-weighted interpolation prevents empty texels flattening moving rims.
float weight = frac(frame);
float rawCoverage = lerp(a.a, b.a, weight);
// BC7/mip filtering can leave tiny non-zero coverage outside the liquid.
// Front-layer depth treats any non-zero opacity as a surface; keep blanks exact.
float coverage = saturate((rawCoverage - .008) / .992);
float3 fields = lerp(a.rgb * a.a, b.rgb * b.a, weight) / max(rawCoverage, .001);
fields = lerp(float3(.5,.5,0), fields, smoothstep(0,.03,coverage));
fields.r = .5 + (fields.r - .5) * mirror;
#if PIXELSHADER
// An empty sprite pixel must contribute neither color nor a surface/depth.
clip(coverage - .00001);
#endif
return float4(fields, coverage);
