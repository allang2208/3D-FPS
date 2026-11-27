// Thunder Lance Arcane Parallax Iris V3 (2026-11-27) — Crisp 2K Vector Secondary Holographic Seal.
// Used as:
//   1. Receding 3D holographic parallax layer (+16 cm behind ChargeCircle) during ThunderLance charging.
//   2. High-voltage expanding arcane shockwave seal on MuzzleIris & Lance Column slices.
// Strictly hollow clean aperture (r < 0.562 zero opacity) + Blue/Violet/Cyan organic color walk.

float2 p = UV * 2.0 - 1.0;
float r = length(p);
float angle = atan2(p.y, p.x);

float centerClear = smoothstep(0.560, 0.574, r);
float outerClip = step(r, 0.994) * (1.0 - smoothstep(0.976, 0.994, r));
float validMask = centerClear * outerClip;

// Counter-rotate relative to primary ChargeCircle outer ring for rich kinetic 3D parallax depth.
float aRot = -Clock * (0.34 + 0.25 * FirePower);
float cR = cos(aRot), sR = sin(aRot);
float2 uvRot = 0.5 + 0.5 * float2(p.x * cR - p.y * sR, p.x * sR + p.y * cR);

float4 tex = Texture2DSample(ArcaneTex, ArcaneTexSampler, uvRot);
// Use outer hexagram/bezel (R) + inner sight filigree (B) + tight outer/inner glow (A), omitting rune band
// so the parallax layer frames cleanly without muddying the foreground calligraphic runes!
float mBand = (1.0 - smoothstep(0.674, 0.690, r)) + smoothstep(0.862, 0.878, r);
float strokes = saturate(max(tex.r * 0.92, tex.b * 0.85));
float glow = tex.a * saturate(mBand);

// Subtle travelling shock ripple along the ring.
float shimmer = 0.82 + 0.18 * cos(angle * 6.0 + Clock * 4.5);

// Organic Blue / Violet / Cyan random color walk synced to ChargeColorSeed.
float3 cBlue   = float3(0.16, 0.52, 1.00);
float3 cViolet = float3(0.68, 0.24, 1.00);
float3 cCyan   = float3(0.08, 0.94, 1.00);
float tWalk = Clock * 1.15 + ColorSeed * 1.73 + 0.28 + 0.16 * sin(angle * 2.0 - Clock * 1.2);
float seg = floor(tWalk);
float fracT = smoothstep(0.08, 0.92, frac(tWalk));
float h0 = frac(sin(seg * 127.1 + ColorSeed * 311.7) * 43758.5453);
float h1 = frac(sin((seg + 1.0) * 127.1 + ColorSeed * 311.7) * 43758.5453);
float i0 = floor(min(2.999, h0 * 3.0));
float i1 = floor(min(2.999, h1 * 3.0));
if (abs(i1 - i0) < 0.5) i1 = fmod(i0 + 1.0 + floor(frac(h1 * 7.3) * 2.0), 3.0);
float3 colA = (i0 < 0.5) ? cBlue : ((i0 < 1.5) ? cViolet : cCyan);
float3 colB = (i1 < 0.5) ? cBlue : ((i1 < 1.5) ? cViolet : cCyan);
float3 tint = lerp(colA, colB, fracT);

float3 finalCol = lerp(tint, float3(0.94, 0.98, 1.0), pow(strokes, 1.15) * (0.32 + 0.28 * FirePower));
float rimAlpha = saturate(Strength * InstanceAlpha * (strokes * 0.72 + glow * 0.30) * 0.62 * shimmer * validMask);
float3 emissive = finalCol * (2.25 + 1.15 * FirePower) * shimmer / max(Exposure, 0.25);

return float4(emissive, rimAlpha);
