"""Import two upright walking loops and bind only MoveClip on the hand Blueprints."""
from pathlib import Path
import json,shutil,sys
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1];OUT=ROOT/'Locomotion'
DEST='/Game/Monsters/FleshHand';REV='FleshHandLocomotion20260927V1'
E=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE before importing')
source=json.loads((OUT/'authoring.json').read_text(encoding='utf-8'))
bindings={'BP_FleshHand':'WalkWeighted','BP_FleshHandMinion':'WalkScurry'}
paths=[DEST+'/'+name for name in bindings]+[DEST+'/Animations/A_FleshHand_'+role for role in source['clips']]
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths):raise RuntimeError('Preserving unsaved target hand assets: '+str(sorted(dirty.intersection(paths))))
report={'state':'importing','saved':[],'revision':REV,'animations':{},'bindings':{},'root_units':{},'runtime_tested':False,'rendered':False}
def record():(OUT/'installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
    value=u.load_asset(path)
    if not value:raise RuntimeError('Missing '+path)
    return value
def save(value):
    E.set_metadata_tag(value,'FleshHand.Locomotion',REV)
    if not E.save_loaded_asset(value,False):raise RuntimeError('Save failed: '+value.get_path_name())
    report['saved'].append(value.get_path_name());record()
for path in paths:
    if E.does_asset_exist(path):
        value=load(path)
        if '/Animations/' in path and E.get_metadata_tag(value,'FleshHand.Locomotion')!=REV:raise RuntimeError('Unowned animation: '+path)
        file=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset');backup=(ROOT.parents[1]/'trash/monster-hands-20260927/SourceAssets/FleshHand20260926/Locomotion/BeforeAssets')/file.relative_to(PROJECT/'Content')
        if file.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,backup)
mesh=load(DEST+'/SK_FleshHand_Green');skeleton=mesh.get_editor_property('skeleton')
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
        task.automated=True;task.replace_existing=True;task.save=False;task.options=options;TOOLS.import_asset_tasks([task])
        if not task.imported_object_paths:raise RuntimeError('No imported clip: '+role)
        clip=load(DEST+'/Animations/A_FleshHand_'+role);clip.set_editor_property('enable_root_motion',False)
        clip.set_editor_property('force_root_lock',False);clip.set_editor_property('rate_scale',1.);clip.set_preview_skeletal_mesh(mesh)
        report['root_units'][role]=match_bind_root_scale(clip,mesh);save(clip);report['animations'][role]=clip.get_path_name()
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
for name,role in bindings.items():
    bp=load(DEST+'/'+name);cdo=u.get_default_object(bp.generated_class());bp.modify();cdo.modify()
    cdo.set_editor_property('move_clip',load(report['animations'][role]));save(bp)
    report['bindings'][name]={'move_clip':report['animations'][role],
        'walk_speed_unchanged':cdo.get_editor_property('walk_speed'),'animation_reference_speed_unchanged':cdo.get_editor_property('animation_walk_speed')}
report['state']='assets_saved_and_bound';record();print('FLESHHAND_LOCOMOTION_SAVED '+str(OUT/'installation.json'))
