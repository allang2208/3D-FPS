"""Read saved source/compressed poses for arm-opening diagnosis, without saves."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
OUT=ROOT/'Saved/MeleeArmOpeningReview20260923';OUT.mkdir(parents=True,exist_ok=True)
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return {'p':[p.x,p.y,p.z],'q':[q.w,q.x,q.y,q.z],'s':[s.x,s.y,s.z]}
result={}
for variant in ('Standard','LongGrip'):
    source=json.loads((ROOT/'SourceAssets/MeleeArmOpening20260923'/variant/'source.json').read_text())
    mesh=u.load_asset(source['mesh'])
    result[variant]={}
    for clip in ('Thrust','Overhead','SprintOverhead'):
        asset=u.load_asset(source['clips'][clip]['asset'])
        result[variant][clip]={}
        for label,evaluation in [('SOURCE',u.AnimDataEvalType.SOURCE),('COMPRESSED',u.AnimDataEvalType.COMPRESSED)]:
            options=u.AnimPoseEvaluationOptions();options.evaluation_type=evaluation;options.optional_skeletal_mesh=mesh
            rows=[]
            for t in ([.54,.58,.60,.625,.65,.70] if clip=='Thrust' else [.97,1.02,1.07,1.125,1.16,1.19,1.22,1.31,1.4]):
                pose=u.AnimPoseExtensions.get_anim_pose_at_time(asset,t,options)
                rows.append({'seconds':t,'world':{n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in source['parents']}})
            result[variant][clip][label]=rows
(OUT/'evaluated-poses.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
print('ARM_OPENING_EVALUATED_POSES_SAVED')
