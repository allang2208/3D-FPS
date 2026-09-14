"""Requested diagnosis without PIE. Gun-local units exclude FBX root scale."""
import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent;report={}
mesh=u.load_asset('/Game/Weapons/DanWesson715/Upgrade20260914/SK_DW715_Manny')
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh
def position(p,n):return u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD)
def distance(a,b):return math.sqrt((a.x-b.x)**2+(a.y-b.y)**2+(a.z-b.z)**2)
for kind in ['single_0_6','single_3_3']:
    clip=u.load_asset('/Game/Weapons/DanWesson715/SingleLoad20260914/Animations/A_DW715_'+kind);entry={}
    contacts=[.55+j*1.15+.91 for j in range(int(kind[-1]))]
    for mode in ['RAW','COMPRESSED']:
        opt.evaluation_type=getattr(u.AnimDataEvalType,mode);last={};jumps=[]
        for i in range(round(clip.get_play_length()*120)+1):
            p=u.AnimPoseExtensions.get_anim_pose_at_time(clip,i/120,opt);G=position(p,'WPN_root')
            for name in ['hand_l','lowerarm_l','upperarm_l','clavicle_l','thumb_03_l','index_03_l']:
                H=position(p,name);v=G.inverse_transform_location(H.translation)
                if name in last:jumps.append({'time':i/120,'bone':name,'step_gun_units':distance(v,last[name])})
                last[name]=v
        entry[mode]={'peak_steps':sorted(jumps,key=lambda x:x['step_gun_units'],reverse=True)[:12],
            'contact_peak_steps':sorted([x for x in jumps if any(abs(x['time']-t)<.12 for t in contacts)],key=lambda x:x['step_gun_units'],reverse=True)[:12]}
    report[kind]=entry
    u.log('DW715_DISPLACEMENT_DIAGNOSIS '+kind+' '+json.dumps(entry))
(O/'diagnosis-import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('DW715_DISPLACEMENT_DIAGNOSIS_COMPLETE')
