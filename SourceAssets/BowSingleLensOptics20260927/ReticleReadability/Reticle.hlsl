// Physical lens UVs: centre (0.5,0.5), rim radius 0.5. No screen overlay.
// Distances below are in rendered pixels, giving stable minimum line coverage.
float2 p = (UV - 0.5) * 2.0;
float2 px = max(fwidth(p), float2(0.00001, 0.00001));
float2 q = abs(p);
float2 gap = max(float2(0.035, 0.035), px * 3.1);
float2 halfWidth = max(float2(0.003, 0.003) / px, float2(0.575, 0.575));
float h = max(max(q.x - 0.93, gap.x - q.x) / px.x, q.y / px.y - halfWidth.y);
float v = max(max(q.y - 0.93, gap.y - q.y) / px.y, q.x / px.x - halfWidth.x);
float d = min(h, v);
// A more legible 3.6-pixel aim point; the fine etched guides keep their width.
float centreDistance = length(p / px) - 1.8;
d = min(d, centreDistance);
if (FourPower > 0.5)
{
    // Unnumbered lower references, attached to the same physical glass UVs.
    float t1 = max((q.x - 0.05) / px.x, abs(p.y + 0.12) / px.y - halfWidth.y);
    float t2 = max((q.x - 0.05) / px.x, abs(p.y + 0.24) / px.y - halfWidth.y);
    d = min(d, min(t1, t2));
}
float core = 1.0 - smoothstep(-0.5, 0.5, d);
// Narrow etched edge, rather than a heavy graphic border. Retain AA coverage.
float outline = 1.0 - smoothstep(-0.25, 0.75, d);
// The aim point gets slightly stronger contrast on bright backgrounds.
outline = max(outline, 1.0 - smoothstep(-0.10, 0.90, centreDistance));
// Illumination is concentrated near the aim point; the outer guides remain dim.
float illumination = lerp(1.0, 0.16, smoothstep(0.22, 0.78, length(p)));
// Boost only the aim point; keep the etched guides and their falloff unchanged.
float centre = 1.0 - smoothstep(-0.5, 0.5, centreDistance);
return float2(core * illumination + centre * 1.40, outline);
