"""Publish approved surfaces through existing material identities, retaining backups."""
import hashlib,json,shutil,sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
sys.path.insert(0,str(PROJECT/'Tools/AssetPipeline'))
import dungeon_wall_release as release
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
CFG=json.loads((ROOT/'Config/production-release.json').read_text())
SAMPLE=json.loads((ROOT/'Config/material-candidates.json').read_text())
RECEIPT=ROOT/'Receipts/production-install.json'
report=json.loads(RECEIPT.read_text()) if RECEIPT.exists() else {'stage':'preparing','backups':{},'frozen_materials':{},'instances':{},'runtime_tested':False}
def record():RECEIPT.write_text(json.dumps(report,indent=2),encoding='utf-8')
def backup(path):
    relative=path.removeprefix('/Game/')+'.uasset';src=PROJECT/'Content'/relative;dst=ROOT/'BeforeProduction/Content'/relative
    if not dst.exists():
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    report['backups'][path]={'file':str(dst),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()};record()
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue.get_game_world():raise RuntimeError('Game active; preserve the current session')
paths=[release.CONCRETE,*CFG['instance_aliases']]
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths):raise RuntimeError('Unsaved target material edits: '+str(dirty.intersection(paths)))
for path in paths:
    if not E.does_asset_exist(path):raise RuntimeError('Expected shared material missing '+path)
    backup(path)
# Freeze the four displayed old materials before their public identities change.
frozen={}
for path in SAMPLE['candidates']:
    dest=release.BASE+'/Baseline/'+path.rsplit('/',1)[1]+'_BeforeUpgrade'
    m=u.load_asset(dest) if E.does_asset_exist(dest) else E.duplicate_asset(path,dest)
    if not m:raise RuntimeError('Cannot freeze baseline '+path)
    release.save(m);frozen[path]=m;report['frozen_materials'][path]=dest;record()
# Commandlets must initialize the level to enumerate its serialized actors.
# An interactive editor keeps its current map; never switch a user's live map.
sample_path=SAMPLE['sample_map']
if not report.get('sample_baseline_saved'):
    if sample_path in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()}:
        raise RuntimeError('Preserve unsaved comparison-map edits')
    relative=sample_path.removeprefix('/Game/')+'.umap';src=PROJECT/'Content'/relative;dst=ROOT/'BeforeProduction/Content'/relative
    if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower():
        if not u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(sample_path):
            raise RuntimeError('Cannot initialize comparison map in background commandlet')
        world=ue.get_editor_world()
    else:
        world=ue.get_editor_world()
        if not world or world.get_path_name().split('.')[0]!=sample_path:
            raise RuntimeError('Freeze comparison baseline with a background commandlet; preserve active map')
    if not world:raise RuntimeError('Cannot load comparison map as an asset')
    changed=0
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor):
        label=actor.get_actor_label()
        if not label.startswith(('A_ORIGINAL','C_ORIGINAL','Old_')):continue
        comp=actor.static_mesh_component
        for i in range(comp.get_num_materials()):
            old=comp.get_material(i)
            if old and old.get_path_name().split('.')[0] in frozen:
                actor.modify();comp.modify();comp.set_material(i,frozen[old.get_path_name().split('.')[0]]);changed+=1
    if not changed:raise RuntimeError('No baseline material slots found in comparison map')
    if not u.EditorLoadingAndSavingUtils.save_map(world,sample_path):raise RuntimeError('Comparison baseline save failed')
    report['sample_baseline_saved']=True;report['sample_baseline_slots']=changed;record()
report['stage']='publishing';record()
release.publish_concrete();report['concrete_saved']=True;record()
for path in CFG['instance_aliases']:
    mi=u.load_asset(path);previous=mi.get_editor_property('parent').get_path_name()
    release.apply_instance(mi)
    report['instances'][path]={'previous_parent':previous,'parent':mi.get_editor_property('parent').get_path_name(),'saved':True};record()
report['stage']='production_materials_saved';report['geometry_changed']=False;report['game_maps_saved']=False
report['current_editor_world']=ue.get_editor_world().get_path_name();record()
print('DUNGEON_WALL_RELEASE_SAVED',json.dumps(report),flush=True)
