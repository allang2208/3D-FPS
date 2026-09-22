// Retain the original blade AND guard UV ink and their common length phase.
// Only the emitted light fades; the engraved gold remains part of the metal.
float time = PreviewTime >= 0 ? PreviewTime : T;
float phase = frac(time * .13);
float edge = smoothstep(0, .15, phase) * (1 - smoothstep(.82, 1, phase));
float wave = exp2(-pow((Mask.b - phase) / .14, 2) * 2) * edge;
float breath = smoothstep(.04, .96, .5 + .5 * sin(time * 1.12 - Mask.b * 2.2));
float pulse = lerp(.42, .86, breath) + BreathStrength * (.5 + .5 * sin(time * .83 - Mask.b * 3.1));
float core = Mask.r * GlowStrength * (pulse + FlowStrength * .65 * wave);
float halo = Mask.g * GlowStrength * .065 * (.32 + .68 * breath);
float3 emission = GlowColor * (core + halo) * saturate(GoldAmount);
float peak = max(emission.r, max(emission.g, emission.b));
return emission * min(1.0, 1.35 / max(peak, .0001));
