// Runebound HUD Motes V2; retain the measured glass/ribbon layout (texture pixels).
static const float2 HudSize = float2(512.0, 2048.0);
static const float HudCenter = 256.00;
static const float HudHalfWidth = 91.02;
static const float HudCapTop = 343.86;
static const float HudTopBoundary = 422.52;
static const float HudHeadX = 252.62;
static const float HudQuadTop = -256.0;
static const float HudLevels[10] = {1991.81, 1501.30, 1367.58, 1234.98, 1098.45, 966.97, 825.38, 684.35, 553.44, 422.52};
static const float HudTicks[8] = {553.44, 684.35, 825.38, 966.97, 1098.45, 1234.98, 1367.58, 1501.30};
static const float4 HudRibbon = float4(160.0, 384.0, 27.0, 430.0);
static const float HudRibbonTurns = 2.720;
// UI-domain translucent material (Slate NoGamma, display space).
// This shader is shared by the passive installer and the dedicated HudMotesV2 author.
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
float inTex = step(HudTopBoundary, P.y); // Exclude every baked dragon-head pixel.
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

// Concentric blue rings now gather a soft nebula and moving round lights.
// The old faceted centre and floating crystal ornaments are intentionally absent.
float2 sealP=P-float2(HudCenter,225.0);
float rad=length(sealP);
float outer=exp(-pow((rad-108.0)/2.0,2.0));
float innerRing=exp(-pow((rad-91.0)/1.5,2.0));
float angle=atan2(sealP.y,sealP.x);
float notches=pow(saturate(cos(angle*12.0+Age*.15)),18.0)*exp(-pow((rad-100.0)/5.0,2.0));
float2 cloudUV=sealP/230.0+float2(Age*.016,-Age*.023);
float cloudNoise=Texture2DSample(NoiseTex,NoiseTexSampler,cloudUV).g;
float haze=exp(-dot(sealP,sealP)/(58.0*58.0))*(.35+.65*cloudNoise);
float gathering=exp(-dot(sealP,sealP)/(23.0*23.0))*(.65+.35*sin(Age*.9));
float neck=exp(-pow((P.x-HudCenter)/3.0,2.0))*step(334.0,P.y)*step(P.y,HudTopBoundary);
float seal=(outer*.65+innerRing*.4+notches*.8+neck*.7)*(0.6+fillV*.5+Burst*.5)+
    (haze*.2+gathering*.13)*(.35+fillV*.7+Burst*.8);
float luminance=max(col.r,max(col.g,col.b));
col=luminance*float3(.12,.47,1.0)+seal*float3(.18,.58,1.0);
// One bounded analytic layer: ten gathering lights above and twenty-two wisps
// rising beside the glass. Position and fade are continuous at each life boundary.
[unroll] for(int mote=0;mote<32;++mote)
{
    float seed=Fn.Hash(mote*17.713+2.0);
    float phase=mote*2.399963;
    float2 pos,velocity;
    float visibility=1.0;
    if(mote<10)
    {
        float orbit=phase+Age*(.16+seed*.11);
        float radius=(24.0+seed*47.0)*(1.0+.09*sin(Age*.7+phase)+Burst*.16);
        pos=float2(HudCenter+cos(orbit)*radius,225.0+sin(orbit)*radius*.68+5.0*sin(Age*.8+phase));
        velocity=float2(-sin(orbit),cos(orbit)*.68);
    }
    else
    {
        float speed=.039+seed*.027;
        float life=frac(Age*speed+Fn.Hash(mote*31.2));
        float side=(mote%2)==0?-1.0:1.0;
        float swing=Age*(.38+seed*.18)+phase;
        float distance=123.0+Fn.Hash(mote*23.7)*91.0;
        pos=float2(HudCenter+side*distance+10.0*sin(swing),1915.0-life*1435.0);
        velocity=float2(5.0*cos(swing),-1435.0*speed);
        float envelope=sin(life*3.14159265);
        visibility=envelope*envelope;
    }
    float2 delta=P-pos;
    float radius=1.5+seed*1.9;
    float2 along=normalize(velocity);
    float longitudinal=dot(delta,along),lateral=dot(delta,float2(-along.y,along.x));
    float core=exp(-dot(delta,delta)/(radius*radius));
    float halo=exp(-dot(delta,delta)/(radius*radius*13.0))*.19;
    float tailLength=5.0+seed*8.0;
    float tail=exp(-lateral*lateral/(radius*radius*.9)-pow((longitudinal+tailLength*.45)/tailLength,2.0))*.15;
    float breath=.78+.22*sin(Age*(.7+seed*.35)+phase);
    float intensity=visibility*breath*(.21+.43*fillV+.12*Pulse+.3*Burst);
    col+=(core+halo+tail)*intensity*float3(.23,.6,1.0);
}

col = saturate(col);
float bodyA = BodyOpacity * (sil * (0.70 + 0.20 * mixV) + (1.0 - sil) * saturate(baseLum * 2.2));
bodyA = max(bodyA, glow * (1.0 - sil) * 0.08 * BodyOpacity);
float coverage = saturate(max(bodyA, max(col.r, max(col.g, col.b))));
return float4(col / max(coverage, 1e-3), coverage * saturate(Reveal));
