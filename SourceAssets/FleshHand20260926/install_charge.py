"""Import three fist-charge clips and bind the main hand after the native build."""
from pathlib import Path
import json,shutil,sys
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1];OUT=ROOT/'Charge'
DEST='/Game/Monsters/FleshHand';REV='FistCharge20260927V1'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong UE project')
source=json.loads((OUT/'authoring.json').read_text(encoding='utf-8'))
report_revision=source.get('revision',REV)
blueprint_path=DEST+'/BP_FleshHand'
paths=[blueprint_path]+[DEST+'/Animations/A_FleshHand_'+role for role in source['clips']]
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths):raise RuntimeError('Preserving unsaved charge assets: '+str(sorted(dirty.intersection(paths))))
report={'revision':report_revision,'state':'importing','saved':[],'animations':{},'root_units':{},'runtime_tested':False,'rendered':False,'game_started':False}
def record():(OUT/'ue_installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Required asset missing: '+path)
    return asset
def save(asset):
    LIB.set_metadata_tag(asset,'FleshHand.Charge',REV)
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());record()
for path in paths:
    if LIB.does_asset_exist(path):
        asset=load(path)
        if path!=blueprint_path and LIB.get_metadata_tag(asset,'FleshHand.Charge')!=REV:raise RuntimeError('Independent charge asset: '+path)
        file=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset');backup=(ROOT.parents[1]/'trash/monster-hands-20260927/SourceAssets/FleshHand20260926/Charge')/('BeforeVisualPolishAssets' if report_revision!=REV else 'BeforeCharge')/file.relative_to(PROJECT/'Content')
        if file.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,backup)
mesh=load(DEST+'/SK_FleshHand_Green');skeleton=mesh.get_editor_property('skeleton')
bp=load(blueprint_path);cdo=u.get_default_object(bp.generated_class())
# Fail before importing if the native DLL still lacks the new reflected contract.
cdo.get_editor_property('charge_windup_clip')
record();previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    for role,row in source['clips'].items():
        options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        options.import_mesh=False;options.import_animations=True;options.import_as_skeletal=True
        options.import_materials=False;options.import_textures=False;options.skeleton=skeleton
        data=options.anim_sequence_import_data;data.set_editor_property('use_default_sample_rate',False)
        data.set_editor_property('custom_sample_rate',60);data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        data.set_editor_property('remove_redundant_keys',False)
        task=u.AssetImportTask();task.filename=row['file'];task.destination_path=DEST+'/Animations';task.destination_name='A_FleshHand_'+role
        task.automated=True;task.replace_existing=True;task.save=False;task.options=options
        TOOLS.import_asset_tasks([task])
        if not task.imported_object_paths:raise RuntimeError('No imported clip for '+role)
        clip=load(DEST+'/Animations/A_FleshHand_'+role)
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',False);clip.set_editor_property('rate_scale',1.)
        clip.set_preview_skeletal_mesh(mesh);report['root_units'][role]=match_bind_root_scale(clip,mesh)
        save(clip);report['animations'][role]=clip.get_path_name()
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
bp.modify();cdo.modify()
for prop,role in [('charge_windup_clip','ChargeWindup'),('charge_rush_clip','ChargeRush'),('charge_recover_clip','ChargeRecover')]:
    cdo.set_editor_property(prop,load(report['animations'][role]))
settings={'charge_min_range':450.,'charge_max_range':1100.,'charge_windup_seconds':1.2,'charge_cooldown':12.,
          'charge_speed':1100.,'charge_distance':1200.,'charge_damage_multiplier':3.,'charge_stun_seconds':2.,'charge_recover_seconds':.7,
          'charge_lead_strength':1.,'charge_max_lead_distance':450.}
for prop,value in settings.items():cdo.set_editor_property(prop,value)
save(bp)
report.update(state='assets_saved_and_bound',settings=settings,minion_behavior='unchanged; contact damage only')
record()
receipt=json.loads((ROOT/'ue_installation.json').read_text(encoding='utf-8'));receipt['charge_attack']=report
(ROOT/'ue_installation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('FLESHHAND_CHARGE_INSTALL_COMPLETE '+str(OUT/'ue_installation.json'))
