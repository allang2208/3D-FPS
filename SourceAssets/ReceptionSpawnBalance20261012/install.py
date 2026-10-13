"""Save the scoped service-door relocation in the live production catalog."""
from pathlib import Path
from datetime import datetime
import json,runpy,shutil,traceback
import unreal as u

ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
FLOW=PROJECT/'SourceAssets/DungeonFacilityFlow20261007'
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
R=runpy.run_path(str(ROOT/'recipe.py'))
report=dict(stage='preparing',game_run=False,rendered=False)

def record():
    (ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor.get_game_world():raise RuntimeError('Preserve active game; map save needs editor mode')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    previous=editor.get_editor_world()
    previous=previous.get_path_name().split('.')[0] if previous else ''
    dirty_before={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    prefix='/Game/__ExternalActors__/GameMaps/L_Dungeon_Randomized/'
    if any(p.lower().startswith(prefix.lower()) for p in dirty_before):raise RuntimeError('Preserve unsaved dungeon actors')
    backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
    files=[PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap',FLOW/'Config/catalog.json',
           FLOW/'Config/layout-bank-v1.json',FLOW/'SpawnEntries20261009/placements.json']
    for category in ('__ExternalActors__','__ExternalObjects__'):
        folder=PROJECT/'Content'/category/'GameMaps/L_Dungeon_Randomized'
        if folder.exists():files.extend(p for p in folder.rglob('*') if p.is_file())
    for path in files:
        dest=backup/path.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    report['backup']=str(backup);record()
    try:
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
        generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
        if len(generators)!=1:raise RuntimeError('Expected one production generator')
        generator=generators[0];raw=generator.get_editor_property('module_catalog_json')
        (backup/'actual-catalog-before.json').write_text(raw,encoding='utf8')
        before=json.loads(raw)
        contract=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash']
        if before['facility_flow']['layout_bank']['contract_sha1']!=contract(before):
            raise RuntimeError('Preserve independently changed layout contract')
        after=R['move'](before)
        bank=after['facility_flow']['layout_bank'];bank['contract_sha1']=contract(after)
        placement_path=FLOW/'SpawnEntries20261009/placements.json'
        placements=R['move_source'](json.loads(placement_path.read_text('utf8')))
        generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(after,ensure_ascii=False))
        dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
        owned=[p for p in dirty if p.get_name() not in dirty_before and (p.get_name()==TARGET or
            any(p.get_name().lower().startswith('/game/'+category+'/gamemaps/l_dungeon_randomized/') for category in ('__externalactors__','__externalobjects__')))]
        if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Could not save dungeon packages')
        if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Could not save dungeon map')
        (FLOW/'Config/catalog.json').write_text(json.dumps(after,ensure_ascii=False,indent=2),encoding='utf8')
        (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(bank,ensure_ascii=False,separators=(',',':')),encoding='utf8')
        placement_path.write_text(json.dumps(placements,ensure_ascii=False,indent=2),encoding='utf8')
        report.update(stage='map_saved',map=TARGET,fixture=R['FIXTURE'],position_cm=R['POSITION'],yaw=R['YAW'],
            left_fixture_preserved='FacilityReceptionHall.service.00',clearance=R['NEW_CLEARANCE'],
            spawn_floor_cm=[420.,1560.,0.],exit_target_floor_cm=[420.,1245.,0.],
            moved_parts=3,layout_contract_sha1=bank['contract_sha1'],layout_entries_moved=False,
            native_code_changed=False,source_placements_saved=True)
        record();print('RECEPTION_SPAWN_BALANCE_SAVED',json.dumps(report,ensure_ascii=False),flush=True)
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if previous and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
            u.EditorLoadingAndSavingUtils.load_map(previous)

if __name__=='__main__':main()
