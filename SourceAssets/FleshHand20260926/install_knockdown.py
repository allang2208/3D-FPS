"""Import ten authored clips and persist both hand Blueprints after the native build."""
from pathlib import Path
import json, math, shutil, sys
import unreal as u

ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1];OUT=ROOT/'Knockdown'
DEST='/Game/Monsters/FleshHand';REV='HandKnockdown20260927V1'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong UE project')
source=json.loads((OUT/'authoring.json').read_text(encoding='utf-8'))
bindings={'launch_palm_clip':'KnockupStart','launch_back_clip':'KnockupStartBack',
          'air_palm_clip':'KnockupAir','air_back_clip':'KnockupAirBack',
          'land_palm_clip':'LandPalm','land_back_clip':'LandBack',
          'down_palm_clip':'DownPalm','down_back_clip':'DownBack',
          'get_up_palm_clip':'GetUpPalm','get_up_back_clip':'GetUpBack'}
blueprint_paths=[DEST+'/BP_FleshHand',DEST+'/BP_FleshHandMinion']
paths=blueprint_paths+[DEST+'/Animations/A_FleshHand_'+role for role in bindings.values()]
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths):raise RuntimeError('Preserving unsaved hand assets: '+str(sorted(dirty.intersection(paths))))
report={'revision':REV,'state':'importing','saved':[],'animations':{},'root_units':{},'characters':{},
        'runtime_tested':False,'rendered':False,'game_started':False,'physics':'one character capsule; no ragdoll'}

def record():(OUT/'ue_installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Required asset missing: '+path)
    return asset
def save(asset):
    LIB.set_metadata_tag(asset,'FleshHand.Knockdown',REV)
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());record()

for path in paths:
    if not LIB.does_asset_exist(path):continue
    asset=load(path)
    if path not in blueprint_paths and LIB.get_metadata_tag(asset,'FleshHand.Knockdown')!=REV:
        raise RuntimeError('Independent animation asset: '+path)
    file=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup=(ROOT.parents[1]/'trash/monster-hands-20260927/SourceAssets/FleshHand20260926/Knockdown/BeforeKnockdown')/file.relative_to(PROJECT/'Content')
    if file.exists() and not backup.exists():
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,backup)
blueprints=[]
for path in blueprint_paths:
    bp=load(path);u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class());component=cdo.get_editor_property('knockdown')
    if component is None:raise RuntimeError('Native hand knockdown component is unavailable; build the ordinary DLL first')
    for prop in bindings:component.get_editor_property(prop)
    blueprints.append((bp,cdo,component))
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
        task.automated=True;task.replace_existing=True;task.save=False;task.options=options
        TOOLS.import_asset_tasks([task])
        if not task.imported_object_paths:raise RuntimeError('No imported animation: '+role)
        clip=load(DEST+'/Animations/A_FleshHand_'+role)
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',False);clip.set_editor_property('rate_scale',1.)
        clip.set_preview_skeletal_mesh(mesh);report['root_units'][role]=match_bind_root_scale(clip,mesh)
        save(clip);report['animations'][role]=clip.get_path_name()
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))

# Derive the broad fall capsule from the authored skin footprint, including the
# side-roll recovery; no per-frame mesh bounds scan is required during gameplay.
radius=0.
for row in source['clips'].values():
    for low,high in row['support_bounds_m']:
        x=max(abs(low[0]),abs(high[0]));y=max(abs(low[1]),abs(high[1]))
        radius=max(radius,math.hypot(x,y))
for bp,cdo,component in blueprints:
    bp.modify();cdo.modify();component.modify()
    for prop,role in bindings.items():component.set_editor_property(prop,load(report['animations'][role]))
    minion=bool(cdo.get_editor_property('minion'))
    scale=cdo.get_editor_property('mesh').get_editor_property('relative_scale3d')
    settings={'enabled':True,'launch_scale':1. if minion else .7,
              'ground_hold_seconds':.45 if minion else .65,
              'fall_collision_radius':radius*100*max(scale.x,scale.y,scale.z)+3.}
    for prop,value in settings.items():component.set_editor_property(prop,value)
    save(bp)
    report['characters'][bp.get_name()]={'component':component.get_path_name(),'settings':settings,'bindings':bindings}
report.update(state='assets_saved_and_bound',animation_count=len(report['animations']),authoring_radius_m=radius,
              entry_points=['RuneSword heavy hit','Meteor explosion','MonsterCombat.ReceiveKnockdown'])
record()
receipt_path=ROOT/'ue_installation.json'
receipt=json.loads(receipt_path.read_text(encoding='utf-8'));receipt['knockdown']=report
receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('FLESHHAND_KNOCKDOWN_INSTALL_COMPLETE '+str(OUT/'ue_installation.json'))
