"""Restore the temperate hills world to pristine terrain (editor Python).

Keeps the world identity (Seed / WorldId) and only clears the runtime terrain edits left
by testing (craters, shovel dig/refill records). It also reports whether the hills map
still contains any voxel-era actors, without saving the map.
"""
import json
from pathlib import Path

import unreal

PROJECT = Path('D:/FPS3D/FPSGAME')
SLOT = 'TemperateHills_World'
LEVEL = '/Game/GameMaps/L_TemperateHills_Initial'

report = {'slot': SLOT, 'level': LEVEL}

save = unreal.GameplayStatics.load_game_from_slot(SLOT, 0)
if save is None:
    report['save_found'] = False
else:
    report['save_found'] = True
    report['version_before'] = save.get_editor_property('version')
    report['seed'] = save.get_editor_property('seed')
    report['world_id'] = str(save.get_editor_property('world_id'))
    report['edits_before'] = len(save.get_editor_property('edits'))
    report['legacy_craters_before'] = len(save.get_editor_property('craters'))
    save.set_editor_property('edits', [])
    save.set_editor_property('craters', [])
    save.set_editor_property('version', 3)
    report['saved'] = bool(unreal.GameplayStatics.save_game_to_slot(save, SLOT, 0))
    reloaded = unreal.GameplayStatics.load_game_from_slot(SLOT, 0)
    report['edits_after'] = len(reloaded.get_editor_property('edits')) if reloaded else -1
    report['seed_after'] = reloaded.get_editor_property('seed') if reloaded else None

# Map check only: list actors that reference a missing/unknown class (voxel-era leftovers).
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if unreal.EditorLoadingAndSavingUtils.load_map(LEVEL) is not None:
    stray = []
    for actor in actors.get_all_level_actors():
        name = actor.get_class().get_name() if actor.get_class() else 'None'
        label = actor.get_actor_label()
        if 'Voxel' in name or 'Voxel' in label or name == 'None':
            stray.append({'label': label, 'class': name})
    report['stray_voxel_actors'] = stray
    report['stray_count'] = len(stray)
else:
    report['map_loaded'] = False

report_path = PROJECT / 'Saved/SceneTests/hills-restore.json'
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('[HILLS_RESTORE] ' + json.dumps(report))
