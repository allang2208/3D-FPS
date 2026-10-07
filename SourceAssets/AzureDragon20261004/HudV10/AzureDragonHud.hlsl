// Azure Dragon energy HUD V10: UI-domain translucent material body (Slate NoGamma, display space).
// HudLayout.hlsl is prepended by install_hud_ue.py. hud_preview.py is the offline twin; keep in step.
// Inputs: UV, Fill, Age, Pulse, Burst, Reveal, BodyOpacity, EmptyTex, FullTex, MaskTex, NoiseTex, GlyphTex.
struct AzureHudFn
{
    float SS(float a, float b, float x) { float t = saturate((x - a) / (b - a)); return t * t * (3.0 - 2.0 * t); }
    float Hash(float x) { return frac(sin(x) * 43758.5453); }
};
AzureHudFn Fn;
const float TwoPi = 6.28318530718;

float2 P = float2(UV.x * HudSize.x, HudQuadTop + UV.y * (HudSize.y - HudQuadTop));
float2 T = P / HudSize;
float inTex = step(0.0, P.y);
float fillV = saturate(Fill);
float f9 = fillV * 9.0;
int seg = (int)min(floor(f9), 8.0);
float menY = lerp(HudLevels[seg], HudLevels[seg + 1], f9 - seg);
float charged = fillV > 0.001 ? 1.0 : 0.0;
float zone = Fn.SS(HudTopBoundary - 16.0, HudTopBoundary + 16.0, P.y);
float capV = Fn.SS(8.4 / 9.0, 1.0, fillV);
float wave = 1.6 * sin(P.x * 0.09 + Age * 3.1) + 1.0 * sin(P.x * 0.21 - Age * 4.7);
float below = Fn.SS(menY - 1.5, menY + 1.5, P.y + wave) * charged;
float mixV = zone * below + (1.0 - zone) * (0.20 + 0.45 * capV);
float4 msk = Texture2DSample(MaskTex, MaskTexSampler, T) * inTex;
float sil = msk.r, inner = msk.g, glow = msk.b, env = msk.a;
float3 col = Texture2DSample(EmptyTex, EmptyTexSampler, T).rgb * inTex * (1.0 - mixV)
           + Texture2DSample(FullTex, FullTexSampler, T).rgb * inTex * (1.0 + 0.35 * Pulse + 0.4 * Burst) * mixV;
float baseLum = max(col.r, max(col.g, col.b));

// Energy streaks flowing up inside the charged glass.
float n1 = Texture2DSample(NoiseTex, NoiseTexSampler, float2(P.x / 520.0 + 0.13 * sin(Age * 0.3), P.y / 1100.0 + Age * 0.06)).g;
float n2 = Texture2DSample(NoiseTex, NoiseTexSampler, float2(P.x / 330.0 + 0.37, P.y / 700.0 + Age * 0.045)).g;
col += pow(n1 * n2, 1.5) * inner * below * zone * 0.30 * float3(0.15, 0.85, 1.0);

// Meniscus line and brighter liquid just beneath it.
float dm = P.y + wave - menY;
float men = (exp(-dm * dm / (2.0 * 2.2 * 2.2)) * 0.95 + exp(-max(dm, 0.0) / 14.0) * (dm > 0.0 ? 0.15 : 0.0)) * inner * zone * charged;
col += men * float3(0.75, 1.0, 1.0);

// Inner flames above the surface.
float hgt = menY - P.y;
float flen = 170.0 + 90.0 * fillV;
float nf = 0.65 * Texture2DSample(NoiseTex, NoiseTexSampler, float2(P.x / 80.0, P.y / 320.0 + Age * 0.30)).r
         + 0.35 * Texture2DSample(NoiseTex, NoiseTexSampler, float2(P.x / 45.0 + 0.5, P.y / 160.0 + Age * 0.45)).a;
float rel = hgt / flen;
float edge0 = 0.44 + 0.24 * rel;
float et = (nf - edge0) / 0.022;
float tongueIn = (Fn.SS(edge0, edge0 + 0.14, nf) * 0.70 + exp(-et * et) * 0.65) * (hgt > 0.0 ? 1.0 : 0.0) * (rel < 1.0 ? 1.0 : 0.0);
col += tongueIn * sqrt(saturate(1.0 - rel)) * inner * zone * charged * (0.9 + 0.5 * Burst) * float3(0.25, 0.95, 1.0);

// Outer flames: soft tongues and strands around the charged vessel, a crown above the head when full.
float reach = 110.0 + 330.0 * fillV + 150.0 * Burst;
float vfade = saturate(1.0 - (menY - P.y) / reach);
float amount = min(1.0, 0.45 + 0.55 * fillV + 0.6 * Burst);
float4 wx = Texture2DSample(NoiseTex, NoiseTexSampler, float2(P.x / 700.0 + 0.4, P.y / 1000.0 + Age * 0.05));
float qx = P.x / 300.0 + (wx.b - 0.5) * 0.45;
float qy = P.y / 820.0 + Age * 0.17 + (wx.r - 0.5) * 0.35;
float nA = Texture2DSample(NoiseTex, NoiseTexSampler, float2(qx, qy)).r;
float nB = Texture2DSample(NoiseTex, NoiseTexSampler, float2(qx * 2.3 + 0.17, qy * 2.0 + Age * 0.05)).a;
float hx = (P.x - HudHeadX) / 80.0;
float plume = capV * exp(-hx * hx) * Fn.SS(HudQuadTop + 10.0, 80.0, P.y) * Fn.SS(HudTopBoundary + 40.0, HudTopBoundary - 160.0, P.y);
float shapeF = ((pow(glow, 0.9) * 0.70 + pow(env, 3.0) * 0.25) * (1.0 - 0.55 * (1.0 - zone)) + plume * 1.1) * vfade * charged;
float dens = shapeF * amount * pow(nA * 0.75 + nB * 0.45, 1.5) * 2.6;
float strands = Texture2DSample(NoiseTex, NoiseTexSampler, float2(qx * 1.4 + (nA - 0.5) * 0.5, qy * 1.1 + 0.31)).g * Fn.SS(0.05, 0.30, dens);
float tongueOut = Fn.SS(0.30, 0.85, dens) * 0.42 + (Fn.SS(0.10, 0.26, dens) - Fn.SS(0.26, 0.50, dens)) * 0.55;
float fire = (tongueOut + strands * 0.70) * (1.0 - 0.85 * inner) * (1.0 - 0.65 * (1.0 - zone) * Fn.SS(0.80, 1.0, glow));
float crown = Fn.SS(HudTopBoundary - 250.0, HudTopBoundary - 420.0, P.y) * capV;
float3 fireCol = float3(0.18, 0.88, 1.0) * (1.0 - crown * 0.6) + float3(0.28, 0.45, 1.0) * crown * 0.6;
col += fire * fireCol * 1.1;

// Halo.
col += glow * (0.04 + 0.08 * fillV + 0.2 * Pulse + 0.3 * Burst) * float3(0.20, 0.75, 0.85);

// Helical rune ribbon: rotating the helix equals travelling along the band.
float sR = (HudCenter - P.x) / HudRibbon.x;
float okR = abs(sR) < 0.999 ? 1.0 : 0.0;
float sC = clamp(sR, -0.999, 0.999);
float phi = Age * 0.45;
float amax = TwoPi * HudRibbonTurns;
float halfT = HudRibbon.z * 0.5;
float ribF = 0.0, ribB = 0.0;
[unroll] for (int side = 0; side < 2; ++side)
{
    float theta = side == 0 ? asin(sC) : 3.14159265 - asin(sC);
    float a0 = theta - phi;
    float kk = round(((P.y - HudRibbon.w) / HudRibbon.y * TwoPi - a0) / TwoPi);
    float alpha = a0 + TwoPi * kk;
    float dy = P.y - (HudRibbon.w + HudRibbon.y * alpha / TwoPi);
    float rangeR = Fn.SS(0.0, 0.6, alpha) * Fn.SS(amax, amax - 0.6, alpha);
    float ed = abs(abs(dy) - halfT) / 1.2;
    float rail = exp(-ed * ed);
    float bandBody = Fn.SS(halfT + 0.8, halfT - 0.8, abs(dy)) * 0.10;
    float2 guv = float2(-alpha * 28.0 / TwoPi / 16.0, dy / halfT * 0.72 * 0.5 + 0.5);
    float gly = Texture2DSampleGrad(GlyphTex, GlyphTexSampler, guv, ddx(guv), ddy(guv)).r * (abs(dy) < halfT ? 1.0 : 0.0);
    float gain = 1.0 + 0.6 * sC * sC;
    float r = (rail + bandBody + gly) * gain * rangeR * okR;
    if (side == 0) ribF = r; else ribB = r;
}
col += (ribF + ribB * 0.42 * (1.0 - 0.5 * sil)) * (0.90 + 0.25 * fillV) * float3(0.60, 0.97, 1.0);

// Floating crystal shards.
float shard = 0.0;
[unroll] for (int i = 0; i < 7; ++i)
{
    float4 S = HudShards[i];
    float cy = S.y + 3.0 * sin(Age * 1.1 + i * 1.7);
    float ang = HudShardTilt[i] + 0.05 * sin(Age * 0.8 + i);
    float dxs = P.x - S.x, dys = P.y - cy;
    float ca = cos(ang), sa = sin(ang);
    float lx = dxs * ca + dys * sa, ly = -dxs * sa + dys * ca;
    float q = abs(lx) / S.z + abs(ly) / S.w;
    float insd = 1.0 - Fn.SS(0.96, 1.04, q);
    float eq = (q - 1.0) / 0.07;
    float rx = lx / 1.3;
    float cr = (ly - 0.18 * S.w) / 1.3;
    float shade = insd * (0.30 + 0.36 * (lx > 0.0 ? 1.0 : 0.0) * (1.0 - abs(ly) / S.w) + 0.18 * (ly < 0.0 ? 1.0 : 0.0));
    shard += exp(-eq * eq) * 1.05 + exp(-rx * rx) * insd * 0.6 + exp(-cr * cr) * insd * 0.5 + shade + exp(-max(q - 1.0, 0.0) * 4.0) * 0.16;
}
col += shard * (0.8 + 0.4 * fillV) * float3(0.50, 0.95, 1.0);

// Rising sparks.
[unroll] for (int layer = 0; layer < 2; ++layer)
{
    float cell = layer == 0 ? 22.0 : 37.0;
    float speed = layer == 0 ? 26.0 : 17.0;
    float2 g = float2(P.x / cell, (P.y + Age * speed) / cell);
    float2 id = floor(g);
    float hsh = Fn.Hash(id.x * 127.1 + id.y * 311.7 + layer * 74.7);
    float2 hp = float2(Fn.Hash(id.x * 269.5 + id.y * 183.3), Fn.Hash(id.x * 419.2 + id.y * 371.9));
    float2 dd = (g - id - (0.2 + 0.6 * hp)) * cell;
    float densS = (0.012 + 0.035 * fillV + 0.08 * Burst) * env * charged;
    col += exp(-dot(dd, dd) / 3.0) * (hsh > 1.0 - densS ? 1.0 : 0.0) * (0.6 + 0.4 * sin(Age * 9.0 + hsh * 40.0)) * float3(0.6, 1.0, 1.0);
}
// Coverage (2026-10-06): purely additive light let bright scenes show straight through the vessel.
// The glass column now occludes the background (denser as it charges), the dragon head occludes by
// its own texture brightness, and a faint backing sits in the glow. Bright light keeps its exact
// colour: alpha never drops below the pixel's brightness, so colour / alpha stays within [0, 1].
col = saturate(col);
float bodyA = BodyOpacity * (sil * (0.70 + 0.20 * mixV) + (1.0 - sil) * saturate(baseLum * 2.2));
bodyA = max(bodyA, glow * (1.0 - sil) * 0.08 * BodyOpacity);
float coverage = saturate(max(bodyA, max(col.r, max(col.g, col.b))));
return float4(col / max(coverage, 1e-3), coverage * saturate(Reveal));
