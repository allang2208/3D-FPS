"""Dump every Custom node body from the built ground materials as standalone HLSL.

The commandlet cannot compile material shaders (nothing renders), so the Custom node
HLSL is validated out of process with the Windows SDK shader compiler instead:
this script writes one .hlsl file per node with the connected input types, and
Tools/WorldGeneration/validate_ground_hlsl.ps1 runs fxc and dxc over them.
"""
import json
from pathlib import Path
import unreal as u

LIB = u.MaterialEditingLibrary
OUT = Path('D:/FPS3D/FPSGAME/Saved/GroundMaterialUpgrade20260918/hlsl')
OUT.mkdir(parents=True, exist_ok=True)

MATERIALS = [('hill', '/Game/WorldGeneration/TemperateHills/M_TemperateGround'),
             ('pebble', '/Game/WorldGeneration/TemperateHills/PebbleShore/M_PebbleShoreGround')]

WIDTHS = {'CMOT_FLOAT1': ('float', 1), 'CMOT_FLOAT2': ('float2', 2),
          'CMOT_FLOAT3': ('float3', 3), 'CMOT_FLOAT4': ('float4', 4)}


def output_type(expr):
    name = expr.__class__.__name__
    if name == 'MaterialExpressionCustom':
        raw = expr.get_editor_property('output_type')
        key = getattr(raw, 'name', None) or str(raw).split('.')[-1].split(':')[0].strip()
        if key not in WIDTHS:
            raise RuntimeError('Unmapped custom output type: %r (from %r)' % (key, raw))
        return WIDTHS[key]
    if name == 'MaterialExpressionTextureSample':
        return ('float4', 4)
    if name == 'MaterialExpressionVertexColor':
        return ('float4', 4)
    if name in ('MaterialExpressionWorldPosition', 'MaterialExpressionVertexNormalWS',
                'MaterialExpressionCameraPositionWS', 'MaterialExpressionCameraVectorWS',
                'MaterialExpressionObjectPositionWS'):
        return ('float3', 3)
    if name == 'MaterialExpressionScalarParameter':
        return ('float', 1)
    raise RuntimeError('Unmapped input expression: ' + name)


PREAMBLE = '''// Standalone compile check for one material Custom node.
// UE supplies these; the stubs keep the node body identical to what the material
// compiler emits.
#define MaterialFloat float
float4 Texture2DSampleGrad(Texture2D t, SamplerState s, float2 uv, float2 gx, float2 gy)
{
    return t.SampleGrad(s, uv, gx, gy);
}
'''


def input_declarations(pins, upstream):
    """Texture objects arrive as a Texture2D plus the implicit <name>Sampler."""
    lines = []
    for name, src in zip(pins, upstream):
        if src.__class__.__name__ == 'MaterialExpressionTextureObject':
            lines.append('Texture2D %s; SamplerState %sSampler;' % (name, name))
        else:
            lines.append('%s %s;' % (output_type(src)[0], name))
    return lines

report = []
for label, path in MATERIALS:
    mat = u.load_asset(path)
    if mat is None:
        raise RuntimeError('Missing material ' + path)
    index = 0
    for expr in LIB.get_material_expressions(mat) or []:
        if expr.__class__.__name__ != 'MaterialExpressionCustom':
            continue
        code = expr.get_editor_property('code')
        rtype, _ = output_type(expr)
        pins = [str(n) for n in LIB.get_material_expression_input_names(expr)]
        upstream = list(LIB.get_inputs_for_material_expression(mat, expr) or [])
        if len(pins) != len(upstream):
            raise RuntimeError('Input/upstream mismatch on %s: %s vs %s' % (label, pins, upstream))
        params = input_declarations(pins, upstream)
        entry = {'float': 'return float4(node_body(),0.0,0.0,1.0);',
                 'float2': 'return float4(node_body(),0.0,1.0);',
                 'float3': 'return float4(node_body(),1.0);',
                 'float4': 'return node_body();'}[rtype]
        text = (PREAMBLE +
                '// ---- inputs ----\n' + '\n'.join(params) + '\n' +
                '// ---- node %s #%d (%s) ----\n' % (label, index, rtype) +
                '%s node_body()\n{\n%s\n}\n' % (rtype, code) +
                'float4 main() : SV_Target0\n{\n    ' + entry + '\n}\n')
        name = '%s_%02d_%s' % (label, index, str(expr.get_editor_property('desc') or 'custom').replace(' ', '_'))
        (OUT / (name + '.hlsl')).write_text(text, encoding='utf-8')
        report.append({'file': name + '.hlsl', 'material': path, 'return': rtype,
                       'desc': str(expr.get_editor_property('desc') or ''), 'params': pins})
        index += 1

(OUT / 'index.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
u.log('GROUND_HLSL_DUMP files=%d' % len(report))
print('wrote %d hlsl files' % len(report))
