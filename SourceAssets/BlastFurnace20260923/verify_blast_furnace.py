"""Independent-process read-back of the installed furnace assets.

Run in its own commandlet so the numbers do not come from the same process that
wrote them:

    & UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this> -unattended -nop4 -nosplash
"""
import json
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
MESH = '/Game/Props/BlastFurnace20260923/SM_BlastFurnace'
PALETTE = '/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette'

report = {}

mesh = u.load_asset(MESH)
if mesh is None:
    raise SystemExit('READBACK_FAILED mesh missing: ' + MESH)
box = mesh.get_bounds()


def probe(name, *args):
    # getattr first: accessing a missing attribute in the caller would raise
    # outside this guard.
    function = getattr(mesh, name, None)
    if function is None:
        return 'unavailable: StaticMesh has no ' + name
    try:
        return function(*args)
    except Exception as error:  # noqa: BLE001 - read-back should not fail hard
        return 'unavailable: %s' % error


report['mesh'] = {
    'asset': mesh.get_path_name(),
    'size_cm': [round(2 * box.box_extent.x, 4), round(2 * box.box_extent.y, 4), round(2 * box.box_extent.z, 4)],
    'origin_cm': [round(box.origin.x, 4), round(box.origin.y, 4), round(box.origin.z, 4)],
    'triangles': probe('get_num_triangles', 0),
    'uv_channels': probe('get_num_uv_channels', 0),
    'slots': [{'slot': str(s.get_editor_property('material_slot_name')),
               'material': s.get_editor_property('material_interface').get_path_name()
               if s.get_editor_property('material_interface') else None}
              for s in mesh.get_editor_property('static_materials')],
    'nanite': bool(mesh.get_editor_property('nanite_settings').enabled),
    'collision_trace_flag': str(mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')),
}

palette = u.load_asset(PALETTE)
if palette is None:
    raise SystemExit('READBACK_FAILED palette missing: ' + PALETTE)
entries = palette.get_editor_property('components')
report['palette'] = {
    'asset': palette.get_path_name(),
    'entry_count': len(entries),
    'entries': [{'id': str(e.get_editor_property('id')),
                 'footprint': [e.get_editor_property('footprint').x, e.get_editor_property('footprint').y,
                               e.get_editor_property('footprint').z],
                 'mesh': e.get_editor_property('mesh').get_path_name() if e.get_editor_property('mesh') else None,
                 'pivot_offset_cm': [round(e.get_editor_property('pivot_offset_cm').x, 4),
                                     round(e.get_editor_property('pivot_offset_cm').y, 4),
                                     round(e.get_editor_property('pivot_offset_cm').z, 4)]}
                for e in entries],
}

# A material can compile while a pin is silently unconnected, so every output
# is checked by asking which node feeds it, not by trusting recompile's [].
MATERIAL_NAMES = ('Masonry', 'Firebrick', 'WroughtIron', 'ClayLuting',
                  'SlagLining', 'EmberBed', 'OreLump')
PROPERTIES = (('BaseColor', u.MaterialProperty.MP_BASE_COLOR),
              ('Roughness', u.MaterialProperty.MP_ROUGHNESS),
              ('Metallic', u.MaterialProperty.MP_METALLIC),
              ('Normal', u.MaterialProperty.MP_NORMAL))
materials = {}
for name in MATERIAL_NAMES:
    path = '/Game/Props/BlastFurnace20260923/Materials/M_BlastFurnace_' + name
    mat = u.load_asset(path)
    if mat is None:
        materials[name] = 'missing'
        continue
    nodes = u.MaterialEditingLibrary.get_material_expressions(mat)
    inputs = {}
    for label, prop in PROPERTIES:
        node = u.MaterialEditingLibrary.get_material_property_input_node(mat, prop)
        inputs[label] = str(node.get_class().get_name()) if node else None
    materials[name] = {'expression_count': len(nodes), 'output_inputs': inputs,
                       'all_inputs_connected': all(inputs[label] for label, _ in PROPERTIES)}
report['materials'] = materials
report['materials_ok'] = all(isinstance(v, dict) and v['all_inputs_connected'] for v in materials.values())

(HERE / 'verify_receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('BLAST_FURNACE_READBACK ' + json.dumps(report, ensure_ascii=False), flush=True)
