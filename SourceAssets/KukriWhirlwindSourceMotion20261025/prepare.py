"""Read the active native whirlwind packages and idle, without running gameplay."""
import json
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
result={}
for label,section in [('jason',cfg),('kaitlin',cfg['body_variants']['kaitlin'])]:
    mesh=u.load_asset(section['body_mesh']);ref=mesh.skeleton.get_reference_pose()
    names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
    component=u.SkeletalMeshComponent();component.set_skeletal_mesh_asset(mesh)
    data=dict(mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),names=names,
        parents=[names.index(str(component.get_parent_bone(n))) if str(component.get_parent_bone(n)) in names else -1 for n in names],
        reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names],
        reference_world=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.WORLD)) for n in names],clips={})
    options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh;options.evaluation_type=u.AnimDataEvalType.SOURCE
    idle=u.load_asset(section['clips']['Kukri.FullBody.Idle'])
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(idle,0.,options)
    data['idle']=[pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names]
    data['idle_asset']=idle.get_path_name()
    for role in ('Whirlwind.Start','Whirlwind.Loop','Whirlwind.End'):
        clip=u.load_asset(section['clips']['Kukri.FullBody.'+role]);duration=clip.get_play_length()
        frames=[];compressed=[];rate=60
        tracked=['pelvis','spine_03']+[n+'_'+s for s in 'lr' for n in ('clavicle','upperarm','lowerarm','hand')]
        for k in range(round(duration*rate)+1):
            t=min(k/rate,duration);options.evaluation_type=u.AnimDataEvalType.SOURCE
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
            frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
            options.evaluation_type=u.AnimDataEvalType.COMPRESSED
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
            compressed.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in tracked])
        data['clips'][role]=dict(asset=clip.get_path_name(),duration=duration,rate=rate,frames=frames,compressed_bones=tracked,compressed_world=compressed)
    result[label]=data
    (OUT/'active-inputs.json').write_text(json.dumps(result,separators=(',',':')))
    print('WHIRLWIND_ACTIVE_READ '+label,flush=True)
