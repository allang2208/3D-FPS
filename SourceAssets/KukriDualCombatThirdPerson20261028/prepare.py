"""Read the active full-body support takes for dual combat authoring."""
import json
from pathlib import Path
import unreal as u

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
native=json.loads((ROOT/'SourceAssets/KukriWhirlwindSourceMotion20261025/active-inputs.json').read_text())
roles=('Slash1','Slash2','Thrust','Charge','Heavy','Recover1','Recover2')

def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]

result={}
for label in ('jason','kaitlin'):
    active=cfg if label=='jason' else cfg['body_variants'][label]
    data=native[label];mesh=u.load_asset(active['body_mesh'])
    if active['body_mesh']!=data['mesh']:raise RuntimeError('Native body changed')
    opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.SOURCE
    entry=dict(native=data,clips={},previous_roles={r:active['clips'].get('Kukri.FullBody.Dual.'+r) for r in roles})
    for role in ('Dual.Idle',)+roles[:5]:
        clip=u.load_asset(active['clips']['Kukri.FullBody.'+role]);duration=clip.get_play_length();rate=60
        count=round(duration*rate);frames=[]
        for k in range(count+1):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,duration*k/count,opts)
            frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in data['names']])
        entry['clips'][role]=dict(asset=clip.get_path_name(),duration=duration,rate=count/duration,frames=frames,
            markers={str(m.marker_name):m.time for m in u.AnimationLibrary.get_animation_sync_markers(clip)})
        print('DUAL_COMBAT_SOURCE',label,role,duration,flush=True)
    result[label]=entry
(OUT/'inputs.json').write_text(json.dumps(result,separators=(',',':')))
print('DUAL_COMBAT_INPUTS_SAVED',flush=True)
