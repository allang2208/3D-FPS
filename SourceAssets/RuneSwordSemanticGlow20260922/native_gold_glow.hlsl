// Preserve the separate blade/guard UV0 masks and their common length phase.
float time = PreviewTime >= 0.0 ? PreviewTime : T;
float phase = frac(time * .16);
float edge = smoothstep(0.0, .06, phase) * (1.0 - smoothstep(.94, 1.0, phase));
float wave = exp2(-pow((Mask.b - phase) / .085, 2.0) * 3.0) * edge;
float pulse = 1.0 + BreathStrength * sin(time * 1.65);
float core = Mask.r * GlowStrength * (pulse + FlowStrength * wave);
float halo = Mask.g * GlowStrength * .08 * (.90 + .10 * pulse);
float3 emission = GlowColor * (core + halo) * saturate(GoldAmount);
float peak = max(emission.r, max(emission.g, emission.b));
return emission * min(1.0, 1.35 / max(peak, .0001));
