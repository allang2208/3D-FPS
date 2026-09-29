"""Read active donor attacks and bake two native UE retargets for Spitter only."""
import unreal as u
import json, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEST = '/Game/Monsters/SpitterZombie'
FOLDER = DEST+'/Rig/AttackVariantsV13'
RAW = DEST+'/RetargetedRaw/AttackVariantsV13'
LIB = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
if os.environ.get('SPITTER_HEADLESS') != '1':
    level = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():
        raise RuntimeError('PIE is active; preserving the current session')
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(FOLDER) or p.startswith(RAW) for p in dirty):
    raise RuntimeError('Unsaved edits exist in the new attack production folders')
target = u.load_asset(DEST+'/SK_SpitterZombie')
fat = u.get_default_object(u.FatZombie)
nurse_bp = u.load_asset('/Game/Monsters/NurseZombie/BP_NurseZombie')
nurse = u.get_default_object(nurse_bp.generated_class())
donors = {'FatScratch': fat, 'NurseDownSwing': nurse}
target_chains = {
    'Spine': ('Spine02', 'Spine'), 'Neck': ('neck', 'neck'), 'Head': ('Head', 'Head'),
    'ClavicleLeft': ('LeftShoulder', 'LeftShoulder'), 'ClavicleRight': ('RightShoulder', 'RightShoulder'),
    'ArmLeft': ('LeftArm', 'LeftHand'), 'ArmRight': ('RightArm', 'RightHand'),
    'LegLeft': ('LeftUpLeg', 'LeftFoot'), 'LegRight': ('RightUpLeg', 'RightFoot'),
    'ToeLeft': ('LeftToeBase', 'LeftToeBase'), 'ToeRight': ('RightToeBase', 'RightToeBase')}
nurse_chains = {
    'Spine': ('spine_01', 'spine_05'), 'Neck': ('neck_01', 'neck_02'), 'Head': ('head', 'head'),
    'ClavicleLeft': ('clavicle_l', 'clavicle_l'), 'ClavicleRight': ('clavicle_r', 'clavicle_r'),
    'ArmLeft': ('upperarm_l', 'hand_l'), 'ArmRight': ('upperarm_r', 'hand_r'),
    'LegLeft': ('thigh_l', 'foot_l'), 'LegRight': ('thigh_r', 'foot_r'),
    'ToeLeft': ('ball_l', 'ball_l'), 'ToeRight': ('ball_r', 'ball_r')}

def save(asset):
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed: '+asset.get_path_name())

def create(name, cls, factory):
    return u.load_asset(FOLDER+'/'+name) or TOOLS.create_asset(name, FOLDER, cls, factory)

def ik(name, mesh, root, chains):
    asset = create(name, u.IKRigDefinition, u.IKRigDefinitionFactory())
    ctl = u.IKRigController.get_controller(asset)
    ctl.set_skeletal_mesh(mesh)
    ctl.set_retarget_root(root)
    existing = {str(c.chain_name) for c in ctl.get_retarget_chains()}
    for name, (start, end) in chains.items():
        if name not in existing:
            ctl.add_retarget_chain(name, start, end, '')
    save(asset)
    return asset

dst = ik('IK_SpitterAttackV13', target, 'Hips', target_chains)
output = ROOT/'Native'
output.mkdir(parents=True, exist_ok=True)
report = {}
for role, cdo in donors.items():
    mesh = cdo.get_editor_property('visual_mesh')
    clip = cdo.get_editor_property('attack_clip')
    if not mesh or not clip:
        raise RuntimeError('Active donor assets missing: '+role)
    src = ik('IK_'+role, mesh, 'Hips' if role == 'FatScratch' else 'pelvis',
             target_chains if role == 'FatScratch' else nurse_chains)
    rtg = create('RTG_'+role+'_Spitter', u.IKRetargeter, u.IKRetargetFactory())
    ctl = u.IKRetargeterController.get_controller(rtg)
    ctl.set_ik_rig(u.RetargetSourceOrTarget.SOURCE, src)
    ctl.set_ik_rig(u.RetargetSourceOrTarget.TARGET, dst)
    ctl.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE, mesh)
    ctl.set_preview_mesh(u.RetargetSourceOrTarget.TARGET, target)
    if ctl.get_num_retarget_ops() == 0:
        ctl.add_default_ops()
    ctl.auto_map_chains(u.AutoMapChainType.EXACT, True)
    pose = ctl.create_retarget_pose('SpitterAligned', u.RetargetSourceOrTarget.TARGET)
    ctl.set_current_retarget_pose(pose, u.RetargetSourceOrTarget.TARGET)
    ctl.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
    save(rtg)
    params = u.IKRetargetBatchOperationInputs()
    params.assets_to_retarget = [LIB.find_asset_data(clip.get_path_name())]
    params.source_mesh, params.target_mesh, params.ik_retarget_asset = mesh, target, rtg
    params.search, params.replace = clip.get_name(), 'A_SpitterV13Raw_'+role
    params.target_path = RAW
    params.include_referenced_assets = False
    params.overwrite_existing_files = True
    results = u.IKRetargetBatchOperation.run_batch_retarget(params)
    result = next((a.get_asset() for a in results if isinstance(a.get_asset(), u.AnimSequence)), None)
    if result is None:
        raise RuntimeError('Retarget failed: '+role)
    result.set_preview_skeletal_mesh(target)
    result.set_editor_property('enable_root_motion', False)
    save(result)
    task = u.AssetExportTask()
    task.object, task.filename = result, str(output/(result.get_name()+'.fbx'))
    task.automated, task.prompt, task.replace_identical = True, False, True
    task.exporter = u.AnimSequenceExporterFBX()
    options = u.FbxExportOption()
    options.set_editor_property('export_preview_mesh', False)
    task.options = options
    if not u.Exporter.run_asset_export_task(task):
        raise RuntimeError('Export failed: '+role)
    report[role] = dict(asset=result.get_path_name(), seconds=result.get_play_length(), fbx=task.filename,
        source=clip.get_path_name(), source_mesh=mesh.get_path_name(),
        contact_seconds=cdo.get_editor_property('contact_time'), contact_end_seconds=cdo.get_editor_property('contact_end'),
        donor_recovery_seconds=cdo.get_editor_property('recovery_time'),
        provenance='Existing project FatZombie Mesh2Motion CC0 attack' if role=='FatScratch' else 'User-provided ZombieFemale asset pack; local reuse only')
(ROOT/'native.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('SPITTER_ATTACK_VARIANTS_RETARGETED '+json.dumps(report, ensure_ascii=False))
