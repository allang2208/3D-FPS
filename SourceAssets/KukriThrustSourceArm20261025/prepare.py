"""Read the original local KayKit stab and the active native thrusts."""
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
TARGETS = json.loads((ROOT/'SourceAssets/KukriThirdPerson20261024/ComboV3/inputs.json').read_text())['targets']
CFG = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))


def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]


library = json.loads((ROOT/'SourceAssets/ThirdPersonSwordFree20261005/imported-sources.json').read_text())['KayKit']
mesh = u.load_asset(library['mesh'])
clip = u.load_asset(library['clips']['SK_KayKit_Medium_Anim_Melee_1H_Attack_Stab'])
ref = mesh.skeleton.get_reference_pose()
names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
component = u.SkeletalMeshComponent()
component.set_skeletal_mesh_asset(mesh)
source = dict(mesh=mesh.get_path_name(), asset=clip.get_path_name(), names=names,
    parents=[names.index(str(component.get_parent_bone(n))) if str(component.get_parent_bone(n)) in names else -1 for n in names],
    reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names],
    reference_world=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.WORLD)) for n in names],
    rate=60, duration=clip.get_play_length(), frames=[])
opt = u.AnimPoseEvaluationOptions()
opt.optional_skeletal_mesh = mesh
opt.evaluation_type = u.AnimDataEvalType.SOURCE
for k in range(round(clip.get_play_length()*60)+1):
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(k/60,clip.get_play_length()),opt)
    source['frames'].append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names])
(OUT/'kaykit-stab-source.json').write_text(json.dumps(source,separators=(',',':')))
print('KUKRI_SOURCE_ARM_DONOR '+source['asset']+' bones='+str(names),flush=True)

for label, target in TARGETS.items():
    section = CFG if label == 'jason' else CFG['body_variants'][label]
    path = section['clips']['Kukri.FullBody.Thrust']
    clip = u.load_asset(path)
    mesh = u.load_asset(target['mesh'])
    opt.optional_skeletal_mesh = mesh
    frames = []
    for k in range(round(clip.get_play_length()*60)+1):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(k/60,clip.get_play_length()),opt)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in target['names']])
    old = json.loads((ROOT/f'SourceAssets/KukriThrustWrist20261025/{label}-actions.json').read_text())['clips']['Thrust']
    old['frames'] = frames
    old['rate'] = 60
    (OUT/(label+'-current.json')).write_text(json.dumps(dict(asset=path,clips={'Thrust':old}),separators=(',',':')))
    print('KUKRI_SOURCE_ARM_INPUT '+label+' '+path,flush=True)
