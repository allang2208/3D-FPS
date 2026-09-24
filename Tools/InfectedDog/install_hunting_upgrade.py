"""Save the opt-in canine hunting profile after the normal Editor build.

Run in a background Python commandlet when the editor is closed, or through
the mutex bridge in an editor already using the rebuilt native module.
Does not run the game, render previews, or alter animation / mesh assets.
"""
import json
import shutil
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/InfectedDogHunting20260925'
BP_PATH = '/Game/Monsters/InfectedDog/BP_InfectedDog'
SET_PATH = '/Game/Monsters/InfectedDog/MeshyV2/DA_InfectedDogMeshy_AnimationSet'
RUN_PATH = '/Game/Monsters/InfectedDog/MeshyV2/GodotRunNaturalV3/A_InfectedDogMeshy_GodotRunNaturalV3'
SETTINGS = {
    'use_predictive_hunting': True,
    'pounce_lead_strength': 1.0,
    'pounce_max_lead_distance': 260.0,
    'pounce_stand_off': 85.0,
    'bite_contact_slack': 20.0,
    'bite_contact_angle': 130.0,
    'pounce_contact_reach': 190.0,
    'pounce_contact_angle': 130.0,
    'hunting_height_tolerance': 90.0,
    'attack_tracking_yaw_rate': 540.0,
}

if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Wrong project')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world() is not None:
    raise RuntimeError('End PIE before saving infected dog defaults')
bp = u.load_asset(BP_PATH)
if not bp:
    raise RuntimeError('Missing infected dog blueprint')
cdo = u.get_default_object(bp.generated_class())
if not isinstance(cdo, u.InfectedDogMonster):
    raise RuntimeError('Infected dog parent class changed')
dataset = cdo.get_editor_property('animation_set')
if not dataset or dataset.get_path_name().split('.')[0] != SET_PATH:
    raise RuntimeError('Active animation set changed; preserving current assets')
actions = dataset.get_editor_property('actions')
for role in ('Run', 'RunTurnLeft', 'RunTurnRight'):
    if actions[role].get_editor_property('sequence').get_path_name().split('.')[0] != RUN_PATH:
        raise RuntimeError('Accepted canine run binding changed: ' + role)
dirty = {p.get_name().casefold() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if BP_PATH.casefold() in dirty:
    raise RuntimeError('Preserving unsaved infected dog blueprint edits')

# Resolve every new field before touching the asset. An old loaded DLL will
# fail here without leaving a partially modified blueprint.
before = {key: cdo.get_editor_property(key) for key in SETTINGS}
ROOT.mkdir(parents=True, exist_ok=True)
snapshot = ROOT / 'before.json'
if not snapshot.exists():
    preserved = {key: cdo.get_editor_property(key) for key in (
        'bite_trigger_range', 'bite_cooldown', 'bite_windup', 'bite_recovery',
        'pounce_min_range', 'pounce_max_range', 'pounce_cooldown', 'pounce_windup',
        'pounce_recovery', 'pounce_travel_start', 'pounce_travel_end', 'pounce_arc_height',
        'chase_speed', 'aggro_radius', 'leash_radius')}
    snapshot.write_text(json.dumps({'settings': before, 'preserved': preserved,
        'animation_set': dataset.get_path_name(), 'run': RUN_PATH}, indent=2), encoding='utf-8')
    shutil.copy2(PROJECT / 'Content/Monsters/InfectedDog/BP_InfectedDog.uasset',
        ROOT / 'BP_InfectedDog.before.uasset')
cdo.modify()
for key, value in SETTINGS.items():
    cdo.set_editor_property(key, value)
u.EditorAssetLibrary.set_metadata_tag(bp, 'InfectedDog.HuntingRevision', 'CanineHuntingV1-20260925')
if not u.EditorAssetLibrary.save_loaded_asset(bp, False):
    raise RuntimeError('Could not save infected dog blueprint')
report = {'state': 'hunting_profile_saved', 'saved': [bp.get_path_name()],
    'settings': SETTINGS, 'animation_assets_changed': False, 'runtime_tested': False,
    'preview_rendered': False, 'accepted_run': RUN_PATH}
(ROOT / 'installation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('INFECTED_DOG_HUNTING_SAVED ' + json.dumps(report))
