import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent
mesh=u.load_asset('/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny')
clip=u.load_asset('/Game/Weapons/RifleTacticalSprint20260915/QBZ191/Base/A_QBZ191_TacticalSprint_Base_Enter')
u.AKMAnimationAuditLibrary.finish_animation_compression(clip)
d={'mesh_skeleton':mesh.skeleton.get_path_name(),'clip_skeleton':clip.get_editor_property('skeleton').get_path_name(),'samples':{}}
settings=clip.get_editor_property('bone_compression_settings')
d['compression']=settings.get_path_name();d['codecs']=[str(c) for c in settings.get_editor_property('codecs')]
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh
for retarget in (True,False):
    opt.should_retarget=retarget
    for mode in (u.AnimDataEvalType.RAW,u.AnimDataEvalType.COMPRESSED):
        opt.evaluation_type=mode
        for t in (0.,.15,.3):
            p=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opt)
            d['samples'][str(retarget)+str(mode)+str(t)]={n:str(u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD)) for n in ('root','WPN_root','hand_l','hand_r','WPN_SOCKET_Muzzle')}
(O/'qbz-compression-before.json').write_text(json.dumps(d,indent=2))
u.log(str(d))
