"""Read current cut routes and compression error without changing the world."""
import json,math
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'));result={}
version=globals().get('READ_VERSION','before')
for label in ('jason','kaitlin'):
    active=cfg if label=='jason' else cfg['body_variants'][label];mesh=u.load_asset(active['body_mesh'])
    source=json.loads(((OUT if version=='after' else ROOT/'SourceAssets/KukriDualCombatThirdPerson20261028')/(label+'-actions.json')).read_text())
    opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
    result[label]={}
    names=[k+'_'+side for side in 'lr' for k in ('clavicle','upperarm','lowerarm','hand','upperarm_twist_01','upperarm_twist_02','lowerarm_twist_01','lowerarm_twist_02')]
    for role in ('Dual.Slash1','Dual.Slash2'):
        path=active['clips']['Kukri.FullBody.'+role];clip=u.load_asset(path);data=source['clips'][role];pe=qe=0.
        for k in range(0,len(data['frames']),3):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,k/120,opts)
            for name in names:
                t=u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.LOCAL);ref=data['frames'][k][source['names'].index(name)]
                pe=max(pe,math.sqrt(sum((v-w)**2 for v,w in zip((t.translation.x,t.translation.y,t.translation.z),ref[:3]))))
                dot=sum(v*w for v,w in zip((t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w),ref[3:7]))
                qe=max(qe,math.degrees(2*math.acos(min(1.,abs(dot)))))
        result[label][role]=dict(asset=path,max_local_position_error_cm=pe,max_local_rotation_error_deg=qe)
(OUT/(version+'-saved-read.json')).write_text(json.dumps(result,indent=2));print(json.dumps(result))
