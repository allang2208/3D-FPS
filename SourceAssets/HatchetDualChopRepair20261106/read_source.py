"""Read the installed dual-heavy poses before editing; no game world or saves."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text('utf-8-sig'))
A = u.AnimPoseExtensions

def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]

for label, body in [('Arms',None),('Jason',cfg),('Kaitlin',cfg['body_variants']['kaitlin'])]:
    meshpath = '/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms' if body is None else body['body_mesh']
    mesh = u.load_asset(meshpath)
    ref = mesh.skeleton.get_reference_pose()
    names = [str(n) for n in A.get_bone_names(ref)]
    comp = u.SkeletalMeshComponent(); comp.set_skeletal_mesh_asset(mesh)
    parents = [names.index(str(comp.get_parent_bone(n))) if str(comp.get_parent_bone(n)) in names else -1 for n in names]
    options = u.AnimPoseEvaluationOptions(); options.optional_skeletal_mesh=mesh; options.evaluation_type=u.AnimDataEvalType.SOURCE
    paths = {r:'/Game/Weapons/TacticalHatchet20261101/SwiftFalconHeavy/'+label+'/A_Falcon'+r for r in ['DualCharge','DualRelease']}
    paths['Idle'] = '/Game/Weapons/Kukri20261020/Animations/A_Kukri_DualIdle' if body is None else body['clips']['Kukri.FullBody.Dual.Idle']
    paths['Attack2'] = '/Game/Weapons/Kukri20261020/Animations/A_Kukri_DualAttack2' if body is None else body['clips']['Kukri.FullBody.Dual.Slash2']
    if body is None: paths['OldChop']='/Game/Weapons/TacticalHatchet20261101/Animations/A_TacticalHatchet_DualAttack3'
    data=dict(mesh=meshpath,names=names,parents=parents,reference=[pack(A.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names],clips={})
    for role,path in paths.items():
        clip=u.load_asset(path)
        if not clip: raise RuntimeError(path)
        frames=[]
        for f in range(1 if role=='Idle' else round(clip.get_play_length()*60)+1):
            pose=A.get_anim_pose_at_time(clip,min(f/60,clip.get_play_length()),options)
            frames.append([pack(A.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
        data['clips'][role]=dict(path=clip.get_path_name(),length=clip.get_play_length(),frames=frames)
    (P/(label+'-source.json')).write_text(json.dumps(data,separators=(',',':')),'utf8')
u.log('HATCHET_DUAL_SOURCE_SAVED')
