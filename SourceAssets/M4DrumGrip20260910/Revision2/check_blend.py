import unreal,json,math
from pathlib import Path
O=Path(__file__).parent;L=unreal.AnimPoseExtensions
opt=unreal.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416');opt.evaluation_type=unreal.AnimDataEvalType.RAW
poses=[L.get_anim_pose_at_time(unreal.load_asset(p),0,opt) for p in ['/Game/Weapons/M4ContactImpactFinal/A_AKM_idle','/Game/Weapons/M4DrumGripCandidate/A_M4_DrumGrip_reload']]
names=L.get_bone_names(poses[0]);rows=[]
for n in names:
 a,b=[L.get_bone_pose(p,n,unreal.AnimPoseSpaces.LOCAL) for p in poses]
 q=a.rotation;r=b.rotation;angle=math.degrees(2*math.acos(min(1,abs(q.x*r.x+q.y*r.y+q.z*r.z+q.w*r.w))))
 rows.append({'bone':str(n),'angle':angle,'distance':a.translation.distance(b.translation),'a':str(a),'b':str(b)})
(O/'blend_diagnosis.json').write_text(json.dumps(rows,indent=2));unreal.log('BLEND_DIAGNOSIS_DONE')
