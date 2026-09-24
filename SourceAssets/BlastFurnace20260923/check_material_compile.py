"""Recompile the furnace materials and report what actually drives BaseColor.

    & UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this> -unattended -nop4 -nosplash -AllowCommandletRendering

If a material fails to compile, UE keeps the last good shader and the mesh
renders with whatever fallback that shader has -- which is exactly the
untextured look in game even though the asset graph looks correct.
"""
import json
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
ROOT = '/Game/Props/BlastFurnace20260923'
SLOTS = ('Masonry', 'Firebrick', 'WroughtIron', 'ClayLuting',
         'SlagLining', 'EmberBed', 'OreLump')
LIB = u.MaterialEditingLibrary

report = {}
for name in SLOTS:
    path = '%s/Materials/M_BlastFurnace_%s' % (ROOT, name)
    material = u.load_asset(path)
    if material is None:
        report[name] = {'loaded': False}
        continue
    errors = LIB.recompile_material(material)
    base_node = LIB.get_material_property_input_node(material, u.MaterialProperty.MP_BASE_COLOR)
    rough_node = LIB.get_material_property_input_node(material, u.MaterialProperty.MP_ROUGHNESS)
    normal_node = LIB.get_material_property_input_node(material, u.MaterialProperty.MP_NORMAL)
    metal_node = LIB.get_material_property_input_node(material, u.MaterialProperty.MP_METALLIC)

    def describe(node):
        if node is None:
            return None
        kind = node.get_class().get_name()
        if kind == 'MaterialExpressionTextureSampleParameter2D':
            texture = node.get_editor_property('texture')
            return {'node': kind, 'texture': texture.get_name() if texture else None}
        return {'node': kind}

    expressions = LIB.get_material_expressions(material)
    report[name] = {
        'compile_errors': [str(e) for e in errors],
        'expression_count': len(expressions),
        'inputs': {'BaseColor': describe(base_node), 'Roughness': describe(rough_node),
                   'Normal': describe(normal_node), 'Metallic': describe(metal_node)},
    }
    print('MATERIAL_COMPILE %-14s errors=%d expr=%d base=%s'
          % (name, len(errors), len(expressions),
             json.dumps(report[name]['inputs']['BaseColor'], ensure_ascii=False)), flush=True)

(HERE / 'compile-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                         encoding='utf-8')
bad = [k for k, v in report.items() if v.get('compile_errors')]
print('MATERIAL_COMPILE_DONE broken=%s' % (bad if bad else 'none'), flush=True)
