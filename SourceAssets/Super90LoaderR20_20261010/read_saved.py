"""Scoped post-import sample of the reported release/bolt segment; no game run."""
import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent
mesh=u.load_asset('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
out={'runtime_tested':False,'clips':{},'framing':{}}
names=('clavicle_l','upperarm_l','lowerarm_l','lowerarm_aux_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l','index_01_l','WPN_root')
def pack(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
for branch,end in (('normal',144),('empty',180)):
    for count in (1,7):
        name='A_Super90_loader_'+branch+'_'+str(count)
        clip=u.load_asset('/Game/Weapons/Super90/Speedloader20261007/Animations/'+name)
        row={'length':clip.get_play_length(),'revision':u.EditorAssetLibrary.get_metadata_tag(clip,'Super90SpeedloaderSource'),'samples':[]}
        for f in sorted({0,88,112,120,127,132,138,min(150,end),min(161,end),end}):
            sample={'frame':f}
            for mode in ('SOURCE','COMPRESSED'):
                opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.should_retarget=False;opt.evaluation_type=getattr(u.AnimDataEvalType,mode)
                pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,f/60.,opt)
                sample[mode]={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}
            row['samples'].append(sample)
        out['clips'][name]=row
for key,path in (('M4','/Game/Weapons/M4ContactImpactFinal/A_AKM_idle'),('Super90','/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_idle')):
    opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.should_retarget=False
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(u.load_asset(path),0.,opt)
    out['framing'][key]={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in ('hand_r','WPN_root','WPN_RearSight','WPN_FrontSight')}
(O/'saved_pose_samples.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('SUPER90_R20_POSES_READ',len(out['clips']),flush=True)
