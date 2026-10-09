"""Add one existing dungeon chest to each ecology subject without rebuilding it."""
from pathlib import Path
import json,runpy,shutil,hashlib,traceback
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
existing=globals().get('ECOLOGY_EDITOR_BATCH',False)
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not existing:
    raise RuntimeError('Use the serialized background or existing-editor entry')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('PIE has not ended; treasure saving remains pending')
dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
if dirty:raise RuntimeError('Preserve unsaved maps: '+str(dirty))
world=editor.get_editor_world() if editor else None
previous=world.get_path_name().split('.')[0] if world else None
helpers=runpy.run_path(str(ROOT/'Scripts/ecology_treasure.py'))
cfg=helpers['apply'](json.loads((ROOT/'Config/room.json').read_text('utf8')))
if cfg.get('phase')=='production':raise RuntimeError('Subject chest installer retired; treasure is part of the production ecology module')
room=cfg['rooms'][2];chest=next(p for p in room['props'] if p['identity']=='ecology_upper_platform')
actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
receipt=ROOT/'Receipts/upper-platform-chest-20261005.json'
report=dict(revision=helpers['REVISION'],stage='saving',maps={},chest=chest,
    assets_reused=True,new_assets=False,native_changes=False,tests_run=False,game_run=False,rendered=False)
def record():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def load(path):
    result=u.load_asset(path)
    if not result:raise RuntimeError('Required treasure asset missing: '+path)
    return result
def backup(path):
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    target=ROOT/'Revisions/upper-platform-chest-before'/(path.stem+'-'+digest[:12]+path.suffix)
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():shutil.copy2(path,target)
try:
    record()
    for target,offset in [(room['map'],[0,0,0]),(cfg['sample_map'],room['offset'])]:
        backup(PROJECT/'Content'/Path(target.removeprefix('/Game/')).with_suffix('.umap'))
        current=u.EditorLoadingAndSavingUtils.load_map(target)
        if not current:raise RuntimeError('Cannot load '+target)
        for actor in actors.get_all_level_actors():
            if helpers['TAG'] in [str(t) for t in actor.tags]:actors.destroy_actor(actor)
        actor=helpers['spawn'](actors,load,chest,offset,target.rsplit('/',1)[-1])
        if not u.EditorLoadingAndSavingUtils.save_map(current,target):raise RuntimeError('Map save failed '+target)
        position=actor.get_actor_location()
        report['maps'][target]=dict(stage='map_saved',count=1,position_cm=[position.x,position.y,position.z],yaw=chest['yaw'])
        record()
    for filename in ('room.json','modules-draft.json'):backup(ROOT/'Config'/filename)
    draft=json.loads((ROOT/'Config/modules-draft.json').read_text('utf8'))
    module=next(m for m in draft['modules'] if m['id']=='EcoBiosphere')
    module['props']=[p for p in module.get('props',[]) if p.get('identity')!='ecology_upper_platform']+[chest]
    module['upper_platform_chest_revision']=helpers['REVISION']
    (ROOT/'Config/room.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
    (ROOT/'Config/modules-draft.json').write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf8')
    report.update(stage='maps_saved',pending_map_saves=False,operation_host='existing_editor' if existing else 'background_commandlet')
    record();print('ECOLOGY_UPPER_PLATFORM_CHEST_SAVED')
except Exception:
    report.update(stage='save_failed',error=traceback.format_exc());record();raise
finally:
    if existing and previous:u.EditorLoadingAndSavingUtils.load_map(previous)
