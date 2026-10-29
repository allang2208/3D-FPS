"""Export the current single carry as input; no assets or worlds are modified."""
import json
from pathlib import Path
import unreal as u

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
rig=json.loads((ROOT/'SourceAssets/KukriWhirlwindSourceMotion20261025/active-inputs.json').read_text())

def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]

result={}
for label in ('jason','kaitlin'):
    active=cfg if label=='jason' else cfg['body_variants'][label]
    data=rig[label];mesh=u.load_asset(active['body_mesh'])
    if active['body_mesh']!=data['mesh']:raise RuntimeError('Native body changed')
    asset=active['clips']['Kukri.FullBody.Idle'];clip=u.load_asset(asset)
    length=clip.get_play_length();rate=120;n=round(length*rate)
    opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.SOURCE
    frames=[]
    for k in range(n+1):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,length*k/n,opts)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.LOCAL)) for b in data['names']])
    roles=['Dual.Idle']+['Dual.Whirlwind.'+stage for stage in ('Start','Loop','End')]
    result[label]=dict(mesh=active['body_mesh'],asset=asset,rate=rate,duration=length,frames=frames,
        previous_roles={r:active['clips'].get('Kukri.FullBody.'+r) for r in roles})
    print('DUAL_IDLE_INPUT_EXPORTED',label,asset,len(frames),flush=True)
(OUT/'inputs.json').write_text(json.dumps(result,separators=(',',':')))
