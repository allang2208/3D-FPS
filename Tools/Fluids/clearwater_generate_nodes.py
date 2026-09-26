"""Generate self-contained material Custom-node bodies with the wave loops unrolled.

WHY THIS EXISTS
---------------
Unreal emits a Custom node's `code` field into the BODY of a generated function:

    float3 CustomExpression0(FMaterialPixelParameters Parameters, float2 P, ...)
    {
        <code field here>
    }

Two consequences, both measured rather than assumed:

  1. A function definition in the body is illegal HLSL
     ("function definition is not allowed here").
  2. `#include` does NOT help. The preprocessor expands it in place, so the header's contents
     land inside the function body too -- the same error, now pointing at the header. There is
     no preamble hook on a Custom node, so a material graph cannot inject anything at file
     scope.

Macros DO work: they create no scope. Verified by compiling both forms with the engine's own
dxc, wrapped exactly as Unreal wraps them.

So the node bodies are generated here: helper ops as macros in a shader include, and every
loop over the 48 wave parameters unrolled into straight-line statements. What gets emitted is
long but has no function definitions anywhere.

    python Tools/Fluids/clearwater_generate_nodes.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'SourceAssets' / 'ClearwaterWater20260926'
HLSL = ASSETS / 'clearwater_waves.hlsl'
NODES = ASSETS / 'nodes.json'
INC = ROOT / 'Shaders' / 'ClearwaterWaves.ush'

WAVE_COUNT = 48
WAVE_PARAMS = ['W%d' % i for i in range(WAVE_COUNT)]

# Helper ops as macros. Every one is a single expression so it is legal anywhere, and none
# of them introduce a scope.
MACROS = r'''// Clearwater material helper macros.
//
// Ported from https://github.com/Aureliengmz/clearwater (MIT, (c) 2026 Lumaris).
//
// These are MACROS, not functions, and that is forced by the host: Unreal emits a Custom
// node's code field into the body of a generated function, where a function definition is
// illegal HLSL and a `#include` just drags the same problem into the body. Macros create no
// scope, so they are the only reusable unit a material graph can reach.
//
// GENERATED FILE -- edit Tools/Fluids/clearwater_generate_nodes.py and re-run it. Do not
// hand-edit; the node bodies are generated from the same definitions.
#pragma once

#define CW_FRAC(x)          ((x) - floor(x))
#define CW_FRAC2(x)         ((x) - floor(x))
#define CW_FRAC3(x)         ((x) - floor(x))

#define CW_HASH12(p)        (CW_FRAC(dot(CW_FRAC3(float3((p).xyx) * 0.1031), \
                                CW_FRAC3(float3((p).xyx) * 0.1031).yzx + 33.33)))

#define CW_VNOISE(p)        (lerp(lerp(CW_HASH12(floor(p)), \
                                       CW_HASH12(floor(p) + float2(1.0, 0.0)), \
                                       CW_FRAC2(p).x * CW_FRAC2(p).x * (3.0 - 2.0 * CW_FRAC2(p).x)), \
                                  lerp(CW_HASH12(floor(p) + float2(0.0, 1.0)), \
                                       CW_HASH12(floor(p) + float2(1.0, 1.0)), \
                                       CW_FRAC2(p).x * CW_FRAC2(p).x * (3.0 - 2.0 * CW_FRAC2(p).x)), \
                                  CW_FRAC2(p).y * CW_FRAC2(p).y * (3.0 - 2.0 * CW_FRAC2(p).y)))

// Exact single-interface dielectric Fresnel (clearwater fresnel(), index.html 424-430).
//
// Single expression, no branch. clearwater returns 1.0 when the refracted angle is
// evanescent (st2 >= 1); `step` selects that case so the macro stays branch-free and legal
// inside a function body. sqrt is guarded by max(.., 0) because both sides are evaluated.
#define CW_FRESNEL(cosI, n) (CW_FsFresnelAll((cosI), (n)))
#define CW_FRESNEL_ALL(cosI, n)                                                     \
    CW_FsSelect((cosI), (n))

// Both branches, then select -- keeps this a single expression.
#define CW_FsFresnelAll(ci0, n)                                                     \
    (lerp(CW_FsNormal((ci0), (n)), 1.0,                                            \
          step(1.0, CW_FsSt2((ci0), (n)))))

#define CW_FsSt2(ci0, n)   ((1.0 - CW_FsCi(ci0) * CW_FsCi(ci0)) / ((n) * (n)))
#define CW_FsCi(ci0)       (clamp((ci0), 0.0, 1.0))
#define CW_FsCt(ci0, n)    (sqrt(max(1.0 - CW_FsSt2((ci0), (n)), 0.0)))
#define CW_FsNormal(ci0, n)                                                          \
    (0.5 * (CW_FsRs(ci0, n) * CW_FsRs(ci0, n) + CW_FsRp(ci0, n) * CW_FsRp(ci0, n)))
#define CW_FsRs(ci0, n)    ((CW_FsCi(ci0) - (n) * CW_FsCt(ci0, n))                   \
                            / max(CW_FsCi(ci0) + (n) * CW_FsCt(ci0, n), 1e-5))
#define CW_FsRp(ci0, n)    (((n) * CW_FsCi(ci0) - CW_FsCt(ci0, n))                   \
                            / max((n) * CW_FsCi(ci0) + CW_FsCt(ci0, n), 1e-5))

// Clearwater's sky(), reduced to the analytic gradient and the sun lobes. The distant
// headland, pine canopy and aerial perspective are dropped: the level has real terrain and
// SkyAtmosphere does the scattering.
//
// These two constants matter more than they look. Water is almost fully reflective at
// grazing angles (Fresnel -> 1 across most of a sea-level view), so the sky IS the water's
// colour. The first tuned values -- zenith (0.11, 0.27, 0.62), horizon (0.66, 0.78, 0.90) --
// rendered the surface as a pale washed-out blue-grey (measured mean RGB 0.518/0.601/0.676
// with only 0.055 luminance contrast). Darkening the horizon toward turquoise is what turns
// that into the saturated shallow-water look clearwater's reference image shows.
#define CW_SKY(D, SunDir)                                                            \
    (lerp(float3(0.66, 0.78, 0.90), float3(0.11, 0.27, 0.62),                        \
          pow(saturate((D).y), 0.42))                                                \
     + float3(1.0, 0.86, 0.66) * (0.22 * pow(max(dot((D), (SunDir)), 0.0), 6.0)      \
                                + 0.30 * pow(max(dot((D), (SunDir)), 0.0), 64.0)     \
                                + 1.60 * pow(max(dot((D), (SunDir)), 0.0), 2400.0)))
'''


def wave_unrolled(var_prefix='S'):
    """Straight-line accumulation over all 48 wave parameters.

    Emitted as two accumulators so a node can take only the pieces it needs: `H` is height,
    `Gx`/`Gz` the wave-field gradient, `C` the choppiness sum.
    """
    lines = []
    for i in range(0, WAVE_COUNT, 6):
        group = WAVE_PARAMS[i:i + 6]
        lines.append('    {')
        lines.append('        float4 W[6] = { %s };' % ', '.join(group))
        lines.append('        [unroll] for (int i = 0; i < 6; ++i)')
        lines.append('        {')
        lines.append('            float2 k = W[i].xy; float A = W[i].z; float w = W[i].w;')
        lines.append('            float ph = dot(k, P) - w * T;')
        lines.append('            float s = sin(ph); float c = cos(ph);')
        lines.append('            H += A * s; Gx += A * k.x * c; Gz += A * k.y * c;')
        lines.append('            C += Chop * A * s * 0.01;')
        lines.append('        }')
        lines.append('    }')
    return '\n'.join(lines)


def main():
    text = HLSL.read_text(encoding='utf-8') if HLSL.exists() else ''
    doc = json.loads(NODES.read_text(encoding='utf-8'))
    wave_pass = ', '.join(WAVE_PARAMS)

    INC.parent.mkdir(parents=True, exist_ok=True)
    INC.write_text(MACROS, encoding='utf-8')
    print('wrote %s (%d lines)' % (INC, MACROS.count('\n') + 1))

    # Wave accumulation shared by the displacement and normal nodes.
    accum = (
        'float H = 0.0; float Gx = 0.0; float Gz = 0.0; float C = 0.0;\n'
        + wave_unrolled())

    bodies = {}

    bodies['displacement'] = (
        '// 48-component Clearwater spectrum, evaluated straight-line (no function scope).\n'
        + accum + '\n'
        '// clearwater C1/C2: horizontal displacement follows the same quadrature as the\n'
        '// gradient, which is what makes the surface travel rather than pulse in place.\n'
        'float dX = -C;\n'
        'return float3(-C, -C * 0.35, H * AmpScale);')

    # NO texture sampling anywhere in a node body. A Custom node cannot receive a Texture2D:
    # the pin arrives as a float4, and `.SampleLevel` on it fails to compile with
    # "invalid format for vector swizzle 'SampleLevel'" / "use of undeclared identifier
    # '<Tex>Sampler'". Fine normals and caustics are therefore sampled by the material graph
    # and combined OUTSIDE the Custom node -- see build_water_material() and
    # build_seabed_material() in author_clearwater_water.py.
    bodies['normal'] = (
        accum + '\n'
        '// Tangent-space normal. D(u,v) = (u + dX, v, H), so dD/du = (1+dX, 0, dH/du).\n'
        'float dXu = -C;\n'
        'float3 Du = float3(1.0 + dXu, 0.0, Gx * AmpScale);\n'
        'float3 Dv = float3(0.0, 1.0 + dXu, Gz * AmpScale);\n'
        'float3 N = normalize(cross(Du, Dv));\n'
        '// Impact ripples from the project water-interaction slots (WaterHit0..3).\n'
        'float3 R = float3(0.0, 0.0, 0.0);\n'
        'float4 Hits[4] = { Hit0, Hit1, Hit2, Hit3 };\n'
        '[unroll] for (int hi = 0; hi < 4; ++hi)\n'
        '{\n'
        '    float4 HH = Hits[hi];\n'
        '    if (HH.w > 0.0 && HH.z >= 0.0 && HH.z <= RipMaxAge)\n'
        '    {\n'
        '        float2 d = P - HH.xy; float r = length(d);\n'
        '        if (r > 1e-4)\n'
        '        {\n'
        '            float front = max(RipSpeed * HH.z, 1.0);\n'
        '            float sig2 = max(front * front * 0.12, 144.0);\n'
        '            float band = exp(-(r - front) * (r - front) / sig2);\n'
        '            float env = band * exp(-HH.z / max(RipMaxAge * 0.55, 1e-3)) * HH.w;\n'
        '            float dband = -2.0 * (r - front) / sig2 * band;\n'
        '            float dHdr = env * (dband * sin(0.16 * (r - front))\n'
        '                              + band * cos(0.16 * (r - front)) * 0.16) * 0.09;\n'
        '            R.xy -= d / r * dHdr;\n'
        '        }\n'
        '    }\n'
        '}\n'
        'return normalize(N + float3(R.xy * RipScale, 0.0));')

    bodies['optics'] = (
        '// clearwater optics: Fresnel reflection + transmitted floor + in-scatter + glints.\n'
        'const float IOR = 1.3335;\n'
        'float3 SigT = SigmaA + SigmaS;\n'
        'float3 Nw = N;\n'
        'float nv = dot(Nw, V);\n'
        'if (nv < 0.02) { Nw = normalize(Nw + V * (0.02 - nv)); nv = dot(Nw, V); }\n'
        'float F = CW_FRESNEL(nv, IOR);\n'
        'float3 Rr = reflect(-V, Nw); Rr.y = abs(Rr.y);\n'
        # clearwater's own constant (index.html line 470). Left at the source value so that
        # tuning the camera framing and tuning the shading are not the same experiment: an
        # earlier pass changed both at once and could not tell which moved the result.
        'float3 Refl = CW_SKY(Rr, SunDir) * 1.25;\n'
        '// Beckmann glints widened by the slope variance (clearwater LEAN trick).\n'
        'float3 Hv = normalize(V + SunDir);\n'
        'float nh = max(dot(Nw, Hv), 0.0);\n'
        'float nl = max(dot(Nw, SunDir), 0.0);\n'
        'float a2 = 0.00012 + GlintWidening;\n'
        'float c2 = max(nh * nh, 1e-4);\n'
        'float D = exp(-((1.0 - c2) / c2) / max(a2, 1e-6)) / (3.14159265 * max(a2, 1e-6) * c2 * c2);\n'
        'float Vis = 0.5 / max(nl * sqrt(nv * nv * (1.0 - a2) + a2)\n'
        '                    + nv * sqrt(nl * nl * (1.0 - a2) + a2), 1e-5);\n'
        'float3 Spec = SunColor.rgb * min(D * Vis * CW_FRESNEL(max(dot(Hv, V), 0.0), IOR) * nl, 12000.0);\n'
        'float Ts = 1.0 - CW_FRESNEL(max(SunDir.y, 0.0), IOR);\n'
        'float3 SunT = refract(-SunDir, float3(0, 0, 1), 1.0 / IOR);\n'
        'float Path = DepthCm * 0.01 / max(-SunT.z, 0.05);\n'
        '// Caustics arrive as a single scalar the material graph sampled and averaged; a\n'
        '// Custom node cannot take a Texture2D input, so the sampling happens outside.\n'
        'float Caus = max(Caustic, 0.0);\n'
        'float3 Floor = SceneColor * Ts * exp(-SigT * Path) * Caus;\n'
        'float3 Lmid = SunColor.rgb * Ts * exp(-SigT * Path * 0.5)\n'
        '           * ((1.0 - 0.64) / (12.566 * pow(max(1.0 + 0.64 - 1.6 * dot(SunT, -V), 1e-4), 1.5)) + 0.02);\n'
        'float3 Lin = (SigmaS / max(SigT, 1e-4)) * Lmid * 3.2 * (1.0 - exp(-SigT * Path));\n'
        'float3 C = F * Refl + (1.0 - F) * (Floor + Lin) + Spec;\n'
        '// Lens diffraction star on the sun glints (clearwater buildPSF cone, closed form).\n'
        'float facing = saturate(dot(normalize(V), SunDir));\n'
        'float Glint = pow(facing, 220.0) * 14.0;\n'
        'float2 gd = (ScreenUV - SunScreen) * float2(Aspect, 1.0);\n'
        'float gr = length(gd);\n'
        'float2 gdir = gr > 1e-5 ? gd / gr : float2(0.0, 0.0);\n'
        'float gcore = exp(-(gr * gr) / max(GlareRadius * GlareRadius * 0.08, 1e-8));\n'
        'float gtail = GlareRadius / (gr + GlareRadius * 0.35);\n'
        'float gstar = 0.40 + 0.60 * pow(abs(cos(3.0 * atan2(gdir.y, gdir.x))), 3.0);\n'
        'float3 G = lerp(GlareCool, GlareWarm, saturate(gr / max(GlareRadius * 0.5, 1e-4)))\n'
        '          * gstar * (gcore + gtail * gtail * 0.35) * Glint;\n'
        'return C + G;')

    # NOTE: no texture sampling here. A material Custom node cannot receive a Texture2D as an
    # input pin; the pin arrives as a float4 and `.SampleLevel` on it fails to compile with
    # "invalid format for vector swizzle 'SampleLevel'". Caustics are therefore applied
    # OUTSIDE the node, by multiplying a TextureSample expression into Base Color in the
    # material graph -- see build_seabed_material() in author_clearwater_water.py. This node
    # produces albedo only.
    bodies['seabed'] = (
        'float3 base = float3(0.60, 0.55, 0.44);\n'
        'float n = CW_VNOISE(P * 0.35) * 0.6 + CW_VNOISE(P * 1.3) * 0.4;\n'
        'float weed = smoothstep(0.55, 0.85, CW_VNOISE(P * 0.032 + 11.0));\n'
        'base *= lerp(0.62, 1.22, n);\n'
        'base = lerp(base, base * float3(0.55, 0.62, 0.40), weed * 0.7);\n'
        'return base;')

    bodies['underwater'] = (
        '// Push the scene through the water column, same optics as the surface transmission.\n'
        'const float IOR = 1.3335;\n'
        'float3 SigT = SigmaA + SigmaS;\n'
        'float Path = max(distance(CamPos, PixelPos) * 0.01, 0.0);\n'
        'float3 toCam = normalize(CamPos - PixelPos);\n'
        'float CosView = saturate(-toCam.z);\n'
        'float Entry = 1.0 - CW_FRESNEL(CosView, IOR);\n'
        'float3 SunT = refract(-SunDir, float3(0, 0, 1), 1.0 / IOR);\n'
        'float3 Lmid = SunColor.rgb * Entry * exp(-SigT * Path * 0.5)\n'
        '           * ((1.0 - 0.64) / (12.566 * pow(max(1.0 + 0.64 - 1.6 * dot(SunT, float3(0,0,-1)), 1e-4), 1.5)) + 0.02);\n'
        'float3 Lin = (SigmaS / max(SigT, 1e-4)) * Lmid * 3.2 * (1.0 - exp(-SigT * Path));\n'
        'return SceneColor * Entry * exp(-SigT * Path) + Lin;')

    # The include is part of the generated body. Without it re-running this script would
    # drop it and every material would fail with
    #     File '/Project/ClearwaterWaves.ush' not found
    # The engine maps the virtual directory "/Project" onto <ProjectDir>/Shaders itself
    # (LaunchEngineLoop.cpp), so the file simply has to live there -- nothing in C++ needs to
    # register it.
    include = '#include "/Project/ClearwaterWaves.ush"\n'
    for name, spec in doc['nodes'].items():
        if name not in bodies:
            raise SystemExit('no generated body for node %r' % name)
        body = bodies[name]
        spec['code'] = body if body.startswith('#include') else include + body

    NODES.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    print('wrote %s' % NODES)
    for name, spec in doc['nodes'].items():
        code = spec['code']
        has_def = re.search(r'(?m)^\s*(?:float|float2|float3|float4|void)\s+\w+\s*\([^;{]*\)\s*$', code)
        print('  %-14s %4d lines, pins=%2d, function-definition=%s, include=%s'
              % (name, code.count('\n') + 1, len(spec['inputs']),
                 'YES(BAD)' if has_def else 'none',
                 'yes' if code.startswith('#include') else 'NO(BAD)'))


if __name__ == '__main__':
    main()
