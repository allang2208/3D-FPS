"""Save M08 traversal action/configuration after the native traversal build.
Uses existing authored poses; does not launch PIE or perform a movement test.
"""
import json, shutil
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
OUT=PROJECT/'SourceAssets/Monsters/LurkerM08/TraversalV02_20261004'
OUT.mkdir(parents=True,exist_ok=True)
DEST='/Game/Monsters/LurkerM08'
REV='M08_SurfaceTraversalV02_20261004'
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
report={'revision':REV,'state':'saving','saved':[],'runtime_tested':False,'rendered':False}
def save(a):
    LIB.set_metadata_tag(a,'M08.TraversalRevision',REV)
    if not LIB.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    report['saved'].append(a.get_path_name())
def load(path):
    a=u.load_asset(path)
    if a is None:raise RuntimeError('Required M08 asset missing '+path)
    return a
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if p.get_name().startswith(DEST):raise RuntimeError('Preserving unsaved M08 asset '+p.get_name())
backup=OUT/'Before';backup.mkdir(exist_ok=True)
for relative in ['BP_LurkerM08.uasset','DA_M08_AnimationSet.uasset']:
    source=PROJECT/'Content/Monsters/LurkerM08'/relative
    if source.exists() and not (backup/relative).exists():shutil.copy2(source,backup/relative)

active_set=load(DEST+'/DA_M08_AnimationSet')
active_actions=active_set.get_editor_property('actions')
current_jump=active_actions.get('TraverseJump')
current_pounce=active_actions.get('AttackPounce')
if (current_jump and current_jump.sequence and current_pounce and current_pounce.sequence
        and current_jump.sequence.get_editor_property('skeleton')==active_set.reference_mesh.get_editor_property('skeleton')):
    # Preserve the authored jump on the current rig during movement reinstall.
    clip=current_jump.sequence;source=current_pounce.sequence
else:
    source=load(DEST+'/Animations/A_M08_AttackPounce')
    name='A_M08_TraverseJump';path=DEST+'/Animations/'+name
    if LIB.does_asset_exist(path):
        clip=load(path)
        if LIB.get_metadata_tag(clip,'M08.TraversalRevision')!=REV:raise RuntimeError('Preserving independent animation '+path)
    else:
        clip=TOOLS.duplicate_asset(name,DEST+'/Animations',source)
        if clip is None:raise RuntimeError('Could not save traversal jump action')
    save(clip)
dataset=load(DEST+'/DA_M08_AnimationSet')
actions=dataset.get_editor_property('actions')
action=u.QuadrupedTemplateAction()
for key,value in {'sequence':clip,'loop':False,'hold_last_pose':True,'terminal':False,
                  'blend_seconds':.12,'play_rate':1.,'contact_start_seconds':-1.,'contact_end_seconds':-1.}.items():
    action.set_editor_property(key,value)
actions['TraverseJump']=action
dataset.set_editor_property('actions',actions);save(dataset)

bp=load(DEST+'/BP_LurkerM08')
u.BlueprintEditorLibrary.compile_blueprint(bp)
cdo=u.get_default_object(bp.generated_class())
for key,value in {'climb_speed':180.,'jump_range':700.,'jump_height':500.,'surface_turn_speed':240.,
                  'pounce_min_range':145.,'pounce_max_range':700.,'animation_set':dataset}.items():
    cdo.set_editor_property(key,value)
save(bp)
report.update(state='traversal_assets_saved',blueprint=bp.get_path_name(),animation_set=dataset.get_path_name(),
    traversal_action=clip.get_path_name(),source_action=source.get_path_name(),
    physical_surface_navigation=True,ground_navmesh_required=False,
    no_damage_traversal_jump=True,climb_speed_cm_s=180.,jump_range_cm=700.,jump_search_height_cm=500.)
(OUT/'installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('M08_TRAVERSAL_ASSETS_SAVED')
