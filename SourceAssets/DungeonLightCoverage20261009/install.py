"""Save the requested reach corrections into production and maintained subjects."""
from pathlib import Path
from datetime import datetime
import copy,json,runpy,shutil,traceback
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
FLOW=PROJECT/'SourceAssets/DungeonFacilityFlow20261007'
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
SUBJECTS=['/Game/GameMaps/Design/L_FacilityTransit_Subject','/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject']
R=runpy.run_path(str(ROOT/'recipe.py'))
save=runpy.run_path(str(PROJECT/'SourceAssets/ReceptionCoverage20261009/install.py'))['save']

def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    playing=bool(ed.get_game_world())
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    previous=ed.get_editor_world().get_path_name().split('.')[0] if ed.get_editor_world() else None
    load_world=u.load_asset if playing else u.EditorLoadingAndSavingUtils.load_map
    report=dict(stage='preparing',revision=R['REVISION'],maps=[],game_run=False,rendered=False,active_pie_preserved=playing)
    def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
    sources=[FLOW/'Config/catalog.json',FLOW/'Config/layout-bank-v1.json',FLOW/'Config/original-entry-actors.json']
    for target in [TARGET]+SUBJECTS:
        rel=target.removeprefix('/Game/');sources.append(PROJECT/'Content'/(rel+'.umap'))
        for category in ('__ExternalActors__','__ExternalObjects__'):
            folder=PROJECT/'Content'/category/rel
            if folder.exists():sources.extend(p for p in folder.rglob('*') if p.is_file())
    for source in sources:
        dest=backup/source.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    report['backup']=str(backup);record()
    try:
        world=load_world(TARGET)
        generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
        if len(generators)!=1:raise RuntimeError('Expected one saved generator')
        g=generators[0];catalog=json.loads(g.get_editor_property('module_catalog_json'))
        (backup/'catalog-before.json').write_text(json.dumps(catalog,ensure_ascii=False),encoding='utf8')
        contract=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash']
        bank=catalog['facility_flow']['layout_bank'];old_hash=contract(catalog)
        if old_hash!=bank['contract_sha1']:raise RuntimeError('Preserve existing inconsistent layout bank')
        placements=copy.deepcopy(bank['entries'])
        report['catalog_changes']=R['apply_catalog'](catalog)
        actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
        report['fixed_changes']=[]
        for c in R['config']()['changes']:
            if c['module']!='FixedStart':continue
            a=actors[c['id']];light=a.get_component_by_class(u.LocalLightComponent)
            before=dict(radius=light.attenuation_radius,shadows=light.cast_shadows,intensity=light.intensity)
            a.modify();light.modify();light.set_attenuation_radius(c['fields']['radius']);light.set_cast_shadows(True)
            report['fixed_changes'].append(dict(id=c['id'],before=before,radius_after=light.attenuation_radius))
        bank['light_coverage_update']=dict(revision=R['REVISION'],source_contract_sha1=old_hash,placement_data_changed=False)
        bank['contract_sha1']=contract(catalog)
        if bank['entries']!=placements:raise RuntimeError('Unexpected layout mutation')
        g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
        save(world,TARGET)
        (FLOW/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
        (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(bank,ensure_ascii=False,separators=(',',':')),encoding='utf8')
        original=json.loads((FLOW/'Config/original-entry-actors.json').read_text('utf8'))
        R['apply_fixed_config'](original)
        (FLOW/'Config/original-entry-actors.json').write_text(json.dumps(original,ensure_ascii=False,indent=2),encoding='utf8')
        report['maps'].append(dict(path=TARGET,saved=True,catalog_lights=len(report['catalog_changes']),fixed_lights=len(report['fixed_changes'])));record()
        for target in SUBJECTS:
            world=load_world(target);changes=R['apply_subject'](world)
            save(world,target)
            report['maps'].append(dict(path=target,saved=True,changes=changes));record()
        report.update(stage='maps_saved',bank_contract_sha1=bank['contract_sha1'],brightness_changed=False,directions_changed=False,cones_changed=False)
        record();print('DUNGEON_COVERAGE_SAVED',len(report['catalog_changes']),'catalog lights;',len(report['fixed_changes']),'fixed lights;',len(report['maps']),'maps; intensity and directions unchanged')
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if not playing and previous and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(previous)

if __name__=='__main__':main()
