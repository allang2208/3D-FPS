// Same twelve taps, bilinear coverage and occlusion rule as the dungeon's V4 container contour.
float3 scene = ColorInput.rgb;
if (ResidentStencil < 1 || abs(StencilInput.r - ResidentStencil) < .5) return scene;
float2 uv = GetViewportUV(Parameters);
float2 viewPixel = GetSceneTextureViewSize(25).zw;
float2 bufferPixel = GetSceneTextureBufferSize(25).zw;
float coverage = 0;
[unroll] for (int i = 0; i < 12; ++i)
{
    float angle = 6.2831853 * (i / 12.0);
    float2 tap = uv + float2(cos(angle), sin(angle)) * viewPixel * Width;
    if (any(tap < 0) || any(tap > 1)) continue;
    float2 grid = ViewportUVToSceneTextureUV(tap, 25) / bufferPixel - .5;
    float2 base = floor(grid), f = frac(grid);
    float covered = 0;
    [unroll] for (int j = 0; j < 4; ++j)
    {
        float2 corner = float2(j & 1, j >> 1);
        float2 sampleUV = ClampSceneTextureUV((base + corner + .5) * bufferPixel, 25);
        float s = SceneTextureLookup(sampleUV, 25, false).r;
        if (abs(s - ResidentStencil) >= .5) continue;
        float depth = SceneTextureLookup(ClampSceneTextureUV(sampleUV, 13), 13, false).r;
        float visible = SceneTextureLookup(ClampSceneTextureUV(sampleUV, 1), 1, false).r;
        float tolerance = max(1.5, depth * .0001);
        if (depth > visible + tolerance || depth > SceneDepthInput.r + tolerance) continue;
        covered += (corner.x > .5 ? f.x : 1-f.x) * (corner.y > .5 ? f.y : 1-f.y);
    }
    coverage = max(coverage, covered);
}
return lerp(scene, Green.rgb, .72 * smoothstep(0.0, .85, coverage));
