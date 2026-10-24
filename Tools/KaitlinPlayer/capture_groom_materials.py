"""Carry the selected native character's groom overrides into its runtime recipe."""
import json
from pathlib import Path
import unreal as u

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
components = json.loads((WORK / 'native_components.json').read_text())
subsystem = u.get_engine_subsystem(u.SubobjectDataSubsystem)
library = u.SubobjectDataBlueprintFunctionLibrary
grooms = {}
for path in set(row['blueprint'] for row in components if row['type'] == 'GroomComponent'):
    blueprint = u.load_asset(path)
    objects = [library.get_object_for_blueprint(library.get_data(handle), blueprint)
               for handle in subsystem.k2_gather_subobject_data_for_blueprint(blueprint)]
    mappings = {}
    for component in objects:
        if isinstance(component, u.LODSyncComponent):
            mappings.update({str(key): list(value.get_editor_property('mapping'))
                             for key, value in component.get_editor_property('custom_lod_mapping').items()})
    for component in objects:
        if not isinstance(component, u.GroomComponent):
            continue
        groom = component.get_editor_property('groom_asset')
        binding = component.get_editor_property('binding_asset')
        if not groom or not binding:
            continue
        materials = [component.get_material(index).get_path_name() for index in range(component.get_num_materials())
                     if component.get_material(index)]
        recipe = {'asset': groom.get_path_name(), 'binding': binding.get_path_name(), 'materials': materials}
        component_name = component.get_name().removesuffix('_GEN_VARIABLE')
        if component_name in mappings:
            recipe['lod_mapping'] = mappings[component_name]
        setup = component.get_editor_property('simulation_settings').get_editor_property('simulation_setup')
        recipe['simulation_setup'] = {key: setup.get_editor_property(key) for key in (
            'local_bone', 'local_simulation', 'linear_velocity_scale', 'angular_velocity_scale')}
        grooms[groom.get_path_name()] = recipe
(WORK / 'groom_recipes.json').write_text(json.dumps(list(grooms.values()), indent=2), encoding='utf-8')
(WORK / 'capture_groom_materials_status.json').write_text(json.dumps({'remaining': 0, 'complete': True}), encoding='utf-8')
print('KAITLIN_GROOM_RECIPES_SAVED', len(grooms), flush=True)
