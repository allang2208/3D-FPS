"""Import the six-second emission performance and save the 12-second cooldown."""
from pathlib import Path
import json,sys,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2]
DEST='/Game/Monsters/M10Mawcrawler/RearGasV7';REV='M10RearGasV7_20261003'
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale
E=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
report={'revision':REV,'saved':[],'game_tested':False,'preview_rendered':False}
def receipt():(ROOT/'asset_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf8')
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing '+path)
    return asset
def save(asset):
    E.set_metadata_tag(asset,'M10.RearGasRevision',REV)
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());receipt()
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Preserving active PIE')
if any(str(p.get_name()).startswith('/Game/Monsters/M10Mawcrawler') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserving unsaved M10 assets')
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    mesh=load('/Game/Monsters/M10Mawcrawler/SurfaceRigV5/SK_M10_SurfaceRig_V5')
    skeleton=mesh.get_editor_property('skeleton');path=DEST+'/A_M10_RearGas_V7'
    if E.does_asset_exist(path):
        clip=load(path)
        if E.get_metadata_tag(clip,'M10.RearGasRevision')!=REV:raise RuntimeError('Preserving unowned '+path)
    else:
        u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
        contract=json.loads((ROOT/'export_contract.json').read_text(encoding='utf8'))
        op=u.FbxImportUI();op.automated_import_should_detect_type=False;op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        op.import_as_skeletal=True;op.import_mesh=False;op.import_animations=True;op.import_materials=False;op.import_textures=False;op.skeleton=skeleton
        data=op.anim_sequence_import_data;data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',30)
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME);data.set_editor_property('remove_redundant_keys',False)
        task=u.AssetImportTask();task.filename=contract['animation_file'];task.destination_path=DEST;task.destination_name='A_M10_RearGas_V7'
        task.options=op;task.automated=True;task.save=False;task.replace_existing=False;TOOLS.import_asset_tasks([task]);clip=load(path)
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',False);clip.set_editor_property('rate_scale',1.)
    clip.set_preview_skeletal_mesh(mesh);report['root_unit_adaptation']=match_bind_root_scale(clip,mesh);save(clip);save(skeleton)
    bp=load('/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler');u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class());cdo.set_editor_property('rear_gas_clip',clip);cdo.set_editor_property('rear_gas_cooldown',12.)
    save(bp)
    report.update(stage='assets_saved',animation=clip.get_path_name(),blueprint=bp.get_path_name(),cooldown_seconds=12,emission_seconds=6,total_animation_seconds=8,
        smoke_lifetime='inherits SlagBlackMist: 8 seconds hold + 1.5 seconds fade',direction='nearest front/rear end independent of cooldown; rear target holds position',reuses_green_fx='/Game/Monsters/M10Mawcrawler/RearGasV6/NS_M10RearPoisonGas')
    receipt();u.log('M10_REAR_GAS_V7_ASSETS_SAVED')
except Exception:
    report.update(stage='production_failed',error=traceback.format_exc());receipt();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
