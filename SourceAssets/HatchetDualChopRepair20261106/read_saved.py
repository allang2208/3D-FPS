"""Optional readback of the six retained third-person animations."""
import json,math
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
saved=json.loads((P/'saved-assets.json').read_text());A=u.AnimPoseExtensions
report=[]
for label in ('Jason','Kaitlin'):
    data=json.loads((P/(label+'-moves.json')).read_text());mesh=u.load_asset(data['mesh'])
    options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh;options.evaluation_type=u.AnimDataEvalType.SOURCE
    bones=[k+'_'+s for s in ('r','l') for k in ('upperarm','upperarm_twist_01','upperarm_twist_02','lowerarm','lowerarm_twist_01','lowerarm_twist_02','hand')]
    for role,frames in data['clips'].items():
        clip=u.load_asset(saved[label][role]['asset'])
        maximum_pos=maximum_angle=0.;samples=sorted({0,11,14,20,36,min(49,len(frames)-1),len(frames)-1})
        for frame in samples:
            pose=A.get_anim_pose_at_time(clip,frame/60,options)
            for bone in bones:
                t=A.get_bone_pose(pose,bone,u.AnimPoseSpaces.LOCAL);expected=frames[frame][data['names'].index(bone)]
                maximum_pos=max(maximum_pos,math.dist([t.translation.x,t.translation.y,t.translation.z],expected[:3]))
                q=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w];e=expected[3:7]
                dot=abs(sum(a*b for a,b in zip(q,e)))/(math.sqrt(sum(a*a for a in q))*math.sqrt(sum(a*a for a in e)))
                maximum_angle=max(maximum_angle,math.degrees(2*math.acos(min(1.,dot))))
        passed=maximum_pos<.01 and maximum_angle<.1 and abs(clip.get_play_length()-(len(frames)-1)/60)<.0001
        report.append(dict(rig=label,role=role,passed=passed,max_local_position_error=maximum_pos,max_rotation_error_deg=maximum_angle,asset=clip.get_path_name()))
(P/'saved-readback.json').write_text(json.dumps(report,indent=2),'utf8')
if not all(row['passed'] for row in report):raise RuntimeError('Saved arm poses differ from authored tracks')
u.log('HATCHET_DUAL_READBACK_PASSED assets='+str(len(report)))
