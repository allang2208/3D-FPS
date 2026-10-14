"""Import actual CC0 UAL2 sword takes and retarget them to Jason, headless.

This creates only new packages. The original author archive is kept locally.
No map, pawn, preview renderer or play session is started.
"""
import json
import re
import zipfile
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonSwordDonorRepair20261006'
OUT.mkdir(parents=True, exist_ok=True)
DEST = '/Game/Characters/JasonPlayer20261003/SwordDonorRepair20261006/Source'
lib = u.EditorAssetLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
target = u.load_asset(cfg['body_mesh'])

def save(asset):
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed: '+asset.get_path_name())

def create(name, folder, cls, factory):
    if lib.does_asset_exist(DEST+'/'+folder+'/'+name):
        raise RuntimeError('Existing repair asset: '+name)
    return assets.create_asset(name, DEST+'/'+folder, cls, factory)

def import_fbx(filename, name, skeleton=None):
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION if skeleton else u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal = not bool(skeleton)
    options.import_mesh = not bool(skeleton)
    options.import_animations = bool(skeleton)
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    if skeleton:
        options.skeleton = skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 30)
    task = u.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = DEST+'/Donor'
    task.destination_name = name
    task.automated = True
    task.replace_existing = False
    task.save = True
    task.options = options
    task.factory = u.FbxFactory()
    assets.import_asset_tasks([task])
    imported = [u.load_asset(p) for p in lib.list_assets(task.destination_path, True, False)]
    for asset in imported:
        # Legacy FBX's task.save does not save every generated dependency.
        if isinstance(asset, u.SkeletalMesh) and asset.skeleton:
            save(asset.skeleton)
        save(asset)
    return imported

with zipfile.ZipFile(ROOT/'SourceAssets/ThirdPersonSwordCandidates20261006/UAL2-Standard-author.zip') as z:
    for suffix in ('Female Mannequin/Unity/Mannequin_F.fbx', 'Unity/UAL2_Standard.fbx'):
        entry = next(n for n in z.namelist() if n.endswith('/'+suffix))
        (OUT/Path(suffix).name).write_bytes(z.read(entry))

source = next(a for a in import_fbx(OUT/'Mannequin_F.fbx', 'SK_UAL2_Mannequin') if isinstance(a, u.SkeletalMesh))
imported = import_fbx(OUT/'UAL2_Standard.fbx', 'A_UAL2', source.skeleton)
save(source.skeleton)
source_names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(source.skeleton.get_reference_pose())]
clips = {a.get_name(): a.get_path_name() for a in imported if isinstance(a, u.AnimSequence)}
(OUT/'imported-sources.json').write_text(json.dumps(dict(mesh=source.get_path_name(), bones=source_names, clips=clips), indent=2))
selected = [u.load_asset(p) for n, p in clips.items() if n.endswith(('Sword_Heavy_Combo', 'Sword_Regular_Combo', 'Sword_Dash'))]
if len(selected) != 3:
    raise RuntimeError('Unexpected UAL2 sword take names: '+str(list(clips)))

# Preserve the original donor's component-space anatomy before any retargeting.
def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
raw_options = u.AnimPoseEvaluationOptions()
raw_options.optional_skeletal_mesh = source
raw_options.evaluation_type = u.AnimDataEvalType.SOURCE
raw_clips = {}
for clip in selected:
    duration = clip.get_play_length()
    frames = []
    for i in range(round(duration*60)+1):
        p = u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(i/60,duration),raw_options)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD)) for n in source_names])
    raw_clips[clip.get_name()] = dict(asset=clip.get_path_name(),duration=duration,frames=frames)
raw_ref = source.skeleton.get_reference_pose()
(OUT/'original-poses.json').write_text(json.dumps(dict(names=source_names,
    reference=[pack(u.AnimPoseExtensions.get_bone_pose(raw_ref,n,u.AnimPoseSpaces.WORLD)) for n in source_names],clips=raw_clips),separators=(',',':')))

ik = create('IK_UAL2_Sword', 'Rig', u.IKRigDefinition, u.IKRigDefinitionFactory())
c = u.IKRigController.get_controller(ik)
c.set_skeletal_mesh(source)
names = {re.sub('[^a-z0-9]', '', n.lower()): n for n in source_names}
def bone(n):
    return names[re.sub('[^a-z0-9]', '', n.lower())]
c.set_retarget_root(bone('pelvis'))
chains = {'Spine': ('spine_01', 'spine_03'), 'Neck': ('neck_01', 'neck_01'), 'Head': ('head', 'head')}
for side in ('l', 'r'):
    for label, start, end in [('Clavicle', 'clavicle', 'clavicle'), ('Arm', 'upperarm', 'hand'), ('Leg', 'thigh', 'foot'), ('Toe', 'ball', 'ball')]:
        chains[label+'_'+side] = (start+'_'+side, end+'_'+side)
    for digit in ('thumb', 'index', 'middle', 'ring', 'pinky'):
        chains[digit+'_'+side] = (digit+'_01_'+side, digit+'_03_'+side)
for label, (start, end) in chains.items():
    c.add_retarget_chain(label, bone(start), bone(end), '')
save(ik)
target_rig = u.load_asset('/Game/Characters/JasonPlayer20261003/SwordFullBody20261005/Rig/IK_Jason_Sword')
rtg = create('RTG_UAL2_Jason_Sword', 'Rig', u.IKRetargeter, u.IKRetargetFactory())
c = u.IKRetargeterController.get_controller(rtg)
c.set_ik_rig(u.RetargetSourceOrTarget.SOURCE, ik)
c.set_ik_rig(u.RetargetSourceOrTarget.TARGET, target_rig)
c.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE, source)
c.set_preview_mesh(u.RetargetSourceOrTarget.TARGET, target)
c.add_default_ops()
c.auto_map_chains(u.AutoMapChainType.EXACT, True)
pose = c.create_retarget_pose('Jason_UAL2_Aligned', u.RetargetSourceOrTarget.TARGET)
c.set_current_retarget_pose(pose, u.RetargetSourceOrTarget.TARGET)
c.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
save(rtg)
inputs = u.IKRetargetBatchOperationInputs()
inputs.assets_to_retarget = [lib.find_asset_data(a.get_path_name()) for a in selected]
inputs.source_mesh = source
inputs.target_mesh = target
inputs.ik_retarget_asset = rtg
inputs.prefix = 'J_'
inputs.target_path = DEST+'/DonorRetargeted'
inputs.include_referenced_assets = False
inputs.overwrite_existing_files = False
retargeted = [d.get_asset() for d in u.IKRetargetBatchOperation.run_batch_retarget(inputs)]

options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = target
options.evaluation_type = u.AnimDataEvalType.SOURCE
names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(target.skeleton.get_reference_pose())]
def pack(t):
    return [t.translation.x, t.translation.y, t.translation.z, t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w, t.scale3d.x, t.scale3d.y, t.scale3d.z]
result = {}
for clip in retargeted:
    if not isinstance(clip, u.AnimSequence):
        continue
    save(clip)
    duration = clip.get_play_length()
    frames = []
    for i in range(round(duration*60)+1):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, min(i/60, duration), options)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL)) for n in names])
    result[clip.get_name()] = dict(asset=clip.get_path_name(), duration=duration, rate=60, frames=frames)
(OUT/'retargeted-poses.json').write_text(json.dumps(dict(names=names, clips=result), separators=(',', ':')))
print('UAL2_SWORD_DONORS_SAVED '+json.dumps({k:v['asset'] for k,v in result.items()}))
