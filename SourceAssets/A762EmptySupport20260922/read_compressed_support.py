import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent
meta=json.loads((O/'authoring.json').read_text())
source=u.AnimPoseEvaluationOptions();source.set_editor_property('evaluation_type',u.AnimDataEvalType.SOURCE)
compressed=u.AnimPoseEvaluationOptions();compressed.set_editor_property('evaluation_type',u.AnimDataEvalType.COMPRESSED)
rows={};peak=0.
for key,info in meta.items():
    a=u.load_asset(info['asset']);worst=0.
    for frame in (254,272,280,310,320,330,345,365,385,400,440):
        time=(frame-info['frames'][0])/120
        raw=u.AnimPoseExtensions.get_anim_pose_at_time(a,time,source)
        packed=u.AnimPoseExtensions.get_anim_pose_at_time(a,time,compressed)
        for bone in info['changed_bones']:
            lhs=u.AnimPoseExtensions.get_bone_pose(raw,bone,u.AnimPoseSpaces.LOCAL).rotation
            rhs=u.AnimPoseExtensions.get_bone_pose(packed,bone,u.AnimPoseSpaces.LOCAL).rotation
            av=[getattr(lhs,c) for c in ('x','y','z','w')];bv=[getattr(rhs,c) for c in ('x','y','z','w')]
            dot=abs(sum(x*y for x,y in zip(av,bv)))/math.sqrt(sum(x*x for x in av)*sum(x*x for x in bv))
            error=math.degrees(2*math.acos(min(1.,max(0.,dot))));worst=max(worst,error)
    rows[key]={'seconds':a.get_play_length(),'source_compressed_max_rotation_degrees':worst}
    peak=max(peak,worst)
(O/'compressed_support_diagnosis.json').write_text(json.dumps({'clips':rows,'maximum_degrees':peak,'PIE_tested':False},indent=2),encoding='utf-8')
print('A762_SUPPORT_COMPRESSED_READBACK',len(rows),'MAX_DEGREES',peak,'NO_PIE')
