import json
import unreal as u

result = {'meshes': {}, 'materials': {}, 'playing': False}
base = '/Game/Items/Consumables/MineralWater20261003'
for suffix in ('Shell', 'Cap', 'Liquid', 'Full', 'Half'):
    asset = u.load_asset(base + '/SM_MineralWater_' + suffix)
    if asset is None:
        result['meshes'][suffix] = None
        continue
    bounds = asset.get_bounds()
    result['meshes'][suffix] = {
        'origin': [bounds.origin.x, bounds.origin.y, bounds.origin.z],
        'extent': [bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z],
        'slots': [{'slot': str(s.material_slot_name),
                   'material': s.material_interface.get_path_name() if s.material_interface else None}
                  for s in asset.static_materials],
        'nanite': asset.get_editor_property('nanite_settings').enabled,
    }
for suffix in ('PET', 'Cap', 'Label', 'Liquid'):
    asset = u.load_asset(base + '/Materials/M_MineralWater_' + suffix)
    result['materials'][suffix] = {
        'blend_mode': str(asset.get_editor_property('blend_mode')),
        'shading_model': str(asset.get_editor_property('shading_model')),
        'expressions': u.MaterialEditingLibrary.get_num_material_expressions(asset),
    } if asset else None
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result['playing'] = world is not None
if world:
    characters = u.GameplayStatics.get_all_actors_of_class(world, u.FPSGAMECharacter)
    result['held_parts'] = []
    result['drink_components'] = []
    for character in characters:
        for component in character.get_components_by_class(u.FPSPotionUseComponent):
            result['drink_components'].append({
                'hands': [{'name': x.get_name(), 'visible': x.get_editor_property('visible'),
                           'hidden': x.get_editor_property('hidden_in_game'),
                           'hand_l_index': x.get_bone_index('hand_l'),
                           'skeletal_mesh': x.get_skeletal_mesh_asset().get_path_name()
                              if x.get_skeletal_mesh_asset() else None}
                          for x in character.get_components_by_class(u.FPSCastingMeshComponent)],
            })
        for part in character.get_components_by_class(u.StaticMeshComponent):
            if part.get_name().startswith('HeldPotion'):
                asset = part.get_editor_property('static_mesh')
                result['held_parts'].append({'name': part.get_name(),
                    'mesh': asset.get_path_name() if asset else None,
                    'visible': part.get_editor_property('visible'),
                    'hidden': part.get_editor_property('hidden_in_game'),
                    'location': str(part.get_world_location()),
                    'scale': str(part.get_world_scale())})
u.log('MINERAL_WATER_HAND_METADATA ' + json.dumps({k:v for k,v in result.items() if k not in ('meshes', 'materials')}))
