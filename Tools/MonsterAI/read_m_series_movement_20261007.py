"""Read saved M-series class defaults only; do not compile or save assets."""
from pathlib import Path
from datetime import datetime
import json
import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/Saved/MSeriesMovementAudit20261007')
OUT.mkdir(parents=True, exist_ok=True)
specs = {
    'M07': ('/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07.BP_BlindSupplicantM07_C',
            ['walk_speed', 'chase_speed', 'source_walk_speed', 'source_chase_speed'],
            ['slow_walk_clip', 'chase_clip']),
    'M08': ('/Game/Monsters/LurkerM08/BP_LurkerM08.BP_LurkerM08_C',
            ['walk_speed', 'chase_speed', 'climb_speed', 'surface_turn_speed'], []),
    'M09': ('/Script/FPSGAME.HangingBellM09', ['ceiling_speed'], []),
    'M10': ('/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler.BP_M10Mawcrawler_C',
            ['walk_speed', 'animation_walk_speed', 'moving_turn_speed', 'pivot_turn_speed', 'turn_acceleration'],
            ['move_clip', 'curve_left_clip', 'curve_right_clip', 'pivot_left_clip', 'pivot_right_clip']),
    'M14': ('/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14.BP_SpiralPillarM14_C',
            ['walk_speed', 'animation_walk_speed'], ['move_clip', 'turn_left_clip', 'turn_right_clip']),
    'M25': ('/Game/Monsters/VortexCofferM25/BP_VortexCofferM25.BP_VortexCofferM25_C',
            ['walk_speed', 'animation_walk_speed'], ['move_clip']),
    'M27': ('/Game/Monsters/MantisM27/BP_MantisM27.BP_MantisM27_C',
            ['walk_speed', 'source_move_speed', 'cloak_move_speed'], ['walk_clip']),
}
def clip_info(clip):
    return dict(path=clip.get_path_name(), seconds=clip.get_play_length(),
                rate_scale=clip.get_editor_property('rate_scale')) if clip else None

report = dict(captured_at=datetime.now().isoformat(), kind='saved_class_defaults',
              assets_saved=False, game_started=False, monsters={}, errors={})
for key, (path, properties, clips) in specs.items():
    try:
        cls = u.load_class(None, path)
        cdo = u.get_default_object(cls)
        move = cdo.get_editor_property('character_movement')
        row = dict(class_path=path, properties={p: cdo.get_editor_property(p) for p in properties},
                   movement={p: move.get_editor_property(p) for p in
                             ['max_walk_speed', 'max_fly_speed', 'max_acceleration',
                              'braking_deceleration_walking', 'orient_rotation_to_movement']},
                   movement_class=move.get_class().get_name(),
                   clips={p: clip_info(cdo.get_editor_property(p)) for p in clips})
        row['movement']['rotation_rate_yaw'] = move.get_editor_property('rotation_rate').yaw
        if key == 'M08':
            dataset = cdo.get_editor_property('animation_set')
            row['animation_set'] = dict(path=dataset.get_path_name(),
                walk_speed=dataset.get_editor_property('walk_speed'),
                run_speed=dataset.get_editor_property('run_speed'))
        if key == 'M09':
            row['clips'] = {str(name): clip_info(clip) for name, clip in cdo.get_editor_property('clips').items()}
        report['monsters'][key] = row
    except Exception as exc:
        report['errors'][key] = str(exc)
(OUT / 'saved_defaults.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print('M_SERIES_MOVEMENT_READ_ONLY_COMPLETE ' + str(len(report['monsters'])))
if report['errors']:
    raise RuntimeError(str(report['errors']))
