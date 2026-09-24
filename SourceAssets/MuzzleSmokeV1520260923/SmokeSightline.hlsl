float2 offset = (ViewportUV - 0.5) * ViewportSize / max(ViewportSize.y,1.0);
float center = 1.0 - smoothstep(0.020,0.085,length(offset));
float expanded = smoothstep(0.12,0.60,saturate(ParticleAge));
// Preserve smoke outside the small aiming area instead of fading the whole view.
return Opacity * (1.0 - center * saturate(SightProtection) * lerp(0.65,1.0,expanded));
