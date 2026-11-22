// AllWeaponRuneFlow20261102: keep the UV-baked glyph fixed on the blade.
// Only its light travels, in blade-local centimetres, from root to tip.
float time = PreviewTime >= 0 ? PreviewTime : T;
float along = saturate((P.z - BladeStart) / max(BladeLength, .01));
float phase = frac(time * .13);
float edge = smoothstep(0, .15, phase) * (1 - smoothstep(.82, 1, phase));
float center = lerp(-.20, 1.20, phase);
float wave = exp2(-pow((along - center) / .15, 2) * 2) * edge;
float breath = smoothstep(.04, .96, .5 + .5 * sin(time * 1.12 - along * 2.2));
// Normalize hue so the dark slate peaks can glow without changing their metal.
float3 tint = RuneTint / max(max(RuneTint.r, max(RuneTint.g, RuneTint.b)), .04);
float3 emission = tint * saturate(Ink) * GlowStrength * (.12 + .20 * breath + .68 * wave);
float peak = max(emission.r, max(emission.g, emission.b));
return emission * min(1., .85 / max(peak, .0001));
