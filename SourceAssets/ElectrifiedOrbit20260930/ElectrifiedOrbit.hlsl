// V3: open, branched lightning fragments. There is no continuous ring baseline.
// UV.x is 0..1 along each fragment; integer pairs distinguish the branches.
float facing = saturate(abs(dot(normalize(NormalWS), normalize(ViewVector))));
float core = pow(facing, 5.0);
float along = frac(UV.x);
float strand = floor(UV.x * 0.5);
float clock = Time * (11.0 + abs(Speed) * 7.0) + Phase * 7.0 + strand * 0.37;
float tick = floor(clock);
float random = frac(sin(tick * 31.17 + Phase * 79.3 + strand * 13.7) * 43758.5453);
float pulse = (0.18 + 0.82 * exp2(-frac(clock) * 3.5)) * step(0.17, random);
float charge = exp2(-frac(along - Time * Speed * 4.0 + Phase) * 9.0);
float gap = smoothstep(0.13, 0.34, abs(sin(along * 16.0 + tick * 1.87 + strand)));
float ends = smoothstep(0.0, 0.09, along) * (1.0 - smoothstep(0.88, 1.0, along));
float opacity = (0.11 * facing + 0.89 * core) * ends * gap * pulse;
float3 violet = float3(0.24, 0.09, 1.0);
float3 whiteCore = float3(0.77, 0.85, 1.0);
float3 color = lerp(violet, whiteCore, core);
float energy = (5.0 + 4.0 * charge) * (1.0 + 0.7 * saturate(Flash));
return float4(color * energy / max(Exposure, 0.001), saturate(opacity));
