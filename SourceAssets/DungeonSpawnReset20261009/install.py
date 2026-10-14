"""Remove legacy spawn data from the saved production map; never start gameplay."""
from pathlib import Path
from datetime import datetime
import json,copy,runpy,shutil,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
FLOW=PROJECT/'SourceAssets/DungeonFacilityFlow20261007'
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
R=runpy.run_path(str(ROOT/'recipe.py'))
save=runpy.run_path(str(PROJECT/'SourceAssets/ReceptionCoverage20261009/install.py'))['save']

def main():
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    if ed.get_game_world():raise RuntimeError('Preserve active gameplay while removing saved spawn configuration')
    previous=ed.get_editor_world().get_path_name().split('.')[0] if ed.get_editor_world() else None
    report=dict(stage='preparing',revision=R['REVISION'],game_run=False)
    def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
    sources=[FLOW/'Config/catalog.json',FLOW/'Config/layout-bank-v1.json',PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap']
    for category in ('__ExternalActors__','__ExternalObjects__'):
        folder=PROJECT/'Content'/category/'GameMaps/L_Dungeon_Randomized'
        if folder.exists():sources.extend(p for p in folder.rglob('*') if p.is_file())
    for source in sources:
        dest=backup/source.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    report['backup']=str(backup);record()
    try:
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
        g=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)[0]
        catalog=json.loads(g.get_editor_property('module_catalog_json'))
        (backup/'catalog-before.json').write_text(json.dumps(catalog,ensure_ascii=False),encoding='utf8')
        contract=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash']
        bank=catalog['facility_flow']['layout_bank']
        if contract(catalog)!=bank['contract_sha1']:raise RuntimeError('Preserve inconsistent layout bank')
        result=R['extend'](catalog,contract)
        report['removed_spawn_modules']=[m['id'] for m in catalog['modules'] if 'spawn' in m]
        report['removed_boss_modules']=[m['id'] for m in catalog['modules'] if 'boss_encounter' in m]
        report['opened_progression_gates']=[m['id'] for m in catalog['modules'] if 'progression_gate' in m]
        # The existing map is fully loaded here, including its external actors.
        # Remove old saved combat controllers/monsters if any were left in a preview.
        aa=u.get_editor_subsystem(u.EditorActorSubsystem)
        removed=[]
        combat_type=getattr(u,'MonsterCombatComponent',None)
        retired={'DungeonSpawnDirector','DungeonRoomEncounter','DungeonProgressionGate','DungeonRoomGate'}
        for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
            kind=actor.get_class().get_name()
            combat=bool(combat_type and actor.get_component_by_class(combat_type))
            if kind in retired or combat or actor.actor_has_tag('DungeonSpawned') or actor.actor_has_tag('DungeonTerminalBoss'):
                removed.append(dict(label=actor.get_actor_label(),type=kind))
                if not aa.destroy_actor(actor):raise RuntimeError('Could not remove old combat actor')
        report['removed_saved_actors']=removed
        g.modify();g.set_editor_property('module_catalog_json',json.dumps(result,ensure_ascii=False))
        old_classes={p.get('class') for m in catalog['modules'] for p in m.get('spawn',{}).get('pool',[])}
        old_classes.update(m['boss_encounter']['class'] for m in catalog['modules'] if 'boss_encounter' in m)
        assets=list(g.get_editor_property('module_assets'))
        kept=[a for a in assets if a and a.get_path_name() not in old_classes]
        g.set_editor_property('module_assets',kept)
        save(world,TARGET)
        (FLOW/'Config/catalog.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(result['facility_flow']['layout_bank'],ensure_ascii=False,separators=(',',':')),encoding='utf8')
        report.update(stage='map_saved',bank_contract_sha1=result['facility_flow']['layout_bank']['contract_sha1'],
            bank_entries_unchanged=bank['entries']==result['facility_flow']['layout_bank']['entries'],removed_class_dependencies=len(assets)-len(kept))
        record();print('DUNGEON_OLD_SPAWNING_REMOVED',len(report['removed_spawn_modules']),'spawn sections;',len(report['removed_boss_modules']),'boss;',len(report['opened_progression_gates']),'gates; saved',TARGET)
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if previous and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(previous)

if __name__=='__main__':main()
