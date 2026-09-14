"""Focused RAW/compressed comparison of the reported loading-hand displacement.

Gun inverse transforms remove the FBX root scale. Multiply that scale back
to report distances in UE centimeters, with rotation/translation removed.
"""
import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent;report={}
manifest=json.loads((O/'animation.json').read_text())
mesh=u.load_asset('/Game/Weapons/DanWesson715/Upgrade20260914/SK_DW715_Manny')
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh
def pose(p,n):return u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD)
def distance(a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
for kind in ['single_0_6','single_3_3']:
    clip=u.load_asset('/Game/Weapons/DanWesson715/ReloadSplit20260914/Animations/A_DW715_'+kind)
    spec=manifest['clips'][kind];begin=1.5 if spec['empty'] else .6;end=spec['duration']-.7;entry={}
    for mode in ['RAW','COMPRESSED']:
        opt.evaluation_type=getattr(u.AnimDataEvalType,mode);last={};jumps=[];contact_xz=[]
        for i in range(round(clip.get_play_length()*120)+1):
            p=u.AnimPoseExtensions.get_anim_pose_at_time(clip,i/120,opt);G=pose(p,'WPN_root')
            for name in ['hand_l','lowerarm_l','upperarm_l','clavicle_l','thumb_03_l','index_03_l']:
                H=pose(p,name);v=G.inverse_transform_location(H.translation)
                v=(v.x*G.scale3d.x,v.y*G.scale3d.y,v.z*G.scale3d.z)
                if name in last:jumps.append({'time':i/120,'bone':name,'step_cm':distance(v,last[name])})
                last[name]=v
        loading=[x for x in jumps if begin<x['time']<end]
        contact=[x for x in jumps if any(abs(x['time']-t)<.1 for t in spec['seats'])]
        entry[mode]={'gun_scale':str(G.scale3d),
            'loading_peak_steps':sorted(loading,key=lambda x:x['step_cm'],reverse=True)[:12],
            'contact_peak_steps':sorted(contact,key=lambda x:x['step_cm'],reverse=True)[:12]}
    report[kind]=entry
    u.log('DW715_DISPLACEMENT_AFTER '+kind+' '+json.dumps(entry))
(O/'diagnosis-import-after.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('DW715_DISPLACEMENT_AFTER_COMPLETE')
