"""Import Kevin's already licensed free full-body death into a task-owned folder."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/PlayerDeath20261006'
BASE = '/Game/Characters/JasonPlayer20261003/SwordFullBody20261005'
DEST = '/Game/Characters/JasonPlayer20261003/Death20261006'
sources = json.loads((ROOT/'SourceAssets/ThirdPersonSwordFree20261005/imported-sources.json').read_text())
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
lib = u.EditorAssetLibrary
source, target = u.load_asset(sources['Kevin']['mesh']), u.load_asset(cfg['body_mesh'])
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
options.import_as_skeletal = False
options.import_mesh = False
options.import_animations = True
options.import_materials = options.import_textures = options.create_physics_asset = False
options.skeleton = source.skeleton
options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 30)
task = u.AssetImportTask()
task.filename = str(ROOT/'SourceAssets/ThirdPersonSwordFree20261005/Kevin/Animations/Male/Combat/HumanM@Death01.fbx')
task.destination_path = DEST+'/Source'
task.destination_name = 'A_Kevin_Death01'
task.automated = True
task.replace_existing = False
task.save = True
task.options = options
task.factory = u.FbxFactory()
if lib.does_asset_exist(task.destination_path+'/'+task.destination_name):
    raise RuntimeError('Death donor already exists; refusing replacement')
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
donor = u.load_asset(task.destination_path+'/'+task.destination_name)
if not lib.save_loaded_asset(donor, False):
    raise RuntimeError('Could not save death source')
inputs = u.IKRetargetBatchOperationInputs()
inputs.assets_to_retarget = [lib.find_asset_data(donor.get_path_name())]
inputs.source_mesh, inputs.target_mesh = source, target
inputs.ik_retarget_asset = u.load_asset(BASE+'/Rig/RTG_Kevin_Jason_Sword')
inputs.prefix = 'J_'
inputs.target_path = DEST+'/Source'
inputs.include_referenced_assets = False
inputs.overwrite_existing_files = False
results = u.IKRetargetBatchOperation.run_batch_retarget(inputs)
clip = next(x.get_asset() for x in results if isinstance(x.get_asset(),u.AnimSequence))
clip.set_preview_skeletal_mesh(target)
if not lib.save_loaded_asset(clip, False):
    raise RuntimeError('Could not save retargeted death')

# Export author input with the same layout as prepare_player_death.py.
ref = target.skeleton.get_reference_pose()
names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
component = u.new_object(u.SkeletalMeshComponent)
component.set_skeletal_mesh_asset(target)
parents = [names.index(str(component.get_parent_bone(n))) if str(component.get_parent_bone(n)) in names else -1 for n in names]
def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = target
options.evaluation_type = u.AnimDataEvalType.SOURCE
length = clip.get_play_length()
count = round(length*30)+1
frames, trajectory = [], []
for i in range(count):
    t = length*i/(count-1)
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
    frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
    trajectory.append(dict(t=t, **{n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in ['root','pelvis','head','hand_l','hand_r','foot_l','foot_r']}))
data = dict(mesh=target.get_path_name(),skeleton=target.skeleton.get_path_name(),source=clip.get_path_name(),duration=length,
    names=names,parents=parents,reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names],
    frames=frames,trajectory=trajectory)
(OUT/'kevin-authoring-input.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print('KEVIN_DEATH_IMPORTED '+clip.get_path_name()+' seconds='+str(length))
