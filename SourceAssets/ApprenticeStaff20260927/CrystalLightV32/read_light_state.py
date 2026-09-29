"""Read the user's existing world and crystal bindings; never start or drive PIE."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
report = {'world': None, 'players': [], 'head_materials': []}
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world:
    report['world'] = world.get_path_name()
    for pawn in u.GameplayStatics.get_all_actors_of_class(world, u.FPSGAMECharacter):
        entry = {'actor': pawn.get_name(), 'hidden': pawn.get_editor_property('hidden'),
                 'local': pawn.is_locally_controlled(), 'lights': [], 'staff': []}
        for light in pawn.get_components_by_class(u.PointLightComponent):
            if light.get_name() != 'StaffCrystalLight':
                continue
            entry['lights'].append({'name': light.get_name(),
                'intensity': light.get_editor_property('intensity'),
                'visible': light.is_visible(), 'hidden': light.get_editor_property('hidden_in_game'),
                'affects_world': light.get_editor_property('affects_world'),
                'position': str(light.get_world_location())})
        for part in pawn.get_components_by_class(u.StaticMeshComponent):
            if part.get_name() != 'StaffAssembly' and not part.component_has_tag('StaffPart'):
                continue
            item = {'name': part.get_name(), 'visible': part.is_visible(), 'materials': [],
                    'relative_location': str(part.get_editor_property('relative_location')),
                    'relative_rotation': str(part.get_editor_property('relative_rotation'))}
            for index in range(part.get_num_materials()):
                material = part.get_material(index)
                if not material:
                    continue
                value = material.get_scalar_parameter_value('StaffLightAmount') if isinstance(material, u.MaterialInstanceDynamic) else None
                item['materials'].append({'path': material.get_path_name(), 'light_amount': value})
            entry['staff'].append(item)
        report['players'].append(entry)
head = u.load_asset('/Game/Weapons/ApprenticeStaff20260927/Meshes/SM_Staff_head_crystal_false')
for slot in head.get_editor_property('static_materials'):
    material = slot.material_interface
    report['head_materials'].append({'path': material.get_path_name(),
        'scalars': [str(p) for p in u.MaterialEditingLibrary.get_scalar_parameter_names(material)]})
(ROOT / 'before-state.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('STAFF_LIGHT_STATE ' + json.dumps(report))
