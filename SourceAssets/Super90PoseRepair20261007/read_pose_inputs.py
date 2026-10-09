"""Read the saved bind/idle transforms needed to repair the reported alignment."""
import json
from pathlib import Path
import unreal as u

O=Path(__file__).parent
O.mkdir(exist_ok=True)
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return {'p':[p.x,p.y,p.z],'q':[q.w,q.x,q.y,q.z],'s':[s.x,s.y,s.z]}

result={}
sources={
    'super90':('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7',
               '/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_idle'),
    'm4_reference':('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
                    '/Game/Weapons/M4ContactImpactFinal/A_AKM_idle'),
}
for key,(mesh_path,clip_path) in sources.items():
    mesh=u.load_asset(mesh_path);clip=u.load_asset(clip_path)
    if not mesh or not clip:raise RuntimeError('Missing '+key)
    modifier=u.SkeletonModifier();modifier.set_skeletal_mesh(mesh)
    names=[str(n) for n in modifier.get_all_bone_names()]
    row={'mesh':mesh.get_path_name(),'clip':clip.get_path_name(),
         'parents':{n:str(modifier.get_parent_name(n)) for n in names},
         'reference':{n:pack(modifier.get_bone_transform(n,True)) for n in names}}
    for label,kind in [('source',u.AnimDataEvalType.SOURCE),('compressed',u.AnimDataEvalType.COMPRESSED)]:
        options=u.AnimPoseEvaluationOptions();options.evaluation_type=kind;options.optional_skeletal_mesh=mesh
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0.,options)
        row[label]={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}
    result[key]=row
(O/'pose_inputs.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('SUPER90_POSE_INPUTS_SAVED')
