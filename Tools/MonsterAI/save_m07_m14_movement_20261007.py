"""Save the approved M07/M14 speeds after building their native gait changes."""
from pathlib import Path
import json
import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/M07M14Movement20261007/Records')
OUT.mkdir(parents=True, exist_ok=True)
report = dict(complete=False, saved=[], settings={}, tested=False, rendered=False,
              user_testing_pending=True)

def receipt():
    (OUT / 'ue_revision.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')

receipt()
for species, path, values, motion in (
    ('M07', '/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07',
     dict(walk_speed=82., chase_speed=168.), dict(max_walk_speed=168.)),
    ('M14', '/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14',
     dict(walk_speed=112.),
     dict(max_walk_speed=112., max_acceleration=200., braking_deceleration_walking=360.)),
):
    bp = u.load_asset(path)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = u.get_default_object(bp.generated_class())
    move = cdo.get_editor_property('character_movement')
    before = {key: cdo.get_editor_property(key) for key in values}
    old_motion = {key: move.get_editor_property(key) for key in motion}
    old_motion['rotation_rate_yaw'] = move.get_editor_property('rotation_rate').yaw
    for key, value in values.items():
        cdo.set_editor_property(key, value)
    for key, value in motion.items():
        move.set_editor_property(key, value)
    if species == 'M14':
        move.set_editor_property('rotation_rate', u.Rotator(pitch=0., yaw=75., roll=0.))
    source_keys = ['source_walk_speed', 'source_chase_speed'] if species == 'M07' else ['animation_walk_speed']
    sources = {key: cdo.get_editor_property(key) for key in source_keys}
    u.EditorAssetLibrary.set_metadata_tag(bp, species + '.MovementRevision', 'M07M14Movement20261007')
    if not u.EditorAssetLibrary.save_loaded_asset(bp, False):
        raise RuntimeError('Could not save ' + path)
    report['saved'].append(bp.get_path_name())
    report['settings'][species] = dict(before=before, actor=values, old_movement=old_motion,
        movement=motion, rotation_rate_yaw=move.get_editor_property('rotation_rate').yaw,
        unchanged_animation_sources=sources)
    receipt()
report['complete'] = True
receipt()
print('M07_M14_MOVEMENT_SAVED')
