// Filter the grey fringe over its screen-space footprint. Keep a weak veil
// between the bright body and transparent background, without a clip threshold.
float a = saturate(Opacity);
float width = clamp(fwidth(a) * 0.65, 0.002, 0.14);
float body = smoothstep(0.0, 0.64, a) * 0.40;
body += smoothstep(0.0, 0.64, a - width) * 0.15;
body += smoothstep(0.0, 0.64, a + width) * 0.15;
body += smoothstep(0.0, 0.64, a - width * 0.5) * 0.15;
body += smoothstep(0.0, 0.64, a + width * 0.5) * 0.15;
return a * lerp(0.18, 1.0, body) * saturate(ParticleAlpha);
