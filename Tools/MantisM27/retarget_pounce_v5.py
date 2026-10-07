"""Read and retarget existing licensed Mutant3 locomotion for M27 authoring."""
from pathlib import Path
import json
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/PounceV5')
ROOT.mkdir(parents=True, exist_ok=True)
DEST = '/Game/Monsters/MantisM27/PounceV5/Raw'
L = u.EditorAssetLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
        raise RuntimeError('Requested end of PIE for asset authoring; rerun after it has ended. Editor stays open.')
source = u.load_asset('/Game/Monsters/Mutant3Meshy/KhaimeraV2/SK_Mutant3_Claw')
target = u.load_asset('/Game/Monsters/MantisM27/BindingV2/SK_MantisM27_BindingV2')
retargeter = u.load_asset('/Game/Monsters/MantisM27/ClawV3/Rig/RTG_Mutant3_M27_ClawV3')
if not all([source, target, retargeter]):
    raise RuntimeError('Existing M27 anatomical retarget inputs unavailable')
component = u.new_object(u.SkeletalMeshComponent)
component.set_skeletal_mesh_asset(target)
bones = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
options = u.AnimPoseEvaluationOptions()
options.evaluation_type = u.AnimDataEvalType.RAW
options.optional_skeletal_mesh = target
options.set_editor_property('should_retarget', False)
options.set_editor_property('extract_root_motion', False)

def transform(t):
    p, q = t.translation, t.rotation
    return {'p': [p.x, p.y, p.z], 'q': [q.w, q.x, q.y, q.z]}

report = {'fps': 60, 'retargeter': retargeter.get_path_name(), 'clips': {}, 'tested': False}
for role in ['PounceWindup', 'PounceFlight', 'PounceLand']:
    clip = u.load_asset('/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_' + role)
    if not clip:
        raise RuntimeError('Missing donor ' + role)
    params = u.IKRetargetBatchOperationInputs()
    params.assets_to_retarget = [L.find_asset_data(clip.get_path_name())]
    params.source_mesh, params.target_mesh, params.ik_retarget_asset = source, target, retargeter
    params.search, params.replace = clip.get_name(), 'A_M27_Raw_' + role
    params.target_path = DEST
    params.include_referenced_assets = False
    params.overwrite_existing_files = True
    result = next((a.get_asset() for a in u.IKRetargetBatchOperation.run_batch_retarget(params)
                   if isinstance(a.get_asset(), u.AnimSequence)), None)
    if not result:
        raise RuntimeError('Retarget failed for ' + role)
    result.set_preview_skeletal_mesh(target)
    result.set_editor_property('enable_root_motion', False)
    result.set_editor_property('force_root_lock', False)
    if not L.save_loaded_asset(result, False):
        raise RuntimeError('Cannot save run authoring input')
    length = result.get_play_length()
    frames = []
    for i in range(round(length * 60) + 1):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(result, min(i / 60, length), options)
        frames.append({b: transform(u.AnimPoseExtensions.get_bone_pose(pose, b, u.AnimPoseSpaces.WORLD)) for b in bones})
    reference = {b: transform(u.AnimPoseExtensions.get_ref_bone_pose(pose, b, u.AnimPoseSpaces.WORLD)) for b in bones}
    report['clips'][role] = {'source': clip.get_path_name(), 'raw': result.get_path_name(),
                             'seconds': length, 'frames': frames, 'reference': reference}
defaults = u.get_default_object(u.load_asset('/Game/Monsters/MantisM27/BP_MantisM27').generated_class())
report['previous'] = {}
for key in ['visual_mesh', 'walk_clip', 'walk_speed', 'source_move_speed', 'cloak_move_speed']:
    value = defaults.get_editor_property(key)
    report['previous'][key] = value.get_path_name() if isinstance(value, u.Object) else value
(ROOT / 'native_pounce_poses.json').write_text(json.dumps(report, ensure_ascii=False), encoding='utf-8')
u.log('M27_POUNCE_V5_AUTHORING_INPUTS_SAVED')
