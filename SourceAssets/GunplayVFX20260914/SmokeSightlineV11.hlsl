// Only used by the owner's cosmetic muzzle smoke, never gameplay smoke volumes.
// Keep some smoke through the aim point and blend over a broad area: no cutout.
float2 offset = (ViewportUV - 0.5) * ViewportSize / max(ViewportSize.y, 1.0);
float sightBlend = smoothstep(0.04, 0.24, length(offset));
return Opacity * lerp(0.25, 1.0, sightBlend);
