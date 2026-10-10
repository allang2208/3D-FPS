// Sword native_gold_fade approach: visible metal remains while only light moves.
float time = PreviewTime >= 0 ? PreviewTime : T;
float along = 1.0-saturate(UV.y);
float phase = frac(time * .125);
float endFade = smoothstep(0,.16,phase)*(1-smoothstep(.82,1,phase));
float wave = exp2(-pow((along-phase)/.17,2)*2)*endFade;
float breath = smoothstep(.04,.96,.5+.5*sin(time*BreathSpeed-along*3.3));
float edgeDetail = smoothstep(.23,.72,Field.a);
float intensity = GlowStrength*(.20+.38*breath+.30*wave)*edgeDetail;
float3 emission=GlowColor*intensity;
float peak=max(emission.r,max(emission.g,emission.b));
return emission*min(1.,EmissionPeak/max(peak,.0001));
