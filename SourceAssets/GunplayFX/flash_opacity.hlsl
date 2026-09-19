float2 p = (UV - 0.5) * 2.0;
float angle = atan2(p.y, p.x) + Seed;
float lobes = 0.76 + 0.16 * sin(angle * 5.0) + 0.08 * cos(angle * 9.0 + Seed);
float radius = length(p) / max(lobes, 0.35);
float fringe = 0.84 + 0.16 * sin(p.x * 25.0 + sin(p.y * 16.0) + Seed);
return pow(saturate(1.0 - radius), 1.25) * fringe;
