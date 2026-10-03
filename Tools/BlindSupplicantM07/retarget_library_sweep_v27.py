"""Bake a clean native UE retarget of ZombieAnimationPack Attack_D for M07."""
import json
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001/LibrarySweepV27'
OUT = ROOT/'Native'
OUT.mkdir(parents=True, exist_ok=True)
DEST = '/Game/Monsters/BlindSupplicantM07'
RIG = DEST+'/Rig/LibrarySweepV27'
RAW = DEST+'/AnimationsLibrarySweepV27Raw'
LIB, TOOLS = u.EditorAssetLibrary, u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    level = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():
        raise RuntimeError('M07_V27_PIE_PRESERVED: finish the current play session before asset production.')
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(RIG) or p.startswith(RAW) for p in dirty):
    raise RuntimeError('Unsaved edits in V27 production folders were preserved.')
source = u.load_asset('/Game/ZombieAnimationPack/Demo/EpicContent/Mannequin_UE5/Meshes/SK_Manny_Simple')
target = u.load_asset(DEST+'/SK_M07_BodyMotionV18')
clip = u.load_asset('/Game/ZombieAnimationPack/Animations/Mannequin_UE5/anim_Attack_D')
chains = {'Spine': ('spine_01','spine_05'), 'Neck': ('neck_01','neck_02'), 'Head': ('head','head'),
    'ClavicleLeft': ('clavicle_l','clavicle_l'), 'ClavicleRight': ('clavicle_r','clavicle_r'),
    'ArmLeft': ('upperarm_l','hand_l'), 'ArmRight': ('upperarm_r','hand_r'),
    'LegLeft': ('thigh_l','foot_l'), 'LegRight': ('thigh_r','foot_r')}


def save(asset):
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('V27 save failed: '+asset.get_path_name())


def create(name, cls, factory):
    return u.load_asset(RIG+'/'+name) or TOOLS.create_asset(name, RIG, cls, factory)


def ik(name, mesh):
    asset = create(name, u.IKRigDefinition, u.IKRigDefinitionFactory())
    ctl = u.IKRigController.get_controller(asset)
    ctl.set_skeletal_mesh(mesh)
    ctl.set_retarget_root('pelvis')
    existing = {str(c.chain_name) for c in ctl.get_retarget_chains()}
    for name, (start, end) in chains.items():
        if name not in existing:
            ctl.add_retarget_chain(name, start, end, '')
    save(asset)
    return asset


src, dst = ik('IK_ZombiePack_M07Source', source), ik('IK_M07_LibrarySweep', target)
rtg = create('RTG_ZombiePack_M07_V27', u.IKRetargeter, u.IKRetargetFactory())
ctl = u.IKRetargeterController.get_controller(rtg)
ctl.set_ik_rig(u.RetargetSourceOrTarget.SOURCE, src)
ctl.set_ik_rig(u.RetargetSourceOrTarget.TARGET, dst)
ctl.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE, source)
ctl.set_preview_mesh(u.RetargetSourceOrTarget.TARGET, target)
if ctl.get_num_retarget_ops() == 0:
    ctl.add_default_ops()
ctl.auto_map_chains(u.AutoMapChainType.EXACT, True)
for index in range(ctl.get_num_retarget_ops()):
    op = ctl.get_op_controller(index)
    if isinstance(op, u.IKRetargetRootMotionController):
        # M07 has pelvis as its actual skeleton root and no separate ground
        # root. Copying Manny's ground root here overwrites the retargeted
        # pelvis with Z=0 and discards its body rotation. Keep the pelvis op.
        ctl.set_retarget_op_enabled(index, False)
    if isinstance(op, u.IKRetargetFKChainsController):
        settings = op.get_settings()
        chain_settings = list(settings.chains_to_retarget)
        for chain in chain_settings:
            # Both characters have the same three main arm joints. Preserve
            # each corresponding joint's rotation despite different lengths.
            if str(chain.target_chain_name) in ('ArmLeft','ArmRight','LegLeft','LegRight'):
                chain.rotation_mode = u.FKChainRotationMode.ONE_TO_ONE
        settings.chains_to_retarget = chain_settings
        op.set_settings(settings)
pose = ctl.create_retarget_pose('M07_LibraryAligned', u.RetargetSourceOrTarget.TARGET)
ctl.set_current_retarget_pose(pose, u.RetargetSourceOrTarget.TARGET)
ctl.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
save(rtg)
params = u.IKRetargetBatchOperationInputs()
params.assets_to_retarget = [LIB.find_asset_data(clip.get_path_name())]
params.source_mesh, params.target_mesh, params.ik_retarget_asset = source, target, rtg
params.search, params.replace = clip.get_name(), 'A_M07_LibraryRaw_Attack_D'
params.target_path = RAW
params.include_referenced_assets = False
params.overwrite_existing_files = True
results = u.IKRetargetBatchOperation.run_batch_retarget(params)
result = next((a.get_asset() for a in results if isinstance(a.get_asset(), u.AnimSequence)), None)
if not result:
    raise RuntimeError('Native M07 retarget did not produce an animation.')
result.set_preview_skeletal_mesh(target)
result.set_editor_property('enable_root_motion', False)
result.set_editor_property('force_root_lock', False)
save(result)
task = u.AssetExportTask()
task.object, task.filename = result, str(OUT/(result.get_name()+'.fbx'))
task.automated, task.prompt, task.replace_identical = True, False, True
task.exporter = u.AnimSequenceExporterFBX()
options = u.FbxExportOption()
options.set_editor_property('export_preview_mesh', False)
task.options = options
if not u.Exporter.run_asset_export_task(task):
    raise RuntimeError('Native retarget FBX export failed.')
report = dict(source=clip.get_path_name(), source_mesh=source.get_path_name(), target_mesh=target.get_path_name(),
    raw_asset=result.get_path_name(), raw_fbx=task.filename, duration_seconds=result.get_play_length(),
    retargeter=rtg.get_path_name(), retarget_method='Native UE IK Rig / IK Retargeter; complete source body and limb animation',
    limb_rotation_mode='OneToOne', root_policy='PelvisRetarget_NoGroundRootCopy',
    authoring_only=True, formal_blueprint_changed=False, rendered=False, tested=False,
    provenance='Existing locally imported ZombieAnimationPack; local project reuse only')
(ROOT/'native_retarget_v27.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('M07_V27_NATIVE_RETARGET_SAVED '+str(ROOT/'native_retarget_v27.json'))
