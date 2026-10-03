"""Read the specific uppercut assets to isolate source versus imported drift."""
from pathlib import Path
import json
import unreal as u
P=Path(__file__).resolve().parent
mesh=u.load_asset('/Game/Characters/ModularOutfit20260924/BarePalmV7/RuneSword/SK_RuneSword_BareArmsV7')
names=['WPN_root','Blade_Base','Blade_Tip','upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r']
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return dict(p=[p.x,p.y,p.z],q=[q.w,q.x,q.y,q.z],s=[s.x,s.y,s.z])
out={}
for variant in ('Standard','LongGrip'):
    asset=u.load_asset('/Game/Weapons/SwordUppercut20261003/'+variant+'/A_Sword_UppercutV1_'+variant)
    item={'revision':u.EditorAssetLibrary.get_metadata_tag(asset,'SwordUppercut.Revision'),'seconds':asset.get_play_length(),'samples':{}}
    for kind in ('SOURCE','COMPRESSED'):
        options=u.AnimPoseEvaluationOptions()
        options.evaluation_type=getattr(u.AnimDataEvalType,kind)
        options.optional_skeletal_mesh=mesh
        rows=[]
        for t in (0.,.175,.233333,1.,1.125,1.267,1.6,1.8,1.833333,2.05):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(asset,t,options)
            rows.append({'t':t,'world':{n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}})
        item['samples'][kind]=rows
    out[variant]=item
(P/globals().get('POSE_OUTPUT_NAME','current_pose_before.json')).write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
print('UPPERCUT_POSE_READ '+json.dumps({v:{k:d[k] for k in ('revision','seconds')} for v,d in out.items()}))
