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
float3 light = max(scene, 0.0) * frameExposure;
float luma = dot(light, float3(0.2126, 0.7152, 0.0722));
// Warm practical lights can wash out the red channel before luminance peaks.
float level = lerp(luma, max(light.r, max(light.g, light.b)), 0.40);
const float knee = 0.45;
if (level <= knee)
    return scene;

// Unit slope at the knee, with no hard clip on bright cheek and cloth detail.
const float shoulder = 0.42;
float mapped = knee + shoulder * log(1.0 + (level - knee) / shoulder);
return scene * (mapped / level);
