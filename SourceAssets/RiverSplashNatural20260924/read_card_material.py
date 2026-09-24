"""Read only the texture and material involved in the reported square card."""
import json
from pathlib import Path
import unreal as u

out = Path(u.Paths.project_dir()) / 'SourceAssets/RiverSplashNatural20260924'
t = u.load_asset('/Game/Fluids/RiverSplashNatural20260924/T_RiverSplashPacked')
m = u.load_asset('/Game/Fluids/RiverPilot20260923/M_RiverCrown')
lib = u.MaterialEditingLibrary
result = {'texture': {}, 'material': {}, 'custom_nodes': []}
for key in ('compression_settings', 'compression_no_alpha', 'compress_without_alpha',
            'compression_force_alpha', 'srgb', 'mip_gen_settings', 'lod_bias'):
    try: result['texture'][key] = str(t.get_editor_property(key))
    except Exception: pass
for key in ('blend_mode', 'translucency_lighting_mode', 'refraction_method', 'shading_model'):
    try: result['material'][key] = str(m.get_editor_property(key))
    except Exception: pass
for n in lib.get_material_expressions(m):
    if isinstance(n, u.MaterialExpressionCustom):
        result['custom_nodes'].append({'code': n.get_editor_property('code'),
                                     'type': str(n.get_editor_property('output_type'))})
for name in ('OPACITY', 'NORMAL', 'SPECULAR', 'REFRACTION'):
    p = getattr(u.MaterialProperty, 'MP_' + name)
    n = lib.get_material_property_input_node(m, p)
    result['material'][name] = n.get_name() if n else None
(out / 'card-material-before.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
u.log('RIVER_CARD_MATERIAL ' + json.dumps(result))
