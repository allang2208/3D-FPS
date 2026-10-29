"""Read current native carry and full-body thrust inputs; never save source packages."""
import json
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
def pack(t):
    return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
result={}
for label,section in [('jason',cfg),('kaitlin',cfg['body_variants']['kaitlin'])]:
    mesh=u.load_asset(section['body_mesh']);ref=mesh.skeleton.get_reference_pose()
    names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
    comp=u.SkeletalMeshComponent();comp.set_skeletal_mesh_asset(mesh)
    data=dict(mesh=mesh.get_path_name(),names=names,
        parents=[names.index(str(comp.get_parent_bone(n))) if str(comp.get_parent_bone(n)) in names else -1 for n in names],
        reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names],
        reference_world=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.WORLD)) for n in names],clips={})
    opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.SOURCE
    for role,key in [('Hip','Pistol.KukriCarry.Hip'),('Aim','Pistol.KukriCarry.Aim'),('Thrust','Kukri.FullBody.Thrust')]:
        clip=u.load_asset(section['clips'][key]);length=clip.get_play_length()
        times=[0.] if role!='Thrust' else [min(i/60.,length) for i in range(round(length*60)+1)]
        frames=[]
        for t in times:
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opt)
            frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
        data['clips'][role]=dict(asset=clip.get_path_name(),frames=frames,rate=60,duration=length)
    data['idle']=data['clips']['Hip']['frames'][0]
    result[label]=data
(OUT/'inputs.json').write_text(json.dumps(result,separators=(',',':')))
print('PISTOL_KUKRI_THRUST_INPUTS_SAVED',flush=True)
