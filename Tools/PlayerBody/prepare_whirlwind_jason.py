"""Retarget the CC0 spinning donor and export poses for offline leg authoring.

Run in a background Python commandlet, or through the existing editor batch
mutex when an editor is already open. Writes only this task's new Source asset.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonWhirlwind20261006'
BASE = '/Game/Characters/JasonPlayer20261003/SwordFullBody20261005'
DEST = '/Game/Characters/JasonPlayer20261003/Whirlwind20261006'
lib = u.EditorAssetLibrary
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
sources = json.loads((ROOT/'SourceAssets/ThirdPersonSwordFree20261005/imported-sources.json').read_text())['KayKit']
mesh = u.load_asset(cfg['body_mesh'])
source = u.load_asset(sources['mesh'])
loop_source_path = next(p for n, p in sources['clips'].items() if n.endswith('Melee_2H_Attack_Spinning'))
spin_source_path = next(p for n, p in sources['clips'].items() if n.endswith('Melee_2H_Attack_Spin'))
loop_path = DEST+'/Source/J_'+loop_source_path.split('.')[-1]
loop = u.load_asset(loop_path) if lib.does_asset_exist(loop_path) else None
if loop is None:
    inputs = u.IKRetargetBatchOperationInputs()
    inputs.assets_to_retarget = [lib.find_asset_data(loop_source_path)]
    inputs.source_mesh = source
    inputs.target_mesh = mesh
    inputs.ik_retarget_asset = u.load_asset(BASE+'/Rig/RTG_KayKit_Jason_Sword')
    inputs.prefix = 'J_'
    inputs.target_path = DEST+'/Source'
    inputs.include_referenced_assets = False
    inputs.overwrite_existing_files = False
    outputs = u.IKRetargetBatchOperation.run_batch_retarget(inputs)
    loop = next(d.get_asset() for d in outputs if isinstance(d.get_asset(), u.AnimSequence))
    loop.set_preview_skeletal_mesh(mesh)
    if not lib.save_loaded_asset(loop, False):
        raise RuntimeError('Could not save retargeted spinning donor')

component = u.new_object(u.SkeletalMeshComponent)
component.set_skeletal_mesh_asset(mesh)
ref = mesh.skeleton.get_reference_pose()
names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
parents = [names.index(str(component.get_parent_bone(n))) if str(component.get_parent_bone(n)) in names else -1 for n in names]

def pack(t):
    return [t.translation.x, t.translation.y, t.translation.z,
            t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w,
            t.scale3d.x, t.scale3d.y, t.scale3d.z]

def extract(clip, donor):
    options = u.AnimPoseEvaluationOptions()
    options.optional_skeletal_mesh = mesh
    options.evaluation_type = u.AnimDataEvalType.SOURCE
    donor_options = u.AnimPoseEvaluationOptions()
    donor_options.optional_skeletal_mesh = source
    donor_options.evaluation_type = u.AnimDataEvalType.SOURCE
    duration = clip.get_play_length()
    count = round(duration*60)+1
    frames, donor_roots = [], []
    for i in range(count):
        t = duration*i/(count-1)
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, t, options)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL)) for n in names])
        donor_pose = u.AnimPoseExtensions.get_anim_pose_at_time(donor, t, donor_options)
        donor_roots.append(pack(u.AnimPoseExtensions.get_bone_pose(donor_pose, 'root', u.AnimPoseSpaces.WORLD)))
    return dict(asset=clip.get_path_name(), duration=duration, frames=frames, donor_roots=donor_roots)

spin = u.load_asset(BASE+'/Animations/J_SK_KayKit_Medium_Anim_Melee_2H_Attack_Spin')
data = dict(mesh=mesh.get_path_name(), skeleton=mesh.skeleton.get_path_name(), names=names, parents=parents,
            reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref, n, u.AnimPoseSpaces.LOCAL)) for n in names],
            spin=extract(spin, u.load_asset(spin_source_path)), loop=extract(loop, u.load_asset(loop_source_path)))
(OUT/'authoring-input.json').write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
print('WHIRLWIND_PREPARED '+loop.get_path_name()+' bones='+str(len(names)))
