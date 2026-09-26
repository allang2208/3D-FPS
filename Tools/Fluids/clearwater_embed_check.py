"""Offline dry-run of the Clearwater material Custom-node code, wrapped the way UE wraps it.

THE POINT OF THIS FILE
----------------------
The first version of this check assembled each node's code as a free-standing function at
file scope. That compiled cleanly and was useless: Unreal emits a Custom node's `code` field
into the BODY of a generated function,

    float3 CustomExpression0(FMaterialPixelParameters Parameters, float2 P, ...)
    {
        <code field here>
    }

and function definitions are illegal there. So the check reported success while every real
material failed to compile and UE silently substituted the Default Material. A validation
that does not reproduce the host's structure is worse than no validation, because it
manufactures confidence.

This version reproduces the wrapper exactly, resolves the `#include` the way the shader
compiler will, and additionally rejects a node body that defines a function.

    python Tools/Fluids/clearwater_embed_check.py
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'SourceAssets' / 'ClearwaterWater20260926'
NODES = ASSETS / 'nodes.json'
INC_NAME = 'ClearwaterWaves.ush'
INC_PATH = ROOT / 'Shaders' / INC_NAME
FXC = r'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\fxc.exe'
DXC = r'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\dxc.exe'

PIN_TYPES = {
    'P': 'float2', 'T': 'float', 'Chop': 'float', 'AmpScale': 'float',
    'FineNormalMap': 'Texture2D', 'RipSpeed': 'float', 'RipMaxAge': 'float',
    'RipScale': 'float', 'Hit0': 'float4', 'Hit1': 'float4', 'Hit2': 'float4',
    'Hit3': 'float4', 'N': 'float3', 'V': 'float3', 'SunDir': 'float3',
    'SunColor': 'float4', 'SceneColor': 'float3', 'SigmaA': 'float3', 'SigmaS': 'float3',
    'DepthCm': 'float', 'GlintWidening': 'float', 'CausticMap': 'Texture2D',
    'CausShiftA': 'float4', 'CausShiftB': 'float4', 'CausScale': 'float',
    'CausStrength': 'float', 'Base': 'float3', 'WaterDepthCm': 'float',
    'PixelPos': 'float3', 'CamPos': 'float3', 'ScreenUV': 'float2', 'SunScreen': 'float2',
    'Aspect': 'float', 'GlareRadius': 'float', 'GlareWarm': 'float3', 'GlareCool': 'float3',
    # Caustics reach the optics node as a scalar the material graph already sampled:
    # a Custom node cannot receive a Texture2D pin.
    'Caustic': 'float',
}
WAVE_PIN = re.compile(r'^W\d+$')

# A function definition that has leaked into a node body: the exact failure the first
# Clearwater pass shipped. Checked explicitly so it fails regardless of compiler leniency.
NESTED_DEF = re.compile(
    r'(?m)^\s*(?:float|float2|float3|float4|void)\s+[A-Za-z_]\w*\s*\([^;{]*\)\s*$')


def pin_type(name):
    if WAVE_PIN.match(name):
        return 'float4'
    if name not in PIN_TYPES:
        raise RuntimeError('unknown pin %r: add it to PIN_TYPES' % name)
    return PIN_TYPES[name]


def sample_arg(name):
    t = pin_type(name)
    return {'float': '1.0', 'float2': 'uv', 'float3': 'float3(0.2, 0.3, 0.4)',
            'float4': 'float4(1.0, 0.5, 10.0, 5.0)'}.get(t, 'TestTex')


def translation_unit(name, spec, wave_pass):
    """Reproduce Unreal's emission: the node code sits INSIDE a generated function body.

    The `#include` stays in the body, exactly as Unreal leaves it, and is resolved by passing
    the shader directory on the include path.
    """
    body = spec['code'].replace('{wavePass}', wave_pass)
    inputs = spec['inputs']
    params = ', '.join('%s %s' % (pin_type(p), p) for p in inputs)
    args = ', '.join(sample_arg(p) for p in inputs)
    samplers = ''.join('\nSamplerState %sSampler;' % p
                       for p in inputs if pin_type(p) == 'Texture2D')
    return (
        'Texture2D TestTex;\nSamplerState TestSamp;\n'
        + samplers + '\n'
        + 'float3 CustomExpression0(float2 uv, %s)\n{\n%s\n}\n' % (params, body)
        + 'float4 main(float2 uv : TEXCOORD0) : SV_Target\n{\n'
        + '    return float4(CustomExpression0(uv, %s), 1.0);\n}\n' % args)


def compile_one(path, exe, extra, include_dir):
    cmd = [exe] + extra + ['/I', str(include_dir)]
    cmd += (['/Fo', 'NUL'] if 'fxc' in exe.lower() else ['-Fo', 'NUL'])
    cmd += [str(path)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, (proc.stderr or '') + (proc.stdout or '')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--keep', action='store_true', help='keep the generated .hlsl files')
    args = ap.parse_args()

    if not INC_PATH.exists():
        print('CLEARWATER_EMBED_CHECK FAILED: missing %s '
              '(run Tools/Fluids/clearwater_generate_nodes.py)' % INC_PATH)
        return 1

    out = ROOT / 'Saved' / 'ClearwaterEmbedCheck'
    out.mkdir(parents=True, exist_ok=True)
    include_dir = INC_PATH.parent

    doc = json.loads(NODES.read_text(encoding='utf-8'))
    wave_pass = doc['wavePass']
    failures = []

    for name, spec in doc['nodes'].items():
        leaked = NESTED_DEF.findall(spec['code'])
        if leaked:
            failures.append([name, 'nested-function-definition'])
            print('%-12s STATIC FAIL: body defines a function -> %s' % (name, leaked))
            continue
        marker = '#include "/Project/%s"' % INC_NAME
        if marker not in spec['code']:
            failures.append([name, 'missing-include'])
            print('%-12s STATIC FAIL: body does not include /Project/%s' % (name, INC_NAME))
            continue

        # The shader is mounted at /Project in Unreal; rewrite it to the real path so the
        # local compiler can resolve the same #include.
        local = dict(spec, code=spec['code'].replace(marker, '#include "%s"' % INC_NAME))
        path = out / ('node_%s.hlsl' % name)
        path.write_text(translation_unit(name, local, wave_pass), encoding='utf-8')

        for tag, exe, extra in (('sm5', FXC, ['/nologo', '/T', 'ps_5_0']),
                                ('sm6', DXC, ['-T', 'ps_6_0', '-Wno-ignored-attributes'])):
            rc, log = compile_one(path, exe, extra, include_dir)
            ok = rc == 0
            if not ok:
                failures.append([name, tag])
            print('%-12s %-4s %s' % (name, tag, 'OK' if ok else 'FAIL'))
            if not ok:
                for line in log.splitlines():
                    if 'error' in line.lower():
                        print('    ' + line.strip())
        if not args.keep:
            path.unlink(missing_ok=True)

    if failures:
        print('CLEARWATER_EMBED_CHECK FAILED ' + json.dumps(failures))
        return 1
    print('CLEARWATER_EMBED_CHECK OK (%d nodes x 2 compilers, wrapped as Unreal wraps them)'
          % len(doc['nodes']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
