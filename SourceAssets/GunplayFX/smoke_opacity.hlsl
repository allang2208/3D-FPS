float2 p = (UV - 0.5) * 2.0;
float low = sin(p.x * 4.2 + Seed) * cos(p.y * 3.7 + Seed * 1.6);
float mid = sin(p.x * 10.5 + sin(p.y * 7.2) + Seed * 2.3);
float fine = sin(p.x * 23.0 + p.y * 17.5 + Seed * 3.1);
float density = saturate(0.64 + 0.19 * low + 0.12 * mid + 0.05 * fine);
float edge = saturate(1.0 - length(p) + low * 0.09);
return smoothstep(0.0, 0.35, edge) * density * saturate(edge * 1.3);
