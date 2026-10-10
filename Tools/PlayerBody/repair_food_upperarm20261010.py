"""Reproduce the reported small food motion, save the fix, and read it back.

Explicitly requested food diagnosis only: sampled source/compressed animation,
no game world, rendering, or changes to the accepted drinking animation.
"""
import hashlib
import json
import math
import runpy
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonFoodUpperarmFix20261010'
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
authored = json.loads((ROOT/'SourceAssets/ThirdPersonFoodNative20261010/authored.json').read_text())
mesh = u.load_asset(cfg['body_mesh'])
bones = ['upperarm_l', 'lowerarm_l', 'hand_l', 'head']
drink_file = ROOT/'Content'/Path(cfg['clips']['Consume.Drink'].split('.')[0].removeprefix('/Game/')+'.uasset')
drink_before = hashlib.sha256(drink_file.read_bytes()).hexdigest()

def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]

def rotate(q, p):
    a = cross(q[:3], p)
    b = cross(q[:3], a)
    return [p[i]+2.*(q[3]*a[i]+b[i]) for i in range(3)]

def transform(t, p):
    return [a+b for a, b in zip(t[:3], rotate(t[3:7], [p[i]*t[7+i] for i in range(3)]))]

def pack(t):
    return [*t.translation.to_tuple(), t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w, *t.scale3d.to_tuple()]

def angle(a, b):
    dot = abs(sum(x*y for x, y in zip(a, b)))
    return math.degrees(2.*math.acos(min(1., max(-1., dot))))

def read_saved(stage):
    result = {}
    for key, definition in authored['clips'].items():
        clip = u.load_asset(cfg['clips'][key])
        times = definition['times']
        duration = clip.get_play_length()
        samples = sorted(set([i/30. for i in range(round(duration*30)+1)]+[times['grab'], times['contact'], times['release']]))
        held = definition['food_grip_mount']+[1., 1., 1.]
        tip = transform(held, definition['contact_point'])
        record = dict(asset=clip.get_path_name(), duration=duration, poses={})
        for label, mode in [('source', u.AnimDataEvalType.SOURCE), ('compressed', u.AnimDataEvalType.COMPRESSED)]:
            options = u.AnimPoseEvaluationOptions()
            options.optional_skeletal_mesh = mesh
            options.evaluation_type = mode
            rows = []
            for seconds in samples:
                pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, min(seconds, duration), options)
                transforms = {bone:pack(u.AnimPoseExtensions.get_bone_pose(pose, bone, u.AnimPoseSpaces.WORLD)) for bone in bones}
                transforms['time'] = seconds
                transforms['food_contact'] = transform(transforms['hand_l'], tip)
                transforms['mouth'] = transform(transforms['head'], cfg['consume_mouth_in_head'])
                rows.append(transforms)
            record['poses'][label] = rows
        rows = record['poses']['compressed']
        grab = min(rows, key=lambda r:abs(r['time']-times['grab']))
        bite = min(rows, key=lambda r:abs(r['time']-times['contact']))
        record['metrics'] = dict(
            wrist_grab_to_bite_cm=math.dist(grab['hand_l'][:3], bite['hand_l'][:3]),
            wrist_height_range_cm=max(r['hand_l'][2] for r in rows)-min(r['hand_l'][2] for r in rows),
            upper_motion_from_grab_degrees=max(angle(grab['upperarm_l'][3:7], r['upperarm_l'][3:7]) for r in rows),
            bite_to_mouth_cm=math.dist(bite['food_contact'], bite['mouth']),
            max_source_compressed_position_difference_cm=max(math.dist(a[b][:3], c[b][:3])
                for a, c in zip(record['poses']['source'], rows) for b in bones))
        result[key] = record
    (OUT/(stage+'.json')).write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result

editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('FOOD_UPPERARM_REPAIR_REQUIRES_END_PLAY')
before = read_saved('before-saved-poses')
runpy.run_path(str(ROOT/'Tools/PlayerBody/save_food_native20261010.py'), run_name='__main__')
after = read_saved('after-saved-poses')
drink_after = hashlib.sha256(drink_file.read_bytes()).hexdigest()
checks = {'drink_unchanged':drink_before == drink_after}
for key, row in after.items():
    metrics = row['metrics']
    checks[key+'.visible_lift'] = metrics['wrist_grab_to_bite_cm'] > 15.
    checks[key+'.upperarm_moves'] = metrics['upper_motion_from_grab_degrees'] > 20.
    checks[key+'.source_matches_compressed'] = metrics['max_source_compressed_position_difference_cm'] < .1
    checks[key+'.authored_contact'] = metrics['bite_to_mouth_cm'] < 1.
report = dict(scope='Source and compressed food animation only; not a gameplay or rendered test.',
              before={k:v['metrics'] for k, v in before.items()}, after={k:v['metrics'] for k, v in after.items()},
              checks=checks, passed=all(checks.values()), drink_hash=drink_after,
              gameplay_tested=False, rendered=False)
(OUT/'diagnosis.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('FOOD_UPPERARM_DIAGNOSIS', json.dumps(report))
if not report['passed']:
    raise RuntimeError('Food saved-pose diagnosis requires follow-up; see diagnosis.json')
