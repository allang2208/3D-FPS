"""Read only the shell material assignments needed for the reported color fix."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
root = '/Game/Weapons/Super90/Cransh20261006'
mesh = u.load_asset(root + '/SK_Super90_V7')
data = {'pie': bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),
        'slots': [], 'materials': {},
        'all_slots': [{'index': i, 'slot': str(s.material_slot_name),
                       'material': s.material_interface.get_path_name() if s.material_interface else None}
                      for i, s in enumerate(mesh.materials)]}
for slot in mesh.materials:
    name = str(slot.material_slot_name)
    if '12gauge' not in name:
        continue
    material = slot.material_interface
    data['slots'].append({'slot': name, 'material': material.get_path_name()})
    if material.get_path_name() in data['materials']:
        continue
    info = {'class': material.get_class().get_name()}
    if isinstance(material, u.Material):
        info['expressions'] = []
        for ex in u.MaterialEditingLibrary.get_material_expressions(material):
            item = {'class': ex.get_class().get_name()}
            for prop in ('texture', 'coordinate_index', 'u_tiling', 'v_tiling', 'constant', 'r'):
                try:
                    value = ex.get_editor_property(prop)
                    item[prop] = value.get_path_name() if isinstance(value, u.Object) else str(value)
                except Exception:
                    pass
            info['expressions'].append(item)
    else:
        info['parent'] = material.get_editor_property('parent').get_path_name()
        for prop in ('texture_parameter_values', 'scalar_parameter_values', 'vector_parameter_values'):
            info[prop] = str(material.get_editor_property(prop))
    data['materials'][material.get_path_name()] = info
data['dirty_packages'] = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
                          if 'Super90' in p.get_name()]
sub = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
data['lod_sections'] = [[sub.get_lod_material_slot(mesh, lod, section)
                         for section in range(sub.get_num_sections(mesh, lod))]
                        for lod in range(sub.get_lod_count(mesh))]
data['imported_names'] = [str(slot.get_editor_property('imported_material_slot_name')) for slot in mesh.materials]
data['source_lod_maps'] = [list(model.get_editor_property('lod_material_map')) for model in mesh.get_editor_property('source_models')]
(O / 'material_inputs.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
print(json.dumps(data, indent=2))
