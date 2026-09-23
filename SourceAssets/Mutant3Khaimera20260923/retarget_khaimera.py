"""Background source intake and native IK retargeting; no gameplay or rendering."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
BASE = '/Game/ParagonKhaimera/Characters/Heroes/Khaimera'
TARGET = '/Game/Monsters/Mutant3Meshy'
DEST = TARGET + '/KhaimeraV1'
LIB = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
NAMES = ['Idle_NonAdditive', 'Jog_Fwd', 'TravelMode_Fwd', 'Bound',
         'Jog_Fwd_Start', 'Jog_Fwd_Stop', 'Jog_Fwd_Pivot_180',
         'RMB_60fps', 'RMB_Targeting_Moving', 'Jump_Start', 'Jump_Apex',
         'Jump_PreLand', 'Jump_Recovery', 'Melee_A_Fast', 'Melee_B_Fast',
         'Melee_C_Fast', 'Melee_Air_Attack', 'R_Ability_Intro_Loop']

def save(asset):
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())

def create(name, cls, factory):
    return u.load_asset(DEST + '/Rig/' + name) or TOOLS.create_asset(name, DEST + '/Rig', cls, factory)

def export(asset, folder, mesh=False):
    task = u.AssetExportTask()
    task.object = asset
    task.filename = str(ROOT / folder / (asset.get_name() + '.fbx'))
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.exporter = u.SkeletalMeshExporterFBX() if mesh else u.AnimSequenceExporterFBX()
    task.options = u.FbxExportOption()
    task.options.set_editor_property('export_preview_mesh', False)
    if not u.Exporter.run_asset_export_task(task):
        raise RuntimeError('Export failed: ' + asset.get_path_name())

source = u.load_asset(BASE + '/Meshes/Khaimera')
target = u.load_asset(TARGET + '/SK_Mutant3_Meshy')
if not source or not target:
    raise RuntimeError('Source/target meshes are required')
source_component = u.SkeletalMeshComponent()
source_component.set_skeletal_mesh_asset(source)
source_bones = [str(source_component.get_bone_name(i)) for i in range(source_component.get_num_bones())]
target_component = u.SkeletalMeshComponent()
target_component.set_skeletal_mesh_asset(target)
target_bones = [str(target_component.get_bone_name(i)) for i in range(target_component.get_num_bones())]
(ROOT / 'skeletons.json').write_text(json.dumps({'source': source_bones, 'target': target_bones}, indent=2))

source_chains = {'Spine': ('spine_01', 'spine_03'), 'Neck': ('neck_01', 'neck_01'), 'Head': ('head', 'head'),
    'ClavicleLeft': ('clavicle_l', 'clavicle_l'), 'ClavicleRight': ('clavicle_r', 'clavicle_r'),
    'ArmLeft': ('upperarm_l', 'hand_l'), 'ArmRight': ('upperarm_r', 'hand_r'),
    'LegLeft': ('thigh_l', 'foot_l'), 'LegRight': ('thigh_r', 'foot_r'),
    'ToeLeft': ('ball_l', 'ball_l'), 'ToeRight': ('ball_r', 'ball_r')}
target_chains = {'Spine': ('Spine02', 'Spine'), 'Neck': ('neck', 'neck'), 'Head': ('Head', 'Head'),
    'ClavicleLeft': ('LeftShoulder', 'LeftShoulder'), 'ClavicleRight': ('RightShoulder', 'RightShoulder'),
    'ArmLeft': ('LeftArm', 'LeftHand'), 'ArmRight': ('RightArm', 'RightHand'),
    'LegLeft': ('LeftUpLeg', 'LeftFoot'), 'LegRight': ('RightUpLeg', 'RightFoot'),
    'ToeLeft': ('LeftToeBase', 'LeftToeBase'), 'ToeRight': ('RightToeBase', 'RightToeBase')}

def rig(name, mesh, pelvis, chains, bones):
    missing = {bone for chain in chains.values() for bone in chain if bone not in bones}
    if missing:
        raise RuntimeError('Missing retarget bones: ' + str(missing))
    asset = create(name, u.IKRigDefinition, u.IKRigDefinitionFactory())
    ctl = u.IKRigController.get_controller(asset)
    ctl.set_skeletal_mesh(mesh)
    ctl.set_retarget_root(pelvis)
    existing = {str(chain.chain_name) for chain in ctl.get_retarget_chains()}
    for name, (start, end) in chains.items():
        if name not in existing:
            ctl.add_retarget_chain(name, start, end, '')
    save(asset)
    return asset

src = rig('IK_Khaimera', source, 'pelvis', source_chains, source_bones)
dst = rig('IK_Mutant3_Khaimera', target, 'Hips', target_chains, target_bones)
rtg = create('RTG_Khaimera_Mutant3', u.IKRetargeter, u.IKRetargetFactory())
ctl = u.IKRetargeterController.get_controller(rtg)
ctl.set_ik_rig(u.RetargetSourceOrTarget.SOURCE, src)
ctl.set_ik_rig(u.RetargetSourceOrTarget.TARGET, dst)
ctl.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE, source)
ctl.set_preview_mesh(u.RetargetSourceOrTarget.TARGET, target)
if ctl.get_num_retarget_ops() == 0:
    ctl.add_default_ops()
ctl.auto_map_chains(u.AutoMapChainType.EXACT, True)
pose = ctl.create_retarget_pose('Khaimera_Aligned', u.RetargetSourceOrTarget.TARGET)
ctl.set_current_retarget_pose(pose, u.RetargetSourceOrTarget.TARGET)
ctl.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
save(rtg)

clips, report = [], {}
opts = u.AnimPoseEvaluationOptions()
opts.set_editor_property('evaluation_type', u.AnimDataEvalType.RAW)
opts.set_editor_property('optional_skeletal_mesh', source)
for name in NAMES:
    clip = u.load_asset(BASE + '/Animations/' + name)
    if not isinstance(clip, u.AnimSequence):
        raise RuntimeError('Missing animation: ' + name)
    additive = str(clip.get_editor_property('additive_anim_type'))
    if 'NONE' not in additive:
        raise RuntimeError('Non-additive source required: ' + name + ' ' + additive)
    duration = clip.get_play_length()
    samples = []
    for i in range(round(duration * 60) + 1):
        time = min(duration, i / 60)
        p = u.AnimPoseExtensions.get_anim_pose_at_time(clip, time, opts)
        frame = {'time': time}
        for bone in ['root', 'pelvis', 'head', 'hand_l', 'hand_r', 'foot_l', 'foot_r', 'ball_l', 'ball_r']:
            t = u.AnimPoseExtensions.get_bone_pose(p, bone, u.AnimPoseSpaces.WORLD)
            frame[bone] = [t.translation.x, t.translation.y, t.translation.z]
        samples.append(frame)
    report[name] = {'asset': clip.get_path_name(), 'seconds': duration, 'additive': additive, 'samples': samples}
    clips.append(clip)
    export(clip, 'source_fbx')
(ROOT / 'source_motion.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
# A preview mesh is unnecessary for animation retargeting. Skeletal mesh FBX
# export requires a render resource and cannot run with NullRHI.

params = u.IKRetargetBatchOperationInputs()
params.assets_to_retarget = [LIB.find_asset_data(a.get_path_name()) for a in clips]
params.source_mesh = source
params.target_mesh = target
params.ik_retarget_asset = rtg
params.prefix = 'A_Mutant3_KhaiRaw_'
params.target_path = DEST + '/Raw'
params.include_referenced_assets = False
params.overwrite_existing_files = True
results = u.IKRetargetBatchOperation.run_batch_retarget(params)
delivery = {}
for data in results:
    anim = data.get_asset()
    if not isinstance(anim, u.AnimSequence):
        continue
    anim.set_preview_skeletal_mesh(target)
    anim.set_editor_property('enable_root_motion', False)
    save(anim)
    export(anim, 'native_retarget')
    delivery[anim.get_name()] = {'asset': anim.get_path_name(), 'seconds': anim.get_play_length()}
if len(delivery) != len(clips):
    raise RuntimeError('Incomplete retarget operation: ' + str(len(delivery)))
(ROOT / 'native_retarget.json').write_text(json.dumps(delivery, indent=2), encoding='utf-8')
u.log('MUTANT3_KHAIMERA_RETARGET_COMPLETE ' + str(len(delivery)))
