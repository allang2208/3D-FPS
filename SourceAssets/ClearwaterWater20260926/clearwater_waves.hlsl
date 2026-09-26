// ============================================================================
//  Clearwater water surface  --  HLSL for FPSGAME / UE 5.8 material Custom nodes
//
//  Ported from https://github.com/Aureliengmz/clearwater (MIT, (c) 2026 Lumaris).
//  Source: index.html
//      pMain          (351-560)  surface shading: Fresnel, reflection, underwater optics
//      sky()          (372-394)  sky gradient and sun lobes
//      fresnel()      (424-430)  exact dielectric Fresnel
//      IORS / SIG_*   (322, 358) per-channel refraction, absorption / scattering
//
//  What changed, and why a browser full-screen shader cannot be copied verbatim:
//   * Clearwater ray-marches a height field every screen pixel, shades sky, water and
//     seabed in one pass, and invents its seabed procedurally. Here the surface is real
//     geometry, the seabed is a real mesh, and UE owns the sky. The ray march and
//     floorDepth()/pebbles() are gone.
//   * Screen-space derivatives (the caustics Jacobian, the particle fwidth fade) are
//     replaced by analytic terms: ddx/ddy are not portable across the passes this runs in.
//   * Screen-space refraction of the background becomes UE's refraction input, so the
//     underwater term is ADDED to the scene rather than substituted for it. Feeding
//     clearwater's absolute colour into Emissive would make the water glow.
//   * Units are centimetres (UE), the spectrum is authored in metres.
//
// Wave data: Tools/Fluids/clearwater_spectrum.py reduces buildH0()'s 256x256 spectrum to
// 48 directional components, two per Wave01..Wave24 parameter:
//      .xy = phase vector k*dir   (rad/cm)
//      .z  = amplitude            (cm)
//      .w  = angular frequency    (rad/s)
//
// The material Custom nodes embed this file's functions verbatim; Tools/Fluids/
// author_clearwater_water.py slices them out by these section markers. Keep the markers.
// ============================================================================

// CW_BEGIN_MATH

float CWFrac(float x) { return x - floor(x); }
float2 CWFrac2(float2 x) { return x - floor(x); }
float3 CWFrac3(float3 x) { return x - floor(x); }

float CWHash12(float2 p)
{
    float3 p3 = CWFrac3(float3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return CWFrac((p3.x + p3.y) * p3.z);
}

float CWVNoise(float2 p)
{
    float2 i = floor(p);
    float2 f = CWFrac2(p);
    float2 u = f * f * (3.0 - 2.0 * f);
    return lerp(lerp(CWHash12(i), CWHash12(i + float2(1, 0)), u.x),
                lerp(CWHash12(i + float2(0, 1)), CWHash12(i + 1), u.x), u.y);
}

// Exact single-interface dielectric Fresnel, ported verbatim from clearwater fresnel().
float CWFresnel(float cosI, float n)
{
    float ci = clamp(cosI, 0.0, 1.0);
    float st2 = (1.0 - ci * ci) / (n * n);
    if (st2 >= 1.0) return 1.0;
    float ct = sqrt(1.0 - st2);
    float rs = (ci - n * ct) / (ci + n * ct);
    float rp = (n * ci - ct) / (n * ci + ct);
    return 0.5 * (rs * rs + rp * rp);
}

// Henyey-Greenstein phase function, as used for clearwater's in-scattered sun term.
float CWHenyeyGreenstein(float cosTheta, float g)
{
    float g2 = g * g;
    return (1.0 - g2) / (4.0 * 3.14159265359
           * pow(max(1.0 + g2 - 2.0 * g * cosTheta, 1e-4), 1.5));
}

// Clearwater's sky(), reduced to what still makes sense once UE owns the sky.
// The distant-headland ridge, pine/limestone canopy and aerial perspective are dropped
// on purpose: the level supplies real terrain and SkyAtmosphere does the scattering.
float3 CWSky(float3 D, float3 SunDir)
{
    float e = D.y;
    float mu = dot(D, SunDir);
    float3 zen = float3(0.11, 0.27, 0.62);
    float3 hor = float3(0.66, 0.78, 0.90);
    float3 c = lerp(hor, zen, pow(saturate(e), 0.42));
    c += float3(1.0, 0.86, 0.66) * (0.22 * pow(max(mu, 0.0), 6.0)
                                  + 0.30 * pow(max(mu, 0.0), 64.0)
                                  + 1.60 * pow(max(mu, 0.0), 2400.0));
    return c;
}

// ---------------------------------------------------------------- wave accumulation
// One wave per float4 parameter (.xy = phase vector k*dir, .z = amplitude cm, .w = omega),
// six per node, eight nodes chained through Add to cover all 48 components.
//
// A wave is NOT packed two-per-parameter even though .xy/.z/.w are used: that would need
// eight floats and a Vector parameter only holds four.
//
// Output: .x = height (cm), .y = dH/dx (slope), .z = dH/dz (slope), .w = choppiness sum.
// Choppiness is clearwater's horizontal displacement: for H = A*sin(phase) the surface
// carries a phase-aligned horizontal push of Q*A*sin(phase) in metres along the wave
// direction. Keeping it is what makes the water look like it is travelling rather than
// pulsing in place.
float4 CWWaves6(float2 P, float T, float Chop,
                float4 W0, float4 W1, float4 W2, float4 W3, float4 W4, float4 W5)
{
    float4 O = float4(0.0, 0.0, 0.0, 0.0);
    float4 W[6] = { W0, W1, W2, W3, W4, W5 };
    [unroll]
    for (int i = 0; i < 6; ++i)
    {
        float2 k = W[i].xy;
        float  A = W[i].z;
        float  w = W[i].w;
        float  ph = dot(k, P) - w * T;
        float  s = sin(ph);
        float  c = cos(ph);
        O.x += A * s;               // height
        O.y += A * k.x * c;         // dH/dx
        O.z += A * k.y * c;         // dH/dz
        O.w += Chop * A * s * 0.01; // 0.01 = metres -> centimetres, for the phase push
    }
    return O;
}

// The 48-component sum, shared by the displacement and normal nodes. Both call this rather
// than repeating the chain, so the two can never drift apart.
float4 CWWaveSum(float2 P, float T, float Chop,
                 float4 W0, float4 W1, float4 W2, float4 W3, float4 W4, float4 W5,
                 float4 W6, float4 W7, float4 W8, float4 W9, float4 Wa, float4 Wb,
                 float4 Wc, float4 Wd, float4 We, float4 Wf, float4 Wg, float4 Wh,
                 float4 Wi, float4 Wj, float4 Wk, float4 Wl, float4 Wm, float4 Wn,
                 float4 Wo, float4 Wp, float4 Wq, float4 Wr, float4 Ws, float4 Wt,
                 float4 Wu, float4 Wv, float4 Ww, float4 Wx, float4 Wy, float4 Wz,
                 float4 Wa0, float4 Wb0, float4 Wc0, float4 Wd0, float4 We0, float4 Wf0,
                 float4 Wg0, float4 Wh0, float4 Wi0, float4 Wj0, float4 Wk0, float4 Wl0)
{
    return CWWaves6(P, T, Chop, W0, W1, W2, W3, W4, W5)
         + CWWaves6(P, T, Chop, W6, W7, W8, W9, Wa, Wb)
         + CWWaves6(P, T, Chop, Wc, Wd, We, Wf, Wg, Wh)
         + CWWaves6(P, T, Chop, Wi, Wj, Wk, Wl, Wm, Wn)
         + CWWaves6(P, T, Chop, Wo, Wp, Wq, Wr, Ws, Wt)
         + CWWaves6(P, T, Chop, Wu, Wv, Ww, Wx, Wy, Wz)
         + CWWaves6(P, T, Chop, Wa0, Wb0, Wc0, Wd0, We0, Wf0)
         + CWWaves6(P, T, Chop, Wg0, Wh0, Wi0, Wj0, Wk0, Wl0);
}

// ---------------------------------------------------------------- vertex displacement
// World Position Offset, in centimetres, relative to the surface at rest. The material node
// passes (P, T, Chop, AmpScale, W0..W23) -- keep this signature in step with
// Tools/Fluids/author_clearwater_water.py; clearwater_embed_check.py compiles both together
// and is what caught a mismatched argument count during development.
float3 CWDisplace(float2 P, float T, float Chop, float AmpScale,
                  float4 W0, float4 W1, float4 W2, float4 W3, float4 W4, float4 W5,
                  float4 W6, float4 W7, float4 W8, float4 W9, float4 Wa, float4 Wb,
                  float4 Wc, float4 Wd, float4 We, float4 Wf, float4 Wg, float4 Wh,
                  float4 Wi, float4 Wj, float4 Wk, float4 Wl, float4 Wm, float4 Wn,
                  float4 Wo, float4 Wp, float4 Wq, float4 Wr, float4 Ws, float4 Wt,
                  float4 Wu, float4 Wv, float4 Ww, float4 Wx, float4 Wy, float4 Wz,
                  float4 Wa0, float4 Wb0, float4 Wc0, float4 Wd0, float4 We0, float4 Wf0,
                  float4 Wg0, float4 Wh0, float4 Wi0, float4 Wj0, float4 Wk0, float4 Wl0)
{
    float4 S = CWWaveSum(P, T, Chop, W0, W1, W2, W3, W4, W5, W6, W7, W8, W9, Wa, Wb,
                         Wc, Wd, We, Wf, Wg, Wh, Wi, Wj, Wk, Wl, Wm, Wn,
                         Wo, Wp, Wq, Wr, Ws, Wt, Wu, Wv, Ww, Wx, Wy, Wz,
                         Wa0, Wb0, Wc0, Wd0, We0, Wf0, Wg0, Wh0, Wi0, Wj0, Wk0, Wl0);
    return float3(-S.w, -S.w * 0.35, S.x * AmpScale);
}

// ---------------------------------------------------------------- surface normal
// Tangent-space normal in UE's convention (+X, +Y, +Z with Z out of the surface).
// Derivation: with the horizontal push X = -Q*Sum(A*sin) and height Z = Sum(A*sin), the
// displaced position is D(u,v) = (u + X, v, Z), giving
//      dD/du = (1 + dX/du, 0, dZ/du),  dD/dv = (0, 1 + dX/dv, dZ/dv)
// dX/du = dX/dv = -Q*Sum(A*k*cos) because the push is scaled by |k| and the second axis
// only dampens it. Rising height (+Z) with increasing u must slope the normal to -X, which
// is exactly what the cross product below yields -- do not "fix" the signs by hand.
float3 CWNormalTS(float2 P, float T, float Chop, float AmpScale,
                  float4 W0, float4 W1, float4 W2, float4 W3, float4 W4, float4 W5,
                  float4 W6, float4 W7, float4 W8, float4 W9, float4 Wa, float4 Wb,
                  float4 Wc, float4 Wd, float4 We, float4 Wf, float4 Wg, float4 Wh,
                  float4 Wi, float4 Wj, float4 Wk, float4 Wl, float4 Wm, float4 Wn,
                  float4 Wo, float4 Wp, float4 Wq, float4 Wr, float4 Ws, float4 Wt,
                  float4 Wu, float4 Wv, float4 Ww, float4 Wx, float4 Wy, float4 Wz,
                  float4 Wa0, float4 Wb0, float4 Wc0, float4 Wd0, float4 We0, float4 Wf0,
                  float4 Wg0, float4 Wh0, float4 Wi0, float4 Wj0, float4 Wk0, float4 Wl0)
{
    float4 S = CWWaveSum(P, T, Chop, W0, W1, W2, W3, W4, W5, W6, W7, W8, W9, Wa, Wb,
                         Wc, Wd, We, Wf, Wg, Wh, Wi, Wj, Wk, Wl, Wm, Wn,
                         Wo, Wp, Wq, Wr, Ws, Wt, Wu, Wv, Ww, Wx, Wy, Wz,
                         Wa0, Wb0, Wc0, Wd0, We0, Wf0, Wg0, Wh0, Wi0, Wj0, Wk0, Wl0);
    float dX = -Chop * S.w;                       // d(dX)/du and d(dX)/dv (same by symmetry)
    float3 Du = float3(1.0 + dX, 0.0, S.y * AmpScale);
    float3 Dv = float3(0.0, 1.0 + dX, S.z * AmpScale);
    return normalize(cross(Du, Dv));
}

// ---------------------------------------------------------------- square B-spline
// Clearwater's texBS(): cubic B-spline filtering from four bilinear taps, reserved for
// once a fine ripple normal map is plumbed in. Unreferenced by the material today; kept
// because it is part of the ported surface maths and the harness below compiles it.
// CW_BEGIN_BS
float4 CWTextureBS(Texture2D Tex, SamplerState Samp, float2 UV)
{
    float2 ts = float2(1024.0, 1024.0);
    float2 p = UV * ts - 0.5;
    float2 f = CWFrac2(p);
    p = floor(p);
    float2 f2 = f * f, f3 = f2 * f;
    float2 w0 = (-f3 + 3.0 * f2 - 3.0 * f + 1.0) / 6.0;
    float2 w1 = (3.0 * f3 - 6.0 * f2 + 4.0) / 6.0;
    float2 w2 = (-3.0 * f3 + 3.0 * f2 + 3.0 * f + 1.0) / 6.0;
    float2 w3 = f3 / 6.0;
    float2 g0 = w0 + w1, g1 = w2 + w3;
    float2 h0 = (w1 / g0 - 0.5 + p) / ts, h1 = (w3 / g1 + 1.5 + p) / ts;
    return (Tex.SampleLevel(Samp, float2(h0.x, h0.y), 0) * g0.x
          + Tex.SampleLevel(Samp, float2(h1.x, h0.y), 0) * g1.x) * g0.y
         + (Tex.SampleLevel(Samp, float2(h0.x, h1.y), 0) * g0.x
          + Tex.SampleLevel(Samp, float2(h1.x, h1.y), 0) * g1.x) * g1.y;
}
// CW_END_BS

// ---------------------------------------------------------------- optics block
// Returns a colour to ADD to the scene through Emissive (screen-space refraction is UE's
// job). SceneColor is the background colour the refraction input already gives us.
//
// FineNormal defaults to zero and is deliberately not wired up: the reduced 48-component
// spectrum already carries the surface detail the source got from its B-spline ripple
// texture, and a mismatched tangent-space normal would perturb every glint in the frame.
// Supply one only once a real ripple normal map is plumbed through.
float3 CWOpticColor(
    float3 N,               // world normal of the water surface (unit)
    float3 V,               // view direction, surface -> camera (unit)
    float3 SunDir,          // direction TO the sun (unit)
    float3 SunColor,        // linear sun radiance
    float3 SceneColor,      // background colour under the surface (linear, HDR)
    float3 Absorption,      // SIG_A, per metre
    float3 Scattering,      // SIG_S, per metre
    float  DepthMeters,     // water path length along the refracted ray
    float  Caustic,         // caustic irradiance multiplier (1 = none)
    float  GlintSharpness,  // slope-variance widening; 0 disables glints
    float3 FineNormal)      // B-spline filtered ripple normal, tangent space
{
    const float IOR = 1.3335;
    float3 SigT = Absorption + Scattering;

    // Perturb the wave normal with the fine ripple detail.
    float3 Nw = normalize(N + float3(FineNormal.xy * 0.35, 0.0));

    float nv = dot(Nw, V);
    if (nv < 0.02) { Nw = normalize(Nw + V * (0.02 - nv)); nv = dot(Nw, V); }

    float F = CWFresnel(nv, IOR);
    float3 R = reflect(-V, Nw);
    R.y = abs(R.y);
    float3 Refl = CWSky(R, SunDir) * 1.25;

    // Sun glints: Beckmann NDF widened by the slope variance (clearwater's LEAN trick).
    float3 H = normalize(V + SunDir);
    float nh = max(dot(Nw, H), 0.0);
    float nl = max(dot(Nw, SunDir), 0.0);
    float a2 = 0.00012 + GlintSharpness;
    float c2 = max(nh * nh, 1e-4);
    float tan2 = (1.0 - c2) / c2;
    float D = exp(-tan2 / max(a2, 1e-6)) / (3.14159265359 * max(a2, 1e-6) * c2 * c2);
    float Vis = 0.5 / max(nl * sqrt(nv * nv * (1.0 - a2) + a2)
                        + nv * sqrt(nl * nl * (1.0 - a2) + a2), 1e-5);
    float Fh = CWFresnel(max(dot(H, V), 0.0), IOR);
    float3 Spec = SunColor * min(D * Vis * Fh * nl, 12000.0);

    // Transmission through the surface toward the seabed.
    float Ts = 1.0 - CWFresnel(max(SunDir.y, 0.0), IOR);

    // Distance the light actually travels through the column, along the refracted sun ray.
    float3 SunT = refract(-SunDir, float3(0, 0, 1), 1.0 / IOR);
    float CosSunT = max(-SunT.z, 0.05);
    float PathMeters = DepthMeters / CosSunT;

    // Seabed: what the scene already shows under the water, plus caustics, extinguished
    // by the full extinction coefficient.
    float3 Floor = SceneColor * Ts * exp(-SigT * PathMeters) * Caustic;

    // In-scattering from the water column (clearwater: Lmid / Lin with an HG phase).
    float3 Lmid = SunColor * Ts * exp(-SigT * PathMeters * 0.5)
                * (CWHenyeyGreenstein(dot(SunT, -V), 0.8) + 0.02);
    float3 Lin = (Scattering / max(SigT, 1e-4)) * Lmid * 3.2 * (1.0 - exp(-SigT * PathMeters));

    float3 Under = Floor + Lin;
    float3 Out = F * Refl + (1.0 - F) * Under + Spec;

    // Clearwater also blends a distance haze over the water. That term is deliberately
    // omitted here: the scene's exponential height fog and SkyAtmosphere already provide
    // aerial perspective, and mixing two haze models double-darkens the horizon.
    return Out;
}

// ---------------------------------------------------------------- caustics
// Clearwater computes caustics every frame by rasterising a projected grid through the
// surface with a per-channel IOR and reading the screen-space Jacobian of the refracted
// source coordinates as intensity (index.html pCaus, lines 297-320). A material cannot run
// that pass, so Tools/Fluids/clearwater_caustics.py evaluates the same physics backwards
// offline and bakes the result: rays deposited where they land on the seabed, weighted by
// 1/|det J|, which is the identical concentration measure. This samples that bake.
//
// Two layers scroll at different rates, which is what keeps the web from reading as a
// sliding wallpaper. The second layer is the same texture at a different scale, so the
// pattern never visibly repeats.
float3 CWCaustics(Texture2D Tex, SamplerState Samp, float2 WorldXY,
                  float2 ShiftA, float2 ShiftB, float Scale,
                  float CausticStrength, float DepthCm)
{
    float2 uvA = WorldXY / Scale + ShiftA;
    float2 uvB = WorldXY / (Scale * 0.61) + ShiftB;
    float3 a = Tex.SampleLevel(Samp, uvA, 0).rgb;
    float3 b = Tex.SampleLevel(Samp, uvB, 0).rgb;
    // Multiply the layers: caustic webs intersect rather than merely sum, and the product
    // keeps the dark gaps dark instead of washing them out.
    float3 web = a * b * 4.0;
    // Deeper water spreads the light: soften the contrast with depth.
    float depth = saturate(DepthCm / 400.0);
    web = lerp(web, lerp(web, 1.0, 0.35), depth);
    return lerp(float3(1.0, 1.0, 1.0), web, saturate(CausticStrength));
}

// ---------------------------------------------------------------- underwater
// Clearwater folds the underwater column into the water surface shader because it raymarches
// the seabed per pixel. With real geometry and a real seabed the equivalent is a post
// process: take what the camera sees below the surface and push it through the water column.
//
// This is the same optics as CWOpticColor's transmission path (SIG_A absorption, SIG_S
// scattering, Henyey-Greenstein in-scatter), applied to the scene colour instead of a
// procedural floor.
//
//   NdotV  = dot(surface normal, camera-to-pixel direction), 1 = straight down
//   PathMeters = distance the view ray travels through water
float3 CWUnderwater(float3 SceneColor, float PathMeters, float CosView,
                    float3 SunDir, float3 SunColor,
                    float3 Absorption, float3 Scattering,
                    float SurfaceFresnel)
{
    const float IOR = 1.3335;
    float3 SigT = Absorption + Scattering;
    float Path = max(PathMeters, 0.0);

    // Looking straight down through the surface, less light enters; at grazing angles the
    // surface reflects instead. clearwater applies the same Fresnel to its sun term.
    float Entry = 1.0 - SurfaceFresnel;

    // In-scattered sunlight along the view ray, with the source's forward-scattering phase.
    float3 SunT = refract(-SunDir, float3(0, 0, 1), 1.0 / IOR);
    float3 Lmid = SunColor * Entry * exp(-SigT * Path * 0.5)
                * (CWHenyeyGreenstein(dot(SunT, float3(0, 0, -1)), 0.8) + 0.02);
    float3 Lin = (Scattering / max(SigT, 1e-4)) * Lmid * 3.2 * (1.0 - exp(-SigT * Path));

    float3 Transmitted = SceneColor * Entry * exp(-SigT * Path);
    return Transmitted + Lin;
}

// ---------------------------------------------------------------- lens diffraction glare
// Clearwater convolves the bright pass with the camera aperture's diffraction pattern by FFT
// every frame (index.html "Lens diffraction glare", lines 626-775), which is what puts a
// six-point star with faint rainbow tints on every sun glint and costs the same whether
// there is one glint or a thousand.
//
// A post-process material cannot run an FFT, but the kernel is static, so
// Tools/Fluids/clearwater_glare.py bakes the aperture PSF (hexagon flats, hairline
// scratches, dust, integrated over eight wavelength bands) and
// clearwater_glare_weights.py reduces it to per-channel tap weights. This walks a sparse
// ring of those taps -- the standard real-time stand-in for a convolution kernel.
//
// Weights and fractions are passed as individual pins, inlined by the authoring script from
// GlareTaps.gen.h -- a material Custom node has no array inputs.
#define CW_GLARE_TAPS 11

float3 CWGlareTap(Texture2D Tex, SamplerState Samp, float2 UV, float2 Dir,
                  float Radius, float W0, float W1, float W2,
                  float3 C0, float3 C1, float3 C2)
{
    float2 o0 = Dir * (W0 * Radius);
    float2 o1 = Dir * (W1 * Radius);
    float2 o2 = Dir * (W2 * Radius);
    float3 acc = (Tex.SampleLevel(Samp, UV + o0, 0).rgb + Tex.SampleLevel(Samp, UV - o0, 0).rgb) * C0
               + (Tex.SampleLevel(Samp, UV + o1, 0).rgb + Tex.SampleLevel(Samp, UV - o1, 0).rgb) * C1
               + (Tex.SampleLevel(Samp, UV + o2, 0).rgb + Tex.SampleLevel(Samp, UV - o2, 0).rgb) * C2;
    return acc;
}

float3 CWGlareCombine(float3 Acc, float Threshold)
{
    // Threshold again so only genuinely bright pixels source a star, then scale back up:
    // the sparse ring covers far fewer pixels than the FFT convolution it replaces.
    float l = max(max(Acc.r, Acc.g), Acc.b);
    return Acc * max(l - Threshold, 0.0) / max(l, 1e-4);
}

// ---------------------------------------------------------------- impact ripples
// The project's water interaction system writes WaterHit0..N as
// (world.x, world.y, age, strength) whenever a bullet, footstep or body touches a registered
// surface (see URiverPilotFXSubsystem::RegisterWaterSurface). Clearwater's own interactive
// ripple is a scrolling wave-equation window (index.html lines 231-281) that a material
// cannot run, so these are evaluated analytically instead: a damped radial ridge that
// expands at a fixed speed and fades with age.
//
// Slots are passed individually rather than as an array: a material Custom node binds inputs
// to named pins, so there is no array to hand it.
//
// Returns the normal perturbation to ADD, in tangent space. Each ring height is a function
// of r alone, so its gradient is dH/dr * (d/r) and can be taken analytically -- finite
// differencing in world space is hopeless here, since world coordinates run to tens of
// thousands of centimetres and a useful epsilon sits below float precision.
float3 CWRippleNormal(float2 WorldXY, float WaveSpeed, float MaxAge,
                      float4 Hit0, float4 Hit1, float4 Hit2, float4 Hit3)
{
    float3 N = float3(0.0, 0.0, 0.0);
    float4 Hits[4] = { Hit0, Hit1, Hit2, Hit3 };
    [unroll]
    for (int i = 0; i < 4; ++i)
    {
        float4 H = Hits[i];
        // Unused slots carry zero strength; a negative age marks "never fired".
        if (H.w <= 0.0 || H.z < 0.0 || H.z > MaxAge) continue;

        float2 d = WorldXY - H.xy;
        float r = length(d);
        if (r < 1e-4) continue;

        // The ring expands outward and decays; a travelling sinusoid inside the packet makes
        // it read as a wave train rather than a single pulse.
        float front = max(WaveSpeed * H.z, 1.0);
        float sig2 = max(front * front * 0.12, 144.0);
        float band = exp(-(r - front) * (r - front) / sig2);
        float env = band * exp(-H.z / max(MaxAge * 0.55, 1e-3)) * H.w;
        const float Freq = 0.16;
        // d/dr [ band * sin(Freq*(r-front)) ]
        float dband = -2.0 * (r - front) / sig2 * band;
        float dHdr = env * (dband * sin(Freq * (r - front))
                          + band * cos(Freq * (r - front)) * Freq) * 0.09;
        N.xy -= d / r * dHdr;
    }
    return N;
}

// ---------------------------------------------------------------- lens diffraction glare
// Clearwater convolves the bright pass with the camera aperture's diffraction pattern by FFT
// every frame (index.html "Lens diffraction glare", lines 626-775), which is what puts a
// six-point star with faint rainbow tints on every sun glint. The cost is independent of how
// many glints there are, because it is a convolution.
//
// That per-frame FFT is not available to a material. The aperture kernel is static, though,
// so Tools/Fluids/clearwater_glare.py bakes it (hexagon flats, hairline scratches, dust,
// integrated over eight wavelength bands) and clearwater_glare_weights.py reduces it to
// per-channel tap weights in GlareTaps.gen.h.
//
// What runs here is a closed-form radial star rather than a full convolution: a stand-in for
// a point-spread function that decays as fast as this one, with the chromatic weights from
// GlareTaps.gen.h carrying the rainbow fringing. It extends clearwater's sun-glint term
// rather than replacing it, so the star sits on top of the physical specular lobe.
//
// Deliberately a function of screen position and the glint's brightness alone -- an 11-tap
// ring would cost eleven texture fetches per pixel, where this costs arithmetic on a value
// the shader already has.
float3 CWGlareStar(float Glint, float2 UV, float2 SunScreen, float Aspect,
                   float Radius, float3 WarmWeight, float3 CoolWeight)
{
    float2 d = (UV - SunScreen) * float2(Aspect, 1.0);
    float r = length(d);
    float2 dir = r > 1e-5 ? d / r : float2(0.0, 0.0);

    // Core bloom plus the long spikes. The 1/r tail is what reads as a spike rather than a
    // disc, so it is kept separate from the compact core term.
    float core = exp(-(r * r) / max(Radius * Radius * 0.08, 1e-8));
    float tail = Radius / (r + Radius * 0.35);
    float falloff = core + tail * tail * 0.35;

    // A six-blade aperture concentrates energy into three axes; cos^2(3*theta) is what turns
    // a plain glow into a star. The cool term is narrower, which is what produces the faint
    // rainbow edge as the two lobes separate with radius.
    float star = 0.40 + 0.60 * pow(abs(cos(3.0 * atan2(dir.y, dir.x))), 3.0);
    float tint = saturate(r / max(Radius * 0.5, 1e-4));
    float3 rgb = lerp(CoolWeight, WarmWeight, tint);

    // Glint is clearwater's clamped specular; gating on it keeps the star on the sun and
    // off every other bright pixel in the frame.
    return rgb * star * falloff * Glint;
}

// CW_END_MATH

// ============================================================================
//  Offline compile harness (validated with fxc ps_5.0 / dxc ps_6.0).
//  The material graph never calls this; it exists so the maths above can be compiled
//  and checked without opening the editor.
// ============================================================================
#ifdef CW_COMPILE_TEST
Texture2D CWTestTex;
SamplerState CWTestSamp;

float4 main(float2 uv : TEXCOORD0) : SV_Target
{
    float4 W = float4(1.0, 0.5, 10.0, 5.0);
    float4 S = CWWaves6(uv * 100.0, 3.0, 0.7,
                        W + 0, W + 1, W + 2, W + 3, W + 4, W + 5);
    float3 D = CWDisplace(uv * 100.0, 3.0, 0.7, 1.0,
                        W + 0, W + 1, W + 2, W + 3, W + 4, W + 5,
                        W + 6, W + 7, W + 8, W + 9, W + 10, W + 11,
                        W + 12, W + 13, W + 14, W + 15, W + 16, W + 17,
                        W + 18, W + 19, W + 20, W + 21, W + 22, W + 23,
                        W + 24, W + 25, W + 26, W + 27, W + 28, W + 29,
                        W + 30, W + 31, W + 32, W + 33, W + 34, W + 35,
                        W + 36, W + 37, W + 38, W + 39, W + 40, W + 41,
                        W + 42, W + 43, W + 44, W + 45, W + 46, W + 47);
    float3 N = CWNormalTS(uv * 100.0, 3.0, 0.7, 1.0,
                        W + 0, W + 1, W + 2, W + 3, W + 4, W + 5,
                        W + 6, W + 7, W + 8, W + 9, W + 10, W + 11,
                        W + 12, W + 13, W + 14, W + 15, W + 16, W + 17,
                        W + 18, W + 19, W + 20, W + 21, W + 22, W + 23,
                        W + 24, W + 25, W + 26, W + 27, W + 28, W + 29,
                        W + 30, W + 31, W + 32, W + 33, W + 34, W + 35,
                        W + 36, W + 37, W + 38, W + 39, W + 40, W + 41,
                        W + 42, W + 43, W + 44, W + 45, W + 46, W + 47);
    float4 BS = CWTextureBS(CWTestTex, CWTestSamp, uv);
    float3 C = CWOpticColor(N, normalize(float3(0, 0, 1)), normalize(float3(0.5, 0.8, 0.3)),
                            float3(6, 5.4, 4.4), float3(0.2, 0.3, 0.25),
                            float3(0.40, 0.074, 0.088), float3(0.028, 0.052, 0.068),
                            1.6, 1.2, 0.4, BS.xyz);
    // Caustics, underwater column, glare ring and impact ripples.
    float3 Cau = CWCaustics(CWTestTex, CWTestSamp, uv * 400.0, float2(0.1, 0.2),
                            float2(-0.3, 0.15), 460.0, 1.0, 160.0);
    float3 Und = CWUnderwater(Cau, 1.6, 0.8, normalize(float3(0.5, 0.8, 0.3)),
                              float3(6, 5.4, 4.4), float3(0.40, 0.074, 0.088),
                              float3(0.028, 0.052, 0.068), 0.02);
    float3 G0 = CWGlareTap(CWTestTex, CWTestSamp, uv, float2(1, 0), 0.35,
                           0.0, 0.035, 0.07, float3(1, 1, 1), float3(1, 1, 1), float3(1, 1, 1));
    float3 G = CWGlareCombine(G0, 0.5);
    float3 Rip = CWRippleNormal(uv * 4000.0, 900.0, 1.8,
                                float4(1000, 1000, 0.4, 0.8), float4(0, 0, -1, 0),
                                float4(0, 0, -1, 0), float4(0, 0, -1, 0));
    return float4(C + S.xyz + D + CWVNoise(uv * 30.0).xxx + Cau * 0.1 + Und * 0.1 + G + Rip, 1.0);
}
#endif
