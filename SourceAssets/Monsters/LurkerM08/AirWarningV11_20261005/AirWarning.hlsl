// UV.x increases from the outer end of each ribbon to the pressure core.
// Layer.r: rings=0, ribbons=0.5, core=1. CPD is driven by the attack clock.
float p = saturate(Progress);
float locked = saturate(Locked);
float rings = 1.0 - step(0.25, Layer.r);
float core = step(0.75, Layer.r);
float streams = 1.0 - rings - core;
float edge = pow(saturate(sin(UV.y * 3.14159265)), 0.55);
float flow = 0.5 + 0.5 * sin(UV.x * 12.5663706 - p * 37.6991118);
float streak = smoothstep(0.30, 0.90, flow);
// Slow modulation has a high floor; the readable warning never blinks off.
float pulse = lerp(0.92 + 0.08 * sin(p * 12.5663706), 1.0, locked);
float ringAlpha = 0.78;
float streamAlpha = edge * (0.30 + 0.55 * streak);
float coreAlpha = lerp(0.38, 0.80, p) * (0.8 + 0.2 * edge);
float alpha = saturate(Visibility * pulse * (rings * ringAlpha + streams * streamAlpha + core * coreAlpha));
float3 amber = float3(1.0, 0.085, 0.0025);
float3 readyWhite = float3(1.0, 0.85, 0.60);
float3 color = lerp(amber, readyWhite, locked);
float brightness = (5.8 + 5.0 * p + 4.0 * locked) * (1.0 + core * 0.35);
return float4(color * brightness * pulse, alpha);
