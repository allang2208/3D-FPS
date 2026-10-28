// Runebound symmetric glass caps V3; preserve the original fill and floating-mote layout.
static const float2 HudSize = float2(512.0, 2048.0);
static const float HudCenter = 256.00;
static const float HudHalfWidth = 91.02;
static const float HudCapTop = 343.86;
static const float HudTopBoundary = 480.00000000;
static const float HudBottomBoundary = 1641.20932785;
// Reflect the existing lower cap about the midpoint of the glass column.
static const float HudCapMirrorY = 2063.73223594;
static const float HudHeadX = 252.62;
static const float HudQuadTop = -256.0;
static const float HudLevels[10] = {1991.81, 1501.30, 1367.58, 1234.98, 1098.45, 966.97, 825.38, 684.35, 553.44, 422.52};
static const float HudTicks[8] = {553.44, 684.35, 825.38, 966.97, 1098.45, 1234.98, 1367.58, 1501.30};
static const float4 HudRibbon = float4(160.0, 384.0, 27.0, 430.0);
static const float HudRibbonTurns = 2.720;
// UI-domain translucent material (Slate NoGamma, display space).
// Dedicated V3 shader; the previous V2 source and shared Azure Dragon assets remain intact.
// Inputs: UV, Fill, Age, Pulse, Burst, Reveal, BodyOpacity, EmptyTex, FullTex, MaskTex, NoiseTex, GlyphTex.
struct AzureHudFn
{
    float SS(float a, float b, float x) { float t = saturate((x - a) / (b - a)); return t * t * (3.0 - 2.0 * t); }
    float Hash(float x) { return frac(sin(x) * 43758.5453); }
};
AzureHudFn Fn;
const float TwoPi = 6.28318530718;

float2 P = float2(UV.x * HudSize.x, HudQuadTop + UV.y * (HudSize.y - HudQuadTop));
// Remove the old upper pointed cap. The retained straight column starts here.
float2 sourceP=P;
float2 T=sourceP/HudSize;
float2 texDx=ddx(P)/HudSize;
float2 texDy=ddy(P)/HudSize;
float inTex=Fn.SS(HudTopBoundary-1.0,HudTopBoundary+1.0,P.y)*step(P.y,HudSize.y);
float fillV = saturate(Fill);
float menY=lerp(HudBottomBoundary,HudTopBoundary,fillV);
float charged = fillV > 0.001 ? 1.0 : 0.0;
float zone = Fn.SS(HudTopBoundary - 16.0, HudTopBoundary + 16.0, P.y);
float capV = Fn.SS(11.0 / 12.0, 1.0, fillV);
float wave = 1.6 * sin(P.x * 0.09 + Age * 3.1) + 1.0 * sin(P.x * 0.21 - Age * 4.7);
float below = Fn.SS(menY - 1.5, menY + 1.5, P.y + wave) * charged;
float mixV = zone * below + (1.0 - zone) * capV;
float4 msk = Texture2DSampleGrad(MaskTex, MaskTexSampler, T, texDx, texDy) * inTex;
float sil = msk.r, inner = msk.g, glow = msk.b, env = msk.a;
float3 col = Texture2DSampleGrad(EmptyTex, EmptyTexSampler, T, texDx, texDy).rgb * inTex * (1.0 - mixV)
           + Texture2DSampleGrad(FullTex, FullTexSampler, T, texDx, texDy).rgb * inTex * (1.0 + 0.35 * Pulse + 0.4 * Burst) * mixV;
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

// Discrete sparks travel on the exact retained helix (radius/pitch/turns/rotation).
// Invert its two projected halves and evaluate only adjacent particles per pixel.
// Two narrow, staggered lanes share the old ribbon centreline; no solid rails or glyphs.
float sR=(HudCenter-P.x)/HudRibbon.x;
float sC=clamp(sR,-.999,.999);
float phi=Age*.45;
float amax=TwoPi*HudRibbonTurns;
float helixPitch=HudRibbon.y/TwoPi;
float particleStep=amax/156.0;
float particleTravel=Age*.62;
float pixelFootprint=max(length(ddx(P)),length(ddy(P)));
float helixLight=0.0;
float helixParticleCoverage=0.0;
float helixBounds=Fn.SS(HudRibbon.x+24.0,HudRibbon.x+14.0,abs(P.x-HudCenter));
[unroll] for(int side=0;side<2;++side)
{
    float thetaGuess=side==0?asin(sC):3.14159265-asin(sC);
    float a0=thetaGuess-phi;
    float turn=round(((P.y-HudRibbon.w)/helixPitch-a0)/TwoPi);
    float closest=a0+TwoPi*turn;
    float2 curvePoint=float2(HudCenter-HudRibbon.x*sin(closest+phi),HudRibbon.w+helixPitch*closest);
    float2 curveSlope=float2(-HudRibbon.x*cos(closest+phi),helixPitch);
    // Refine near the silhouette where inverse-sine alone loses the band width.
    closest+=clamp(dot(P-curvePoint,curveSlope)/max(dot(curveSlope,curveSlope),1.0),-.28,.28);
    [unroll] for(int lane=0;lane<2;++lane)
    {
        float cell=floor((closest+particleTravel)/particleStep-lane*.5);
        [unroll] for(int neighbor=-1;neighbor<=1;++neighbor)
        {
            float id=cell+neighbor;
            float seed=Fn.Hash(id*73.173+lane*117.79+3.1);
            float variant=Fn.Hash(id*19.419+lane*47.21+8.0);
            float alpha=(id+lane*.5+(seed-.5)*.18)*particleStep-particleTravel;
            float theta=alpha+phi;
            float face=step(0.0,cos(theta));
            float belongs=side==0?face:1.0-face;
            float edgeFade=Fn.SS(0.0,.38,alpha)*Fn.SS(amax,amax-.38,alpha);
            float radius=HudRibbon.x+(lane==0?-4.0:4.0)+2.0*sin(Age*.83+seed*TwoPi);
            float2 pos=float2(HudCenter-radius*sin(theta),HudRibbon.w+helixPitch*alpha);
            pos.y+=2.8*sin(Age*.91+variant*TwoPi);
            float2 velocity=normalize(float2(radius*cos(theta)*(.62-.45),-helixPitch*.62));
            float2 delta=P-pos;
            float longitudinal=dot(delta,velocity);
            float lateral=dot(delta,float2(-velocity.y,velocity.x));
            float size=max(1.8+variant*1.8,pixelFootprint*.65);
            float core=exp(-dot(delta,delta)/(size*size));
            float halo=exp(-dot(delta,delta)/(size*size*7.0))*.14;
            float tailLength=4.5+seed*4.0;
            float tailPosition=(longitudinal+tailLength*.5)/tailLength;
            float tail=exp(-lateral*lateral/(size*size*.8)
                -tailPosition*tailPosition)*.24;
            float depth=lerp(.42*(1.0-.60*sil),1.0,face);
            float breath=.76+.24*sin(Age*(1.1+variant*.6)+seed*TwoPi);
            float visible=belongs*edgeFade*depth*helixBounds;
            float gain=visible*breath*(.74+.28*fillV+.18*Pulse+.30*Burst);
            helixLight+=(core+halo+tail)*gain;
            helixParticleCoverage=max(helixParticleCoverage,saturate((core*.82+tail*.35)*visible));
        }
    }
}
col+=helixLight*float3(.60,.97,1.0);


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
// The glass column now occludes the background (denser as it charges), the upper mirrored glass cap occludes by
// its own texture brightness, and a faint backing sits in the glow. Bright light keeps its exact
// colour: alpha never drops below the pixel's brightness, so colour / alpha stays within [0, 1].

// The cap structure comes entirely from the retained lower glass texture.
// A restrained, vertically soft light cloud follows the same blue magic style.
// No independent circle, neck line, centre gem or floating crystal is added.
float capFocusY=HudTopBoundary-(HudLevels[0]-HudBottomBoundary)*.48;
float2 sealP=P-float2(HudCenter,capFocusY);
float2 cloudUV=sealP/230.0+float2(Age*.016,-Age*.023);
float cloudNoise=Texture2DSample(NoiseTex,NoiseTexSampler,cloudUV).g;
float2 hazeP=sealP/float2(52.0,86.0);
float haze=exp(-dot(hazeP,hazeP))*(.35+.65*cloudNoise);
float gathering=exp(-dot(sealP,sealP)/(23.0*23.0))*(.65+.35*sin(Age*.9));
float capLight=(haze*.12+gathering*.08)*(.22+fillV*.55+Burst*.7);
float luminance=max(col.r,max(col.g,col.b));
col=luminance*float3(.12,.47,1.0)+capLight*float3(.18,.58,1.0);
// One bounded analytic layer: ten gathering lights above and twenty-two wisps
// born on the helix and drifting away. Birth and death remain continuous.
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
        pos=float2(HudCenter+cos(orbit)*radius,capFocusY+sin(orbit)*radius*.68+5.0*sin(Age*.8+phase));
        velocity=float2(-sin(orbit),cos(orbit)*.68);
    }
    else
    {
        // Reuse the existing 22 wisp slots. Each is born ON the rotating helix,
        // then leaves it with outward drift, buoyant rise and a soft fade.
        float lifetime=2.6+seed*1.8;
        float cycle=Age/lifetime+Fn.Hash(mote*31.2);
        float life=frac(cycle);
        float birthTime=Age-life*lifetime;
        float birthSeed=Fn.Hash(mote*13.9+floor(cycle)*7.31);
        float birthAlpha=lerp(.08,.92,birthSeed)*amax;
        float birthTheta=birthAlpha+birthTime*.45;
        float2 anchor=float2(HudCenter-HudRibbon.x*sin(birthTheta),HudRibbon.w+helixPitch*birthAlpha);
        float outward=-sin(birthTheta);
        float driftX=outward*(28.0+seed*30.0);
        float rise=30.0+birthSeed*50.0;
        float sway=Age*(.85+seed*.4)+phase;
        pos=anchor+float2(driftX*life+5.0*sin(sway)*life,-rise*life+4.0*sin(sway*.7)*life);
        velocity=float2(driftX/lifetime+4.0*cos(sway)*life,-rise/lifetime);
        visibility=Fn.SS(0.0,.16,life)*Fn.SS(1.0,.55,life);
        visibility*=cos(birthTheta)>=0.0?1.0:.42*(1.0-.60*sil);
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

// Berserker: the original floating glass, helix and all 32 drifting motes remain.
// Recolor the complete light layer together, avoiding leftover blue highlights.
float bloodLum=max(col.r,max(col.g,col.b));
col=bloodLum*float3(1.0,.022,.038);
// Generated volumetric head: same production-image technique as Azure Dragon HUD V10.
float2 headUV=(P-float2(-1.956244541,70.608733624))/float2(498.423930131,498.423930131);
float headInside=step(0,headUV.x)*step(headUV.x,1)*step(0,headUV.y)*step(headUV.y,1);
float4 head=Texture2DSample(WolfHeadTex,WolfHeadTexSampler,saturate(headUV));
float headOpacity=head.a*headInside*saturate(BodyOpacity*1.15);
float3 headColor=head.rgb*(.92+.08*fillV+.10*Pulse+.12*Burst);
// Only existing red veins breathe; never reduce the whole head to red luminance.
float redVein=saturate(head.r-max(head.g,head.b)*2.0);
headColor+=redVein*float3(.07,.001,.002)*(fillV*.45+Pulse*.3+Burst*.5);
col=col*(1.0-headOpacity)+headColor*headOpacity;
// Fine scar cuts show twelve charging intervals without baked text.
float division=frac((P.y-HudTopBoundary)/(HudBottomBoundary-HudTopBoundary)*12.0);
float scar=(1-Fn.SS(.016,.055,min(division,1-division)))*inner*zone;
col*=1-scar*.38;
// A pointed blood drop below the glass finishes the wolf/fang silhouette.
float2 tip=(P-float2(HudCenter,1880.0))/float2(30.0,105.0);
float drop=(1-Fn.SS(.72,1.0,length(float2(tip.x*(1.3+.5*tip.y),tip.y))))*step(-1.2,tip.y)*step(tip.y,1.0);
col+=drop*float3(.56,.012,.024)*(.22+.5*fillV+.25*Pulse);
col = saturate(col);
float bodyA = BodyOpacity * (sil * (0.70 + 0.20 * mixV) + (1.0 - sil) * saturate(baseLum * 2.2));
bodyA = max(bodyA, glow * (1.0 - sil) * 0.08 * BodyOpacity);
bodyA=max(bodyA,max(headOpacity,helixParticleCoverage));
float coverage = saturate(max(bodyA, max(col.r, max(col.g, col.b))));
return float4(col / max(coverage, 1e-3), coverage * saturate(Reveal));
