// P is the engine cylinder's unscaled local position (centimetres).
// WorldScale comes through a vertex interpolator: dynamic rod length affects
// axial distance, not braid pitch. Integer angular harmonics keep the seam closed.
float angle = atan2(P.y, P.x);
float axial = P.z * abs(WorldScale.z) * 6.28318530718 / max(PitchCM, 0.01);
float phase = angle * 2.0 - axial;
float opposite = angle * 3.0 + axial;
// Fade undersampled strands to their mean rather than shimmering at a distance.
float ridge = 0.5 + 0.5 * cos(phase) * saturate(1.0 - fwidth(phase) * 0.31831);
float cross = 0.5 + 0.5 * cos(opposite) * saturate(1.0 - fwidth(opposite) * 0.31831);
float pattern = lerp(ridge, (ridge + cross) * 0.5, Weave);
float microPhase = angle * 18.0 - axial * 7.0;
float fiber = cos(microPhase) * saturate(1.0 - fwidth(microPhase) * 0.31831);
float tracerPhase = angle - axial;
float tracerWave = 0.5 + 0.5 * cos(tracerPhase);
float tracer = lerp(0.025, pow(saturate(tracerWave), 16.0) * 0.18,
    saturate(1.0 - fwidth(tracerPhase) * 1.5)) * (1.0 - Weave);
float3 color = lerp(Dark, Light, 0.2 + pattern * 0.8);
color = lerp(color, Tracer, tracer) * (1.0 + fiber * 0.055);
return float4(color, clamp(Roughness + (0.5-pattern)*0.07 - fiber*0.025, 0.5, 0.95));
