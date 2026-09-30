"""Compile the master's Custom-node bodies out of process (fxc SM5, dxc SM6).

The headless commandlet only translates the material graph; Custom HLSL syntax is
checked here with the Windows SDK compilers, using the exact input types the graph
connects (see build_master.py). Plain CPython.
"""
import subprocess
import sys
from pathlib import Path

O = Path(__file__).parent
BIN = Path(r'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64')
TMP = O / 'logs' / 'hlsl_check'
TMP.mkdir(parents=True, exist_ok=True)
F1, F2, F3, F4 = 'float', 'float2', 'float3', 'float4'
NODES = {
    'WS_Grain': (F4, {'P': F3, 'N': F3, 'Tex': 'TEX', 'TileCm': F1}),
    'WS_Wear': (F4, {'Mask': F4, 'Grain': F4, 'EdgeWear': F1, 'EdgeBreakup': F1, 'EdgeContrast': F1, 'ScratchAmount': F1}),
    'WS_ColorRough': (F4, {'Src': F3, 'SrcR': F1, 'Mask': F4, 'Grain': F4, 'Wear': F4, 'Finish': F3, 'SrcW': F1,
                           'Rough': F1, 'SrcRW': F1, 'Pivot': F1, 'GrainR': F1, 'MottleR': F1, 'MottleC': F1,
                           'Stipple': F1, 'EdgeColor': F3, 'EdgeRough': F1, 'EdgeHL': F1, 'CavDark': F1,
                           'CavRough': F1, 'Handling': F1}),
    'WS_MetalAO': (F4, {'Metal': F1, 'EdgeMetal': F1, 'Wear': F4, 'Mask': F4, 'AOStrength': F1}),
    'WS_Beads': (F4, {'UV': F2, 'Wet': F1, 'Scale': F1}),
    'WS_Wet': (F4, {'CR': F4, 'Data': F4}),
    'WS_WetNormal': (F3, {'Base': F3, 'Data': F4}),
}
PRE = '#define MaterialFloat float\n#define Texture2DSample(t,s,uv) t.Sample(s,uv)\n'
failed = 0
for name, (ret, inputs) in NODES.items():
    body = (O / 'hlsl' / (name + '.hlsl')).read_text(encoding='utf-8-sig')
    decl, args = [], []
    for pin, kind in inputs.items():
        if kind == 'TEX':
            decl.append('Texture2D %s; SamplerState %sSampler;' % (pin, pin))
        else:
            args.append('%s %s' % (kind, pin))
    wrap = {F3: 'return float4(node(%s),1);', F4: 'return node(%s);'}[ret]
    call = ', '.join('0.5' if k == F1 else '(%s)0.5' % k for k in inputs.values() if k != 'TEX')
    text = PRE + '\n'.join(decl) + '\n%s node(%s)\n{\n%s\n}\nfloat4 main() : SV_Target0\n{\n    %s\n}\n' % (
        ret, ', '.join(args), body, wrap % call)
    path = TMP / (name + '.hlsl')
    path.write_text(text, encoding='utf-8')
    for exe, extra in [('fxc.exe', ['/nologo', '/T', 'ps_5_0', '/E', 'main']),
                       ('dxc.exe', ['-T', 'ps_6_0', '-E', 'main', '-Wno-ignored-attributes'])]:
        r = subprocess.run([str(BIN / exe), *extra, str(path)] + (['/Fo', str(path.with_suffix('.cso'))] if exe == 'fxc.exe' else ['-Fo', str(path.with_suffix('.dxil'))]),
                           capture_output=True, text=True)
        ok = r.returncode == 0
        failed += not ok
        print(name.ljust(14), exe.ljust(8), 'OK' if ok else 'FAIL')
        if not ok:
            print((r.stdout + r.stderr)[-1500:])
sys.exit(1 if failed else 0)
