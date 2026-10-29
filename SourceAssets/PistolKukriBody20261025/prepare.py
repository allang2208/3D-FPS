"""Read both native pistol idle and book-carry source poses for authoring."""
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
    comp=u.SkeletalMeshComponent();comp.set_skeletal_mesh_asset(mesh)
    data=dict(mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),names=names,
        parents=[names.index(str(comp.get_parent_bone(n))) if str(comp.get_parent_bone(n)) in names else -1 for n in names],
        reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names],
        reference_world=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.WORLD)) for n in names])
    opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.SOURCE
    for key,role in [('idle','Pistol.Idle'),('book','Staff.BookCarry')]:
        clip=u.load_asset(section['clips'][role]);pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0.,opt)
        data[key]=[pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names]
        data[key+'_asset']=clip.get_path_name()
    result[label]=data
(OUT/'inputs.json').write_text(json.dumps(result,separators=(',',':')))
print('PISTOL_KUKRI_NATIVE_INPUTS_SAVED',flush=True)
