// Arcane Frost Sigil V3 (2026-11-27) — 2K 4-Channel Vector Texture + 3-Layer Counter-Rotation.
// Channel Packing (T_AbsoluteZeroArcaneV3, Linear BC7, sRGB=False):
//   R: 8-point interlaced glacial star crown, 16 branching hexagonal snowflake dendrites & 360-deg vernier.
//   G: 32 distinct calligraphic arcane frost runes + ornate dividers.
//   B: Inner clean-aperture frost-lotus lattice, pearl dots & 8-way compass needles.
//   A: Band-isolated tight stroke-hugging glow + medallion jewel glints (co-rotates with R/G/B, ZERO ghosting!).
// Strictly clean central aperture: rn < 0.482 is 100% zero opacity.
// Organic non-repeating Blue / Violet / Cyan random color walk driven by (Time + ColorSeed).

float2 p = (UV - 0.5) * 2.0;
float ang = atan2(p.y, p.x);
float prog = saturate(Progress);
float syn = saturate(Synergy);

// Smooth radial expansion as windup progresses 0 -> 1.
float expand = lerp(0.58, 1.0, smoothstep(0.0, 0.52, prog));
float2 pExp = p / max(0.08, expand);
float rn = length(pExp);

// Strict clean central aperture (rn < 0.482 strictly zero) + clean outer disc clip.
float centerClear = smoothstep(0.480, 0.492, rn);
float outerClip = step(rn, 0.994) * (1.0 - smoothstep(0.976, 0.994, rn));
float validMask = centerClear * outerClip;

// Three independent counter-rotating arcane layers.
float spinRate = 1.0 + prog * 0.65 + syn * 0.42;
float aOut = Time * 0.22 * spinRate;
float aRune = -Time * 0.34 * spinRate;
float aIn = Time * 0.15 * spinRate;

float cO = cos(aOut),  sO = sin(aOut);
float cR = cos(aRune), sR = sin(aRune);
float cI = cos(aIn),   sI = sin(aIn);

float2 uvOut  = 0.5 + 0.5 * float2(pExp.x * cO - pExp.y * sO, pExp.x * sO + pExp.y * cO);
float2 uvRune = 0.5 + 0.5 * float2(pExp.x * cR - pExp.y * sR, pExp.x * sR + pExp.y * cR);
float2 uvIn   = 0.5 + 0.5 * float2(pExp.x * cI - pExp.y * sI, pExp.x * sI + pExp.y * cI);

float4 texOut  = Texture2DSample(ArcaneTex, ArcaneTexSampler, uvOut);
float4 texRune = Texture2DSample(ArcaneTex, ArcaneTexSampler, uvRune);
float4 texIn   = Texture2DSample(ArcaneTex, ArcaneTexSampler, uvIn);

// Band masks matching generate_arcane_circle_textures_v3.py band_splits=(0.628, 0.864) for 100% locked glow.
float mIn   = 1.0 - smoothstep(0.620, 0.636, rn);
float mOut  = smoothstep(0.856, 0.872, rn);
float mRune = smoothstep(0.620, 0.636, rn) * (1.0 - smoothstep(0.856, 0.872, rn));

// Sequential windup ignition: outer crown & inner rim establish immediately; 32 runes sweep around as Progress rises.
float ignOut = lerp(0.62, 1.0, smoothstep(0.0, 0.30, prog));
float ignIn  = lerp(0.55, 1.0, smoothstep(0.04, 0.38, prog)) * (1.0 + syn * 0.32);
float aNorm  = frac((ang + 3.14159265) / 6.2831853 - Time * 0.10);
float ignRune = lerp(0.32, 1.0, smoothstep(aNorm - 0.22, aNorm + 0.05, prog * 1.25 + 0.18));

float coreOut  = texOut.r  * ignOut;
float coreRune = texRune.g * ignRune;
float coreIn   = texIn.b   * ignIn;
float coreMask = saturate(max(max(coreOut, coreRune), coreIn));
float glowMask = saturate(texOut.a * mOut * ignOut + texRune.a * mRune * ignRune + texIn.a * mIn * ignIn);

// Travelling dual-helix cryo energy current gliding along engraved strokes.
float wave1 = pow(saturate(0.5 + 0.5 * cos(ang * 4.0 - Time * (3.2 + 2.4 * prog))), 4.0);
float wave2 = pow(saturate(0.5 + 0.5 * cos(ang * 8.0 + Time * (2.2 + 1.8 * prog))), 5.0);
float energyFlow = 1.0 + (wave1 * 0.52 + wave2 * 0.34) * (0.35 + 0.65 * prog);

// Organic non-repeating random color walk across Glacier Blue / Arcane Violet / Cryo Cyan.
float3 cBlue   = float3(0.16, 0.56, 1.00);
float3 cViolet = float3(0.66, 0.24, 1.00);
float3 cCyan   = float3(0.08, 0.95, 1.00);

float tWalk = Time * 1.15 + ColorSeed * 1.73;
float seg = floor(tWalk);
float fracT = smoothstep(0.08, 0.92, frac(tWalk));
float h0 = frac(sin(seg * 127.1 + ColorSeed * 311.7) * 43758.5453);
float h1 = frac(sin((seg + 1.0) * 127.1 + ColorSeed * 311.7) * 43758.5453);
float i0 = floor(min(2.999, h0 * 3.0));
float i1 = floor(min(2.999, h1 * 3.0));
if (abs(i1 - i0) < 0.5) i1 = fmod(i0 + 1.0 + floor(frac(h1 * 7.3) * 2.0), 3.0);
float3 colA = (i0 < 0.5) ? cBlue : ((i0 < 1.5) ? cViolet : cCyan);
float3 colB = (i1 < 0.5) ? cBlue : ((i1 < 1.5) ? cViolet : cCyan);
float3 primaryCol = lerp(colA, colB, fracT);

float tWalk2 = tWalk + 0.45 + 0.18 * sin(ang * 2.0 - Time * 1.3);
float seg2 = floor(tWalk2);
float fracT2 = smoothstep(0.08, 0.92, frac(tWalk2));
float h2a = frac(sin(seg2 * 127.1 + ColorSeed * 311.7) * 43758.5453);
float h2b = frac(sin((seg2 + 1.0) * 127.1 + ColorSeed * 311.7) * 43758.5453);
float j0 = floor(min(2.999, h2a * 3.0));
float j1 = floor(min(2.999, h2b * 3.0));
if (abs(j1 - j0) < 0.5) j1 = fmod(j0 + 1.0, 3.0);
float3 accA = (j0 < 0.5) ? cBlue : ((j0 < 1.5) ? cViolet : cCyan);
float3 accB = (j1 < 0.5) ? cBlue : ((j1 < 1.5) ? cViolet : cCyan);
float3 accentCol = lerp(accA, accB, fracT2);

float3 innerTint = lerp(lerp(primaryCol, accentCol, 0.55), float3(0.55, 0.96, 1.0), syn * 0.55);
float wSum = max(0.001, coreOut + coreRune + coreIn);
float3 strokeChroma = (primaryCol * coreOut + accentCol * coreRune + innerTint * coreIn) / wSum;
float3 auraChroma = lerp(primaryCol, accentCol, mRune * 0.72 + mIn * 0.40);

// Incandescent white-hot engraved hairline core inside saturated Blue/Violet/Cyan halo.
float3 hotCore = lerp(strokeChroma, float3(0.95, 0.99, 1.0), pow(coreMask, 1.08) * (0.42 + 0.34 * prog));
float3 finalCol = lerp(auraChroma * 1.10, hotCore * 1.38, saturate(coreMask * 1.35));

float gain = (1.75 + 2.35 * prog * prog + syn * 0.65) * energyFlow;
float combined = saturate(coreMask * 0.94 + glowMask * 0.44) * validMask;
float alpha = saturate((coreMask * 0.90 + glowMask * 0.36) * validMask * Fade);
float3 emissive = finalCol * gain * combined * Fade;

return float4(emissive, alpha);
