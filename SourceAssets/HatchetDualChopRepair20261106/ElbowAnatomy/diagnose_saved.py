import json,math
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
d=json.loads((P/'Kaitlin-moves.json').read_text());s=json.loads((P/'saved-assets.json').read_text())['Kaitlin']['DualRelease'];f=d['clips']['DualRelease']
clip=u.load_asset(s['asset']);opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=u.load_asset(d['mesh']);opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
A=u.AnimPoseExtensions;errors=[]
for i in range(193):
    t=i/120;pose=A.get_anim_pose_at_time(clip,t,opt);a=i//2;b=min(a+1,len(f)-1);alpha=(i%2)*.5
    for n in s['changed_tracks']+[k+'_'+side for side in ('r','l') for k in ('upperarm','lowerarm','hand')]:
        k=d['names'].index(n);v=A.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL).translation;got=[v.x,v.y,v.z]
        expected=[f[a][k][j]*(1-alpha)+f[b][k][j]*alpha for j in range(3)];error=math.dist(got,expected)
        if error>.05:
            opt.evaluation_type=u.AnimDataEvalType.SOURCE;raw=A.get_anim_pose_at_time(clip,t,opt);r=A.get_bone_pose(raw,n,u.AnimPoseSpaces.LOCAL).translation;opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
            errors.append(dict(time=t,bone=n,error=error,compressed=got,source=[r.x,r.y,r.z],expected=expected))
(P/'compression-diagnosis.json').write_text(json.dumps(errors,indent=2),'utf8')
u.log('ELBOW_COMPRESSION_DIAG '+str(len(errors)))
