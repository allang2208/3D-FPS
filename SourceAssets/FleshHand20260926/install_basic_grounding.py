"""Replace only six bound basic hand clips with their corrected support tracks."""
from pathlib import Path
import json
import shutil
import sys
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
OUT=ROOT/'GroundingRepair'
DEST='/Game/Monsters/FleshHand'
REV='RootLocalSupport20260927V1'
ROLES=('Idle','Slam','GrandSlam','Hit','Dizzy','Death')
E=u.EditorAssetLibrary
TOOLS=u.AssetToolsHelpers.get_asset_tools()
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale

if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():
    raise RuntimeError('Wrong project')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('End PIE before replacing the six basic hand clips')
source=json.loads((OUT/'authoring.json').read_text(encoding='utf-8'))
if source['state']!='six_actions_baked_and_exported' or set(source['clips'])!=set(ROLES):
    raise RuntimeError('The six-clip grounding bake is incomplete')
paths=[DEST+'/Animations/A_FleshHand_'+role for role in ROLES]
protected=paths+[DEST+'/SK_FleshHand_Green',DEST+'/SK_FleshHand_Green_Skeleton']
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(protected):
    raise RuntimeError('Preserving unsaved target assets: '+str(sorted(dirty.intersection(protected))))
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing required asset: '+path)
    return obj
mesh=load(DEST+'/SK_FleshHand_Green')
skeleton=mesh.get_editor_property('skeleton')
for path in paths:
    clip=load(path)
    if clip.get_editor_property('skeleton')!=skeleton:
        raise RuntimeError('Target clip uses a different skeleton: '+path)
    file=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup=(ROOT.parents[1]/'trash/monster-hands-20260927/SourceAssets/FleshHand20260926/GroundingRepair/BeforeAssets')/file.relative_to(PROJECT/'Content')
    if file.exists() and not backup.exists():
        backup.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(file,backup)

report={'revision':REV,'state':'importing','saved':[],'animations':{},'root_units':{},
        'binding_method':'replace existing referenced animation packages in place',
        'runtime_tested':False,'rendered':False}
def record():
    (OUT/'installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
record()
previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    for role in ROLES:
        row=source['clips'][role]
        options=u.FbxImportUI()
        options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        options.import_mesh=False;options.import_animations=True;options.import_as_skeletal=True
        options.import_materials=False;options.import_textures=False;options.skeleton=skeleton
        data=options.anim_sequence_import_data
        data.set_editor_property('use_default_sample_rate',False)
        data.set_editor_property('custom_sample_rate',60)
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        data.set_editor_property('remove_redundant_keys',False)
        task=u.AssetImportTask()
        task.filename=row['file'];task.destination_path=DEST+'/Animations'
        task.destination_name='A_FleshHand_'+role
        task.automated=True;task.replace_existing=True;task.save=False;task.options=options
        TOOLS.import_asset_tasks([task])
        if not task.imported_object_paths:raise RuntimeError('No imported clip: '+role)
        clip=load(DEST+'/Animations/A_FleshHand_'+role)
        clip.set_editor_property('enable_root_motion',False)
        clip.set_editor_property('force_root_lock',False)
        clip.set_editor_property('rate_scale',1.)
        clip.set_preview_skeletal_mesh(mesh)
        report['root_units'][role]=match_bind_root_scale(clip,mesh)
        E.set_metadata_tag(clip,'FleshHand.Grounding',REV)
        if not E.save_loaded_asset(clip,False):raise RuntimeError('Save failed: '+clip.get_path_name())
        report['saved'].append(clip.get_path_name())
        report['animations'][role]={'asset':clip.get_path_name(),'seconds':clip.get_play_length()}
        record()
finally:
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
report['state']='six_corrected_animations_saved'
record()
print('HAND_BASIC_GROUNDING_SAVED '+json.dumps(report['animations']))
