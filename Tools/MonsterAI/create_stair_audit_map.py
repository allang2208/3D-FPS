"""Create the owned navigation fixture in editor time; never save a user's open map."""
import json
from pathlib import Path
import unreal

level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
path = '/Game/Tests/MonsterStairs/L_MonsterStairs'
if unreal.EditorAssetLibrary.does_asset_exist(path):
    assert level.load_level(path)
else:
    assert level.new_level_from_template(path, '/Game/GameMaps/DayNight_Lighting')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert unreal.MonsterAIController.build_navigation_bounds(
    world, unreal.Vector(50600, 0, 10100), unreal.Vector(1700, 700, 500))
volume = next(a for a in actors.get_all_level_actors()
              if isinstance(a, unreal.NavMeshBoundsVolume) and a.get_actor_label() == 'MonsterNavigation')
center, extent = volume.get_actor_bounds(False)
assert extent.x > 1000 and extent.y > 400, str(extent)
assert level.save_current_level()
report = {'map': path, 'bounds_center': str(center), 'bounds_extent': str(extent), 'blueprints': []}
for asset in ['/Game/Monsters/NurseZombie/BP_NurseZombie', '/Game/Monsters/HandBrain/BP_HandBrain',
              '/Game/Monsters/PoisonMaggot/BP_PoisonMaggot']:
    bp = unreal.load_asset(asset)
    cdo = unreal.get_default_object(bp.generated_class())
    move = cdo.get_component_by_class(unreal.CharacterMovementComponent)
    report['blueprints'].append({'asset': asset, 'movement': move.get_class().get_name(),
                                'step_height': move.get_editor_property('max_step_height')})
    assert isinstance(move, unreal.MonsterCharacterMovementComponent)
    assert move.get_editor_property('max_step_height') == 40
out = Path(unreal.Paths.project_saved_dir()) / 'MonsterStairs'
out.mkdir(exist_ok=True)
(out / 'fixture.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('MONSTER_STAIR_FIXTURE_SAVED')
