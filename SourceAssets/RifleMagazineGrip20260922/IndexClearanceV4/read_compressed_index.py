"""Compare only imported index tracks with their compressed poses."""
import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent
meta=json.loads((O/'authoring.json').read_text())
source=u.AnimPoseEvaluationOptions();source.set_editor_property('evaluation_type',u.AnimDataEvalType.SOURCE)
compressed=u.AnimPoseEvaluationOptions();compressed.set_editor_property('evaluation_type',u.AnimDataEvalType.COMPRESSED)
result={};peak=0.
for key,info in meta.items():
    a=u.load_asset(info['asset']);worst=0.
    for frame in (36,40,42,44,46,148,238,240,242,244,248,252):
        time=(frame-info['frames'][0])/info['fps']
        raw=u.AnimPoseExtensions.get_anim_pose_at_time(a,time,source)
        packed=u.AnimPoseExtensions.get_anim_pose_at_time(a,time,compressed)
        for n in ('index_01_l','index_02_l','index_03_l'):
            qa=u.AnimPoseExtensions.get_bone_pose(raw,n,u.AnimPoseSpaces.LOCAL).rotation
            qb=u.AnimPoseExtensions.get_bone_pose(packed,n,u.AnimPoseSpaces.LOCAL).rotation
            av=[getattr(qa,c) for c in ('x','y','z','w')];bv=[getattr(qb,c) for c in ('x','y','z','w')]
            dot=abs(sum(x*y for x,y in zip(av,bv)))/math.sqrt(sum(x*x for x in av)*sum(x*x for x in bv))
            error=math.degrees(2*math.acos(min(1.,max(0.,dot))));worst=max(worst,error)
    result[key]={'max_source_compressed_index_angle_degrees':worst,'source_seconds':info['seconds'],'imported_seconds':a.get_play_length()}
    peak=max(peak,worst)
(O/'compressed_index_diagnosis.json').write_text(json.dumps({'clips':result,'maximum_degrees':peak,'PIE_tested':False},indent=2),encoding='utf-8')
print('INDEX_COMPRESSED_READBACK',len(result),'MAX_DEGREES',peak,'NO_PIE')
