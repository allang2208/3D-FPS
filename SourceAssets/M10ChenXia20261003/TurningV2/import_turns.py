"""Import four phase-synchronous turns and bind the dedicated M10 animation class."""
from pathlib import Path
import json,sys,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2]
DEST='/Game/Monsters/M10Mawcrawler';REV='M10TurningV2_20261003'
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale
lib=u.EditorAssetLibrary;tools=u.AssetToolsHelpers.get_asset_tools()
report={'revision':REV,'saved':[],'runtime_tested':False,'preview_rendered':False}
def receipt(): (ROOT/'asset_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def save(asset):
    if not lib.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());receipt()
def load(path):
    obj=u.load_asset(path)
    if obj is None:raise RuntimeError('Required asset missing: '+path)
    return obj
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if any(p.get_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserving unsaved M10 packages')
if not hasattr(u,'M10AnimInstance'):raise RuntimeError('The new native module must be built before binding assets')
report['stage']='importing';receipt()
cvar='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(cvar)
try:
    u.SystemLibrary.execute_console_command(None,cvar+' 0')
    mesh=load(DEST+'/SK_M10_Mawcrawler');skeleton=mesh.get_editor_property('skeleton')
    contract=json.loads((ROOT/'turn_contract.json').read_text(encoding='utf-8'));clips={}
    for role,row in contract['clips'].items():
        name='A_M10_'+role+'_V2';folder=DEST+'/Animations/TurningV2';path=folder+'/'+name
        clip=u.load_asset(path) if lib.does_asset_exist(path) else None
        if clip is not None and lib.get_metadata_tag(clip,'M10.TurningRevision')!=REV:raise RuntimeError('Preserving unowned asset '+path)
        if clip is None:
            op=u.FbxImportUI();op.automated_import_should_detect_type=False;op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
            op.import_as_skeletal=True;op.import_mesh=False;op.import_animations=True;op.import_materials=False;op.import_textures=False;op.skeleton=skeleton
            data=op.anim_sequence_import_data;data.set_editor_property('use_default_sample_rate',False);data.set_editor_property('custom_sample_rate',30)
            data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME);data.set_editor_property('remove_redundant_keys',False)
            task=u.AssetImportTask();task.filename=row['file'];task.destination_path=folder;task.destination_name=name
            task.options=op;task.automated=True;task.save=False;task.replace_existing=False;tools.import_asset_tasks([task]);clip=load(path)
            lib.set_metadata_tag(clip,'M10.TurningRevision',REV)
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',False);clip.set_editor_property('rate_scale',1.)
        clip.set_preview_skeletal_mesh(mesh)
        report.setdefault('root_unit_adaptation',{})[role]=match_bind_root_scale(clip,mesh)
        save(clip);clips[role]=clip
    bp=load(DEST+'/BP_M10Mawcrawler');u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    for prop,role in [('curve_left_clip','CurveLeft'),('curve_right_clip','CurveRight'),('pivot_left_clip','PivotLeft'),('pivot_right_clip','PivotRight')]:cdo.set_editor_property(prop,clips[role])
    for key,value in [('slow_turn_angle',30.),('pivot_start_angle',70.),('pivot_finish_angle',25.),('moving_turn_speed',24.),('pivot_turn_speed',20.),('turn_acceleration',65.),('bite_facing_angle',15.)]:cdo.set_editor_property(key,value)
    component=cdo.get_editor_property('mesh');component.set_anim_instance_class(u.M10AnimInstance.static_class())
    # Native component subtype must be present before saving this Blueprint.
    movement=cdo.get_editor_property('character_movement')
    if not isinstance(movement,u.M10MovementComponent):raise RuntimeError('M10 Blueprint has stale movement component type')
    lib.set_metadata_tag(bp,'M10.TurningRevision',REV);save(bp)
    report.update(stage='assets_saved',blueprint=bp.get_path_name(),animation_class=str(component.get_editor_property('anim_class')),movement_class=movement.get_class().get_name(),old_walk_unchanged=True)
    receipt();u.log('M10_TURN_ASSETS_SAVED')
except Exception:
    report.update(stage='production_failed',error=traceback.format_exc());receipt();raise
finally:u.SystemLibrary.execute_console_command(None,cvar+' '+str(old))
