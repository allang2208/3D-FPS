"""Read the reported failing saved motion without changing or playing assets."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
mesh=u.load_asset('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
sc=u.SkeletalMeshComponent();sc.set_skeletal_mesh_asset(mesh)
names=[str(sc.get_bone_name(i)) for i in range(sc.get_num_bones())]
def pack(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
out={'clips':{},'framing':{}}
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.should_retarget=False
for kind in ('normal_7','normal_1','empty_7'):
    clip=u.load_asset('/Game/Weapons/Super90/Speedloader20261007/Animations/A_Super90_loader_'+kind)
    rows=[]
    for mode in ('SOURCE','COMPRESSED'):
        opt.evaluation_type=getattr(u.AnimDataEvalType,mode)
        for frame in (0,74,87,90,114):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,frame/60,opt)
            rows.append({'mode':mode,'frame':frame,'local':{n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names}})
    out['clips'][kind]={'length':clip.get_play_length(),'rows':rows}
for key,asset in [('M4','/Game/Weapons/M4ContactImpactFinal/A_AKM_idle'),('Super90','/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_idle')]:
    clip=u.load_asset(asset);opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=u.AnimDataEvalType.COMPRESSED;opts.should_retarget=False
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0.,opts)
    out['framing'][key]={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in ('hand_r','WPN_root','WPN_RearSight','WPN_FrontSight')}
(O/'saved_motion_r3.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
print('SAVED_LOADER_INPUTS_READ',flush=True)
