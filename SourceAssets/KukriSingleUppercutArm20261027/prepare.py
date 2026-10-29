"""Read the installed first-person single-hand uppercut and native body boundaries."""
import json
from pathlib import Path
import unreal as u

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))

def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]

def skeleton(mesh):
    ref=mesh.skeleton.get_reference_pose()
    names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
    comp=u.SkeletalMeshComponent();comp.set_skeletal_mesh_asset(mesh)
    return dict(mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),names=names,
        parents=[names.index(str(comp.get_parent_bone(n))) if str(comp.get_parent_bone(n)) in names else -1 for n in names],
        reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names],
        reference_world=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.WORLD)) for n in names])

def read_clip(path,mesh,names,space,rate=120):
    clip=u.load_asset(path)
    if not isinstance(clip,u.AnimSequence):raise RuntimeError('Missing action source '+path)
    opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.SOURCE
    length=clip.get_play_length();frames=[]
    for k in range(round(length*rate)+1):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(length,k/rate),opt)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,space)) for n in names])
    markers={str(m.marker_name):m.time for m in u.AnimationLibrary.get_animation_sync_markers(clip)}
    return dict(asset=clip.get_path_name(),duration=length,rate=rate,frames=frames,markers=markers)

mesh=u.load_asset('/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms')
native=skeleton(mesh)
native['uppercut']=read_clip('/Game/Weapons/Kukri20261020/Animations/A_Kukri_Uppercut',mesh,native['names'],u.AnimPoseSpaces.WORLD)
native['idle']=read_clip('/Game/Weapons/Kukri20261020/Animations/A_Kukri_Idle',mesh,native['names'],u.AnimPoseSpaces.WORLD)
result=dict(native=native,targets={})
for label,section in [('jason',cfg),('kaitlin',cfg['body_variants']['kaitlin'])]:
    mesh=u.load_asset(section['body_mesh']);data=skeleton(mesh)
    idle=read_clip(section['clips']['Kukri.FullBody.Idle'],mesh,data['names'],u.AnimPoseSpaces.LOCAL)
    data['idle']=idle['frames'][0];data['idle_asset']=idle['asset']
    data['previous']=read_clip(section['clips']['Kukri.FullBody.Uppercut'],mesh,data['names'],u.AnimPoseSpaces.LOCAL)
    result['targets'][label]=data
(OUT/'inputs.json').write_text(json.dumps(result,separators=(',',':')))
print('KUKRI_SINGLE_UPPERCUT_ARM_INPUTS_SAVED',flush=True)
