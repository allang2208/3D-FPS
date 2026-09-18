"""Structural audit of the rebuilt ground materials: reachability and parameter use.

A Custom node that no output reaches is still compiled into the shader and costs
instructions, and an unreachable scalar parameter is a knob that does nothing. The
commandlet cannot render, so this walks the graph instead.
"""
import json
from pathlib import Path
import unreal as u

LIB = u.MaterialEditingLibrary
OUT = Path('D:/FPS3D/FPSGAME/Saved/GroundMaterialUpgrade20260918')
MATERIALS = ['/Game/WorldGeneration/TemperateHills/M_TemperateGround',
             '/Game/WorldGeneration/TemperateHills/PebbleShore/M_PebbleShoreGround']
PROPS = ('BASE_COLOR', 'NORMAL', 'ROUGHNESS', 'AMBIENT_OCCLUSION')
report = {}


def walk(mat, roots):
    seen = {}
    stack = list(roots)
    while stack:
        node = stack.pop()
        if node is None or node in seen:
            continue
        seen[node] = True
        for src in (LIB.get_inputs_for_material_expression(mat, node) or []):
            stack.append(src)
    return seen


def describe(expr):
    label = expr.__class__.__name__
    for prop in ('desc', 'parameter_name', 'code'):
        try:
            v = expr.get_editor_property(prop)
        except Exception:
            continue
        if v:
            text = ' '.join(str(v).split())[:60]
            return '%s %s' % (label, text)
    return label


for path in MATERIALS:
    mat = u.load_asset(path)
    if mat is None:
        report[path] = 'MISSING'
        continue
    expressions = list(LIB.get_material_expressions(mat) or [])
    roots = [LIB.get_material_property_input_node(mat, getattr(u.MaterialProperty, 'MP_' + name))
             for name in PROPS]
    reachable = walk(mat, roots)
    orphans = [e for e in expressions if e not in reachable]
    parameters = {}
    for e in expressions:
        if e.__class__.__name__ in ('MaterialExpressionScalarParameter', 'MaterialExpressionVectorParameter',
                                    'MaterialExpressionTextureObjectParameter'):
            parameters[str(e.get_editor_property('parameter_name'))] = (e in reachable)
    report[path] = {
        'expressions': len(expressions),
        'reachable': len(reachable),
        'orphans': [describe(e) for e in orphans],
        'parameters_unreachable': sorted(n for n, used in parameters.items() if not used),
        'parameters': len(parameters),
        'outputs': {name: (describe(LIB.get_material_property_input_node(
            mat, getattr(u.MaterialProperty, 'MP_' + name))) if LIB.get_material_property_input_node(
            mat, getattr(u.MaterialProperty, 'MP_' + name)) else None) for name in PROPS},
    }

(OUT / 'structure_audit.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
u.log('GROUND_STRUCTURE ' + json.dumps(report, ensure_ascii=False))
print(json.dumps(report, indent=2, ensure_ascii=False))
