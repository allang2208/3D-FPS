"""Read only the saved blade-rune chain; no game, preview or asset writes."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[3]
E = u.MaterialEditingLibrary
result = {'materials': [], 'blades': [], 'catalog': {}}
catalog = json.loads((ROOT / 'Content/ColdSteelData/tang-dao-modules.json').read_text(encoding='utf-8-sig'))
result['catalog'] = catalog
for path in [
    '/Game/Weapons/TangDao20261002/SurfaceV2/Materials/M_TangDaoSurface',
    '/Game/Weapons/TangDao20261002/SurfaceV2/Materials/M_TangDaoSurface_Whirlwind',
    '/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2',
]:
    mat = u.load_asset(path)
    row = {'path': path, 'present': bool(mat), 'nodes': []}
    if mat:
        row['settings'] = {}
        for name in ['blend_mode', 'shading_model', 'two_sided', 'used_with_nanite', 'use_material_attributes', 'disable_depth_test', 'translucency_pass']:
            try:
                row['settings'][name] = str(mat.get_editor_property(name))
            except Exception:
                pass
        row['outputs'] = {name: str(E.get_material_property_input_node(mat, prop)) for name, prop in [
            ('front', u.MaterialProperty.MP_FRONT_MATERIAL), ('emissive', u.MaterialProperty.MP_EMISSIVE_COLOR),
            ('opacity', u.MaterialProperty.MP_OPACITY), ('normal', u.MaterialProperty.MP_NORMAL)]}
        for node in E.get_material_expressions(mat):
            entry = {'class': node.get_class().get_name(), 'name': node.get_name()}
            for key in ['code', 'inputs', 'parameter_name', 'default_value', 'texture', 'instance_space', 'transform_source_type', 'transform_type', 'interpolated', 'shader_offsets', 'use_absolute_world_position']:
                try:
                    entry[key] = str(node.get_editor_property(key))
                except Exception:
                    pass
            try:
                entry['connected_inputs'] = [x.get_name() if x else None for x in E.get_inputs_for_material_expression(mat, node)]
            except Exception:
                pass
            row['nodes'].append(entry)
    result['materials'].append(row)
for name in ['factory', 'extended_edge', 'heavy_spine', 'feather_edge']:
    mesh = u.load_asset('/Game/Weapons/TangDao20261002/Meshes/SM_TangDao_Blade_' + name)
    row = {'variant': name, 'present': bool(mesh)}
    if mesh:
        row.update(path=mesh.get_path_name(), nanite=mesh.get_editor_property('nanite_settings').enabled,
                   bounds=str(mesh.get_bounding_box()),
                   materials=[{'slot': str(s.material_slot_name), 'path': s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.static_materials])
    result['blades'].append(row)
result['masks'] = []
for name in ['resonance_rune', 'erosion_rune', 'conduction_rune']:
    tex = u.load_asset('/Game/Weapons/MeleeRunes20260915/SurfaceV2/T_Mask_' + name)
    result['masks'].append({'rune': name, 'present': bool(tex), 'path': tex.get_path_name() if tex else None})
(P / 'state_before.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('TANGDAO_RUNE_FOLLOWUP_READ', json.dumps({'blades': result['blades'], 'masks': result['masks']}, ensure_ascii=False))
