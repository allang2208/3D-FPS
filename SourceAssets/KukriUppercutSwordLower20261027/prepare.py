"""Read the currently connected two-handed sword uppercuts for production."""
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
native = json.loads((ROOT/'SourceAssets/KukriWhirlwindSourceMotion20261025/active-inputs.json').read_text())
result = {}
for label in ('jason', 'kaitlin'):
    active = cfg if label == 'jason' else cfg['body_variants'][label]
    data = native[label]
    mesh = u.load_asset(active['body_mesh'])
    clip = u.load_asset(active['clips']['Melee.FullBody.Uppercut'])
    options = u.AnimPoseEvaluationOptions()
    options.optional_skeletal_mesh = mesh
    options.evaluation_type = u.AnimDataEvalType.SOURCE
    duration = clip.get_play_length()
    count = round(duration*120)+1
    frames = []
    for frame in range(count):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, duration*frame/(count-1), options)
        row = []
        for name in data['names']:
            t = u.AnimPoseExtensions.get_bone_pose(pose, name, u.AnimPoseSpaces.LOCAL)
            row.append([t.translation.x,t.translation.y,t.translation.z,
                        t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,
                        t.scale3d.x,t.scale3d.y,t.scale3d.z])
        frames.append(row)
    markers = {str(m.marker_name):m.time for m in u.AnimationLibrary.get_animation_sync_markers(clip)}
    result[label] = dict(mesh=mesh.get_path_name(), asset=clip.get_path_name(), names=data['names'],
                         parents=data['parents'], duration=duration, rate=(count-1)/duration,
                         markers=markers, frames=frames,
                         previous_roles={r:active['clips']['Kukri.FullBody.'+r] for r in ('Uppercut','Dual.Uppercut')})
    print('SWORD_LOWER_SOURCE',label,clip.get_path_name(),duration,markers,flush=True)
(OUT/'sword-lower-inputs.json').write_text(json.dumps(result,separators=(',',':')))
print('SWORD_LOWER_INPUTS_SAVED',flush=True)
