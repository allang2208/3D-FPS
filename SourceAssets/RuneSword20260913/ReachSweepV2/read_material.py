"""Read the bindings/settings implicated in the user's missing-material report."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).parent
D = '/Game/Weapons/AzureRunesword20260913'
mat = u.load_asset(D + '/M_AzureRunesword')
report = {'material': mat.get_path_name(), 'settings': {}, 'inputs': {}, 'textures': {}, 'bindings': {}}
for prop in ['used_with_skeletal_mesh', 'automatically_set_usage_in_editor', 'blend_mode', 'shading_model']:
    try:
        report['settings'][prop] = str(mat.get_editor_property(prop))
    except Exception as exc:
        report['settings'][prop] = str(exc)
for prop in ['BASE_COLOR', 'NORMAL', 'METALLIC', 'ROUGHNESS', 'EMISSIVE_COLOR']:
    node = u.MaterialEditingLibrary.get_material_property_input_node(mat, getattr(u.MaterialProperty, 'MP_' + prop))
    report['inputs'][prop] = node.get_class().get_name() if node else None
for name in ['BaseColor', 'Normal', 'Metallic', 'Roughness', 'Emissive']:
    tex = u.load_asset(D + '/T_RuneSword_' + name)
    report['textures'][name] = {'path': tex.get_path_name(), 'srgb': tex.get_editor_property('srgb'),
        'compression': str(tex.get_editor_property('compression_settings')),
        'width': tex.blueprint_get_size_x(), 'height': tex.blueprint_get_size_y()}
sk = u.load_asset(D + '/SK_AzureRunesword_Manny')
report['bindings']['skeletal'] = [{'slot': str(s.material_slot_name), 'material': s.material_interface.get_path_name() if s.material_interface else None} for s in sk.get_editor_property('materials')]
sm = u.load_asset(D + '/SM_AzureRunesword')
report['bindings']['world'] = [{'slot': str(s.material_slot_name), 'material': s.material_interface.get_path_name() if s.material_interface else None} for s in sm.get_editor_property('static_materials')]
(P / 'material_before.json').write_text(json.dumps(report, indent=2))
u.log('RUNESWORD_MATERIAL_REPORT_WRITTEN')
