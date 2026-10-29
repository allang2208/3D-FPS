"""Read native body and original CC0 combo inputs for offline authoring only."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))

def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]

def skeleton(mesh):
    ref = mesh.skeleton.get_reference_pose()
    names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
    comp = u.SkeletalMeshComponent()
    comp.set_skeletal_mesh_asset(mesh)
    return dict(mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),names=names,
        parents=[names.index(str(comp.get_parent_bone(n))) if str(comp.get_parent_bone(n)) in names else -1 for n in names],
        reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names],
        reference_world=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.WORLD)) for n in names])

targets = {}
for label,section in [('jason',cfg),('kaitlin',cfg['body_variants']['kaitlin'])]:
    mesh = u.load_asset(section['body_mesh'])
    entry = skeleton(mesh)
    idle = u.load_asset(section['clips']['Kukri.FullBody.Idle'])
    opt = u.AnimPoseEvaluationOptions()
    opt.optional_skeletal_mesh = mesh
    opt.evaluation_type = u.AnimDataEvalType.SOURCE
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(idle,0.,opt)
    entry['idle'] = [pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in entry['names']]
    entry['idle_asset'] = idle.get_path_name()
    targets[label] = entry

prefix = '/Game/Characters/JasonPlayer20261003/SwordDonorRepair20261006/Source/Donor/'
mesh = u.load_asset(prefix+'SK_UAL2_Mannequin')
source = skeleton(mesh)
opt = u.AnimPoseEvaluationOptions()
opt.optional_skeletal_mesh = mesh
opt.evaluation_type = u.AnimDataEvalType.SOURCE
source['clips'] = {}
for label in ['Sword_Regular_Combo','Sword_Regular_A','Sword_Regular_B','Sword_Regular_A_Rec','Sword_Regular_B_Rec']:
    clip = u.load_asset(prefix+'A_UAL2_Armature_'+label)
    if not isinstance(clip,u.AnimSequence):
        raise RuntimeError('Missing original CC0 clip '+label)
    length = clip.get_play_length()
    frames = []
    for i in range(round(length*60)+1):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(length,i/60),opt)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in source['names']])
    source['clips'][label] = dict(asset=clip.get_path_name(),duration=length,rate=60,frames=frames)
    print('KUKRI_COMBO_SOURCE '+label,flush=True)

native_mesh = u.load_asset('/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms')
native = skeleton(native_mesh)
native['grip'] = json.loads((OUT.parent/'native-grip.json').read_text())['bones']
(OUT/'inputs.json').write_text(json.dumps(dict(targets=targets,source=source,native=native),separators=(',',':')))
print('KUKRI_COMBO_INPUTS_SAVED',flush=True)
