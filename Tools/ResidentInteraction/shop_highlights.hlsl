// Input0 is linear HDR with the view's pre-exposure, at the native depth resolution.
// All depth/stencil nodes use the current view's UVs and point sampling.
float3 scene = SceneInput.rgb;
float stencil = ResidentId.r;
if (stencil < 175.5 || stencil > 191.5)
    return scene;
uint slot = (uint)(stencil + 0.5) - 176u;
if (((uint)VisibleSlots & (1u << slot)) == 0u)
    return scene;

// Reject both an occluding prop and a background texel at a silhouette.
// Scene depth and custom depth are linear distances in centimetres.
float tolerance = max(0.8, VisibleDepth.r * 0.00015);
if (abs(ResidentDepth.r - VisibleDepth.r) > tolerance)
    return scene;

// Only the decision about the knee needs exposure-relative units. Keep the RGB
// in its original representation throughout, including for split-screen cameras.
float frameExposure = EyeExposure > 0.0 ? EyeExposure * View.OneOverPreExposure : 1.0;
float luminance = dot(max(scene, 0.0), float3(0.2126, 0.7152, 0.0722)) * frameExposure;
const float knee = 0.70;
if (luminance <= knee)
    return scene;

// Unit slope at the knee, positive slope everywhere. Even the brightest
// values retain at least 57.5% of their original radiance (about -0.80 EV).
float over = luminance - knee;
float reduction = 0.425 * (over / luminance) * (over / (over + 0.55));
return scene * (1.0 - reduction);
