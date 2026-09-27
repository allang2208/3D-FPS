// Post-process material, after tonemapping. The main scene is sampled directly;
// no SceneCapture, offscreen scene render or extra light is introduced.
float2 viewportUV = GetViewportUV(Parameters);
float2 viewSize = View.ViewSizeAndInvSize.xy;
float shortAxis = min(viewSize.x, viewSize.y);
float alpha = saturate(ScopeAlpha);
float radius = 0.425 * lerp(0.965, 1.0, smoothstep(0.0, 1.0, alpha));
float2 p = (viewportUV - 0.5) * viewSize / shortAxis;
float r = length(p) / radius;

// The entire central 76% of the aperture radius remains an exact scene copy.
// This is presentation, not a change to the selected zoom or ballistic aim.
if (r <= 0.76 || r >= 1.01 || Strength <= 0.0 || alpha <= 0.0)
    return SceneColor.rgb;

float edge = smoothstep(0.76, 0.98, r) * (1.0 - smoothstep(0.99, 1.01, r));
float2 radial = p / max(length(p), 0.00001);
float eye = dot(radial, EyeOffset.rg);
float zoom = saturate((ScopeZoom - 1.0) / 5.0);
float amount = (0.65 + 0.50 * saturate(ScopePSO) + 0.25 * zoom + eye * 6.0)
    * edge * saturate(Strength) * alpha;
float2 pixelOffset = radial * amount * shortAxis / 900.0;
float2 warpedUV = saturate(viewportUV + pixelOffset / viewSize);
float2 sceneUV = ClampSceneTextureUV(ViewportUVToSceneTextureUV(warpedUV, 14), 14);
float3 warped = SceneTextureLookup(sceneUV, 14, true).rgb;

// Subpixel grazing dispersion, limited to the perimeter and mixed down.
float2 fringeUV = saturate(viewportUV + pixelOffset * 1.22 / viewSize);
float3 fringe = SceneTextureLookup(ClampSceneTextureUV(ViewportUVToSceneTextureUV(fringeUV, 14), 14), 14, true).rgb;
warped = lerp(warped, float3(fringe.r, warped.g, fringe.b), 0.16 * edge);
float3 coating = lerp(float3(0.997, 1.001, 1.003), float3(1.003, 1.000, 0.993), saturate(ScopePSO));
return warped * lerp(float3(1, 1, 1), coating, edge * alpha);
