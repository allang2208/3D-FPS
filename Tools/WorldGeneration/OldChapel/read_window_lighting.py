"""Read the existing editor/game chapel and the saved window materials, without changing them."""
import json
from pathlib import Path
import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/Saved/ChapelWindow20261115')
OUT.mkdir(parents=True, exist_ok=True)
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
report = {'worlds': [], 'materials': [], 'meshes': []}
for world in [editor.get_editor_world(), editor.get_game_world()]:
    if not world:
        continue
    item = {'world': world.get_path_name(), 'chapels': [], 'vision_rooms': []}
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.TemperateHillsWorld):
        chapel = {'actor': actor.get_path_name(), 'lights': [], 'parts': []}
        for comp in actor.get_components_by_class(u.RectLightComponent):
            chapel['lights'].append({key: str(comp.get_editor_property(key)) for key in
                ['intensity', 'source_width', 'source_height', 'attenuation_radius', 'specular_scale',
                 'affect_translucent_lighting', 'cast_shadows', 'light_color']}
                | {'name': comp.get_name(), 'location': str(comp.get_world_location()),
                   'direction': str(comp.get_forward_vector())})
        for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            if any(word in comp.get_name() for word in ['Lancet', 'WindowBay', 'Oculus']):
                chapel['parts'].append({'name': comp.get_name(), 'mesh': str(comp.static_mesh),
                    'materials': [str(comp.get_material(i)) for i in range(comp.get_num_materials())],
                    'instances': [str(comp.get_instance_transform(i, True)) for i in range(comp.get_instance_count())]})
        item['chapels'].append(chapel)
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.BuildingDaylight):
        item['vision_rooms'].append({'name': actor.get_name(), 'location': str(actor.get_actor_location()),
            **{key: str(actor.get_editor_property(key)) for key in ['room_minimum','room_maximum',
                'additional_dark_adaptation_stops','exposure_compensation','shadow_contrast','highlight_contrast']}})
    report['worlds'].append(item)
base = '/Game/WorldGeneration/TemperateHills/OldChapel/'
for name in ['M_ChapelGlass', 'MI_ChapelLancet', 'M_ChapelLancetFinish']:
    material = u.load_asset(base + 'Materials/' + name)
    row = {'name': name, 'path': material.get_path_name() if material else None}
    if isinstance(material, u.MaterialInstanceConstant):
        row['parent'] = str(material.parent)
        row['texture_parameters'] = str(material.get_editor_property('texture_parameter_values'))
    elif isinstance(material, u.Material):
        row['blend_mode'] = str(material.blend_mode)
        for prop in [u.MaterialProperty.MP_BASE_COLOR, u.MaterialProperty.MP_EMISSIVE_COLOR,
                     u.MaterialProperty.MP_ROUGHNESS, u.MaterialProperty.MP_OPACITY]:
            row[str(prop)] = str(u.MaterialEditingLibrary.get_material_property_input_node(material, prop))
    report['materials'].append(row)
for name in ['SM_ChapelLancet', 'SM_ChapelLancetGlass', 'SM_ChapelWindowBay']:
    mesh = u.load_asset(base + 'Meshes/' + name)
    report['meshes'].append({'name':name, 'slots':str(mesh.get_editor_property('static_materials'))})
report['dirty_maps'] = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
(OUT/'window-state.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('CHAPEL_WINDOW_STATE ' + str(OUT/'window-state.json'))
