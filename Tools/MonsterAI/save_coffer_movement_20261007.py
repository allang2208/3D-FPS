"""Save doubled M10/M25 locomotion tuning after the native animation build."""
from pathlib import Path
import json
import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/CofferMovement20261007/Records')
OUT.mkdir(parents=True, exist_ok=True)
report = dict(complete=False, saved=[], settings={}, tested=False, rendered=False,
              user_testing_pending=True)

def receipt():
    (OUT / 'ue_revision.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')

receipt()
for species, path in (
    ('M10', '/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler'),
    ('M25', '/Game/Monsters/VortexCofferM25/BP_VortexCofferM25'),
):
    bp = u.load_asset(path)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = u.get_default_object(bp.generated_class())
    move = cdo.get_editor_property('character_movement')
    values = dict(walk_speed=110.)
    if species == 'M10':
        values.update(moving_turn_speed=72., pivot_turn_speed=60., turn_acceleration=195.)
    before = {key: cdo.get_editor_property(key) for key in values}
    for key, value in values.items():
        cdo.set_editor_property(key, value)
    motion = dict(max_walk_speed=110., max_acceleration=480., braking_deceleration_walking=720.)
    old_motion = {key: move.get_editor_property(key) for key in motion}
    old_motion['rotation_rate_yaw'] = move.get_editor_property('rotation_rate').yaw
    for key, value in motion.items():
        move.set_editor_property(key, value)
    move.set_editor_property('rotation_rate', u.Rotator(pitch=0., yaw=150., roll=0.))
    source_speed = cdo.get_editor_property('animation_walk_speed')
    u.EditorAssetLibrary.set_metadata_tag(bp, species + '.MovementRevision', 'CofferMovement20261007')
    if not u.EditorAssetLibrary.save_loaded_asset(bp, False):
        raise RuntimeError('Could not save ' + path)
    report['saved'].append(bp.get_path_name())
    report['settings'][species] = dict(before=before, actor=values, old_movement=old_motion,
        movement=motion, rotation_rate_yaw=150., unchanged_animation_source_speed=source_speed,
        full_speed_animation_rate=110. / source_speed)
    receipt()
report['complete'] = True
receipt()
print('M10_M25_DOUBLED_MOVEMENT_SAVED')
