"""Read existing Witch actors and asset settings; do not start or alter gameplay."""
import json
from pathlib import Path
import unreal as u

root = Path('D:/FPS3D/FPSGAME/SourceAssets/WitchLegRestore20261003/Receipts')
live = u.load_asset('/Game/Monsters/WitchRebuilt/SK_WitchRebuilt')
corpse = u.load_asset('/Game/Monsters/WitchRebuilt/CorpseFollow/SK_WitchRebuilt_CorpseFollow')
def asset_info(mesh):
    return {'mesh': mesh.get_path_name(),
            'physics': mesh.get_editor_property('physics_asset').get_path_name(),
            'clothing_assets': [{'name': c.get_name(), 'class': c.get_class().get_path_name()}
                               for c in mesh.get_editor_property('mesh_clothing_assets')],
            'source': str(mesh.get_editor_property('asset_import_data').get_first_filename())}
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
actors = (u.GameplayStatics.get_all_actors_of_class(world, u.WitchMonster) if world
          else u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
rows = []
for actor in actors:
    if not isinstance(actor, u.WitchMonster):
        continue
    mesh = actor.get_editor_property('mesh')
    knockdown = actor.get_component_by_class(u.HumanoidKnockdownComponent)
    instance = mesh.get_anim_instance()
    rows.append({'actor': actor.get_name(), 'class': actor.get_class().get_path_name(),
                 'state': str(actor.get_editor_property('state')),
                 'phase': str(knockdown.get_editor_property('phase')) if knockdown else None,
                 'mesh': mesh.get_editor_property('skeletal_mesh').get_path_name(),
                 'animation': instance.get_class().get_path_name() if instance else None,
                 'cloth_weight': mesh.get_editor_property('cloth_blend_weight'),
                 'cloth_suspended': mesh.is_clothing_simulation_suspended(),
                 'cloth_disabled': mesh.get_editor_property('disable_cloth_simulation'),
                 'forced_lod': mesh.get_forced_lod(),
                 'simulating': mesh.is_simulating_physics(),
                 'feet_world': {bone: list(mesh.get_socket_location(bone).to_tuple())
                                for bone in ('pelvis','thigh_l','calf_l','foot_l','foot_r')},
                 'walk_asset': actor.get_editor_property('walk_clip').get_path_name(),
                 'visual_asset': actor.get_editor_property('visual_mesh').get_path_name()})
    if len(rows) >= 8:
        break
report = {'live': asset_info(live), 'corpse': asset_info(corpse),
          'existing_game_world': bool(world), 'actors': rows, 'read_only': True}
(root / 'active-witch.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('WITCH_ACTIVE_READ ' + json.dumps(report))
