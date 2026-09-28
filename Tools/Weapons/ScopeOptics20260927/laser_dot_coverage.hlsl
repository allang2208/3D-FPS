// The runtime uses a flattened /Engine/BasicShapes/Sphere (radius 50 cm).
// Fade just the rim using this frame's pixel footprint, without TAA history.
float Radius = length(LocalPosition.xy) / 50.0;
float EdgeWidth = max(fwidth(Radius), 0.025);
float Coverage = saturate((1.0 - Radius) / EdgeWidth);

// AfterMotionBlur is unjittered but scene depth still has camera jitter.
// Allow the spot plane's one-pixel depth footprint to avoid self-occlusion
// on sloping receivers. Only use the spot's derivative, never a foreground
// depth discontinuity that could incorrectly open a hole in an occluder.
float DepthFootprint = fwidth(PixelDepth);
float Visibility = saturate((SceneDepth - PixelDepth + DepthFootprint + 0.03)
    / max(DepthFootprint, 0.03));
return Coverage * Visibility;
