"""Read the reported blade-rune material contract and any existing TangDao instance."""
import unreal as u, json
from pathlib import Path
P = Path(__file__).parent
E = u.MaterialEditingLibrary
rows = {'materials': [], 'meshes': [], 'instances': []}
paths = ['/Game/Weapons/TangDao20261002/Materials/M_TangDaoSurface',
         '/Game/Weapons/TangDao20261002/SurfaceV2/Materials/M_TangDaoSurface',
         '/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2']
for path in paths:
    mat = u.load_asset(path)
    row = {'path': path, 'present': bool(mat)}
    if mat:
        row.update(two_sided=mat.get_editor_property('two_sided'),
                   blend_mode=str(mat.get_editor_property('blend_mode')),
                   used_with_nanite=mat.get_editor_property('used_with_nanite'),
                   outputs={name: str(E.get_material_property_input_node(mat, prop)) for name, prop in [
                       ('front_material', u.MaterialProperty.MP_FRONT_MATERIAL),
                       ('emissive', u.MaterialProperty.MP_EMISSIVE_COLOR),
                       ('opacity', u.MaterialProperty.MP_OPACITY),
                       ('world_position_offset', u.MaterialProperty.MP_WORLD_POSITION_OFFSET)]})
        row['nodes'] = []
        for node in E.get_material_expressions(mat):
            entry = {'class': node.get_class().get_name(), 'name': node.get_name()}
            if isinstance(node, u.MaterialExpressionCustom):
                entry['code'] = node.get_editor_property('code')
            if isinstance(node, u.MaterialExpressionVectorParameter):
                entry.update(parameter=str(node.get_editor_property('parameter_name')), value=str(node.get_editor_property('default_value')))
            if isinstance(node, u.MaterialExpressionScalarParameter):
                entry.update(parameter=str(node.get_editor_property('parameter_name')), value=node.get_editor_property('default_value'))
            row['nodes'].append(entry)
    rows['materials'].append(row)
for name in ['factory', 'heavy_spine', 'feather_edge', 'extended_edge']:
    path = '/Game/Weapons/TangDao20261002/Meshes/SM_TangDao_Blade_'+name
    mesh = u.load_asset(path)
    if mesh:
        rows['meshes'].append({'path': mesh.get_path_name(), 'nanite_enabled': mesh.get_editor_property('nanite_settings').enabled,
                               'slots': [{'name': str(s.material_slot_name), 'material': s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.static_materials]})
commandlet = '-run=' in u.SystemLibrary.get_command_line().lower()
editor = None if commandlet else u.get_editor_subsystem(u.UnrealEditorSubsystem)
world = editor.get_game_world() if editor else None
rows['existing_game_world'] = bool(world)
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.FPSGAMECharacter):
        for comp in actor.get_components_by_class(u.StaticMeshComponent):
            mesh = comp.get_static_mesh()
            if not mesh or 'TangDao' not in mesh.get_path_name():
                continue
            row = {'component': comp.get_name(), 'mesh': mesh.get_path_name(), 'materials': [], 'tags': [str(t) for t in comp.component_tags]}
            for slot in range(comp.get_num_materials()):
                base = comp.get_material(slot)
                overlay = comp.get_overlay_material(True, slot)
                entry = {'slot': slot, 'base': base.get_path_name() if base else None, 'overlay': overlay.get_path_name() if overlay else None}
                if isinstance(overlay, u.MaterialInstanceDynamic):
                    entry['scalar_params'] = {key: overlay.k2_get_scalar_parameter_value(key) for key in ['RuneMode', 'GlowStrength', 'GoldenTint']}
                    entry['vector_params'] = {key: str(overlay.k2_get_vector_parameter_value(key)) for key in ['Dimensions', 'BladeAxis', 'BladeOrigin']}
                    tex = overlay.k2_get_texture_parameter_value('RuneTexture')
                    entry['mask'] = tex.get_path_name() if tex else None
                row['materials'].append(entry)
            rows['instances'].append(row)
(P/'state_before.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
print('TANGDAO_RUNE_STATE_READ', json.dumps({key: value if key not in ['materials'] else [{'path': x['path'], 'outputs': x.get('outputs')} for x in value] for key, value in rows.items()}, ensure_ascii=False))
