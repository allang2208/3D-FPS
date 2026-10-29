"""Read only the currently installed single dash and interactive save state."""
import json
from pathlib import Path
import unreal as u
OUT = Path(__file__).resolve().parent
cfg = json.loads((OUT.parents[1] / 'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
report = dict(bodies={})
report['pie_active'] = False
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    level = u.get_editor_subsystem(u.LevelEditorSubsystem)
    report['pie_active'] = bool(level and level.is_in_play_in_editor())
names = ['clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l']
for label, section in [('jason', cfg), ('kaitlin', cfg['body_variants']['kaitlin'])]:
    mesh = u.load_asset(section['body_mesh'])
    clip = u.load_asset(section['clips']['Kukri.FullBody.Dash'])
    options = u.AnimPoseEvaluationOptions()
    options.optional_skeletal_mesh = mesh
    options.evaluation_type = u.AnimDataEvalType.SOURCE
    frames = {}
    for t in [.2, .4, .55, .7, .9]:
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, t, options)
        row = {}
        for name in names:
            x = u.AnimPoseExtensions.get_bone_pose(pose, name, u.AnimPoseSpaces.LOCAL)
            row[name] = [x.rotation.x, x.rotation.y, x.rotation.z, x.rotation.w]
        frames[str(t)] = row
    report['bodies'][label] = dict(asset=clip.get_path_name(), duration=clip.get_play_length(), frames=frames)
(OUT / 'installed-before.json').write_text(json.dumps(report, indent=2))
print('SINGLE_DASH_READ', json.dumps(dict(pie_active=report['pie_active'], assets=[v['asset'] for v in report['bodies'].values()])))
