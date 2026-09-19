"""Requested wrist check of imported RAW and COMPRESSED UE poses, no PIE."""
import json,math
from pathlib import Path
import unreal as u
P=Path(__file__).parent
def xyz(v):return (v.x,v.y,v.z)
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def length(a):return math.sqrt(dot(a,a))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def rotate(q,v,inverse=False):
    a=xyz(q);a=tuple(-x for x in a) if inverse else a
    c=cross(a,v);t=cross(a,tuple(c[i]+q.w*v[i] for i in range(3)))
    return tuple(v[i]+2*t[i] for i in range(3))
def angle(a,b):return math.degrees(math.acos(max(-1,min(1,dot(a,b)/(length(a)*length(b))))))
report={};mesh=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
for profile in ('Base','Drum','Angled','Vertical','Canted','Prism'):
    clip=u.load_asset(f'/Game/Weapons/M4QuickMeleeReplica20260919/{profile}/A_M4_QuickCombat_{profile}')
    rows={}
    for label,typ in (('RAW',u.AnimDataEvalType.RAW),('COMPRESSED',u.AnimDataEvalType.COMPRESSED)):
        opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=typ;opts.optional_skeletal_mesh=mesh
        opts.should_retarget=True
        samples=[]
        for frame in range(109):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,frame/120,opts)
            h=u.AnimPoseExtensions.get_bone_pose(pose,'hand_r',u.AnimPoseSpaces.WORLD)
            e=u.AnimPoseExtensions.get_bone_pose(pose,'lowerarm_r',u.AnimPoseSpaces.WORLD)
            hr=u.AnimPoseExtensions.get_ref_bone_pose(pose,'hand_r',u.AnimPoseSpaces.WORLD)
            er=u.AnimPoseExtensions.get_ref_bone_pose(pose,'lowerarm_r',u.AnimPoseSpaces.WORLD)
            ref=sub(xyz(hr.translation),xyz(er.translation))
            desired=rotate(h.rotation,rotate(hr.rotation,ref,True))
            samples.append({'frame':frame,'wrist':xyz(h.translation),'elbow':xyz(e.translation),
                            'wrist_axis_bend_deg':angle(sub(xyz(h.translation),xyz(e.translation)),desired)})
        rows[label]=samples
    position_error=max(length(sub(a['wrist'],b['wrist']))*10 for a,b in zip(rows['RAW'],rows['COMPRESSED']))
    angle_error=max(abs(a['wrist_axis_bend_deg']-b['wrist_axis_bend_deg']) for a,b in zip(rows['RAW'],rows['COMPRESSED']))
    report[profile]={'length':clip.get_play_length(),'raw_max_wrist_axis_bend_deg':max(x['wrist_axis_bend_deg'] for x in rows['RAW']),
                     'compressed_max_wrist_axis_bend_deg':max(x['wrist_axis_bend_deg'] for x in rows['COMPRESSED']),
                     'max_raw_compressed_wrist_position_difference_mm':position_error,
                     'max_raw_compressed_bend_difference_deg':angle_error,'samples':rows}
    u.log('M4_WRIST_N_UE %s %s'%(profile,json.dumps({k:v for k,v in report[profile].items() if k!='samples'})))
(P/'ue_readback.json').write_text(json.dumps(report,indent=2))
u.log('M4_WRIST_N_READBACK_COMPLETE')
