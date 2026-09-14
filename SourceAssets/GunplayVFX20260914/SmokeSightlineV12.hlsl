// Preserve fresh muzzle smoke. Only older, expanded layers receive a gentle
// reduction in the immediate aim area; no broad quarter-opacity screen mask.
float2 offset = (ViewportUV - 0.5) * ViewportSize / max(ViewportSize.y, 1.0);
float center = 1.0 - smoothstep(0.025, 0.11, length(offset));
float expanded = smoothstep(0.20, 0.65, saturate(ParticleAge));
return Opacity * (1.0 - 0.40 * center * expanded);
