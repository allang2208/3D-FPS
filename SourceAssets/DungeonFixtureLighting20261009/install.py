"""Save inspected fixture bindings; no layout generation, game run or render."""
from pathlib import Path
from datetime import datetime
import json,copy,runpy,shutil,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
FLOW=PROJECT/'SourceAssets/DungeonFacilityFlow20261007'
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
SUBJECTS=['/Game/GameMaps/Design/L_FacilityTransit_Subject','/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject']
R=runpy.run_path(str(ROOT/'recipe.py'));W=runpy.run_path(str(ROOT/'world_lights.py'))

def save(world,target):
    dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    suffix=target.removeprefix('/Game/').lower()+'/'
    owned=[p for p in dirty if p.get_name()==target or any(p.get_name().lower().startswith('/game/'+folder+'/'+suffix) for folder in ('__externalactors__','__externalobjects__'))]
    if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Scoped package save failed: '+target)
    if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Map save failed: '+target)

def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ed.get_game_world():raise RuntimeError('Preserve active PIE')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    previous=ed.get_editor_world().get_path_name().split('.')[0] if ed.get_editor_world() else None
    report=dict(stage='preparing',revision=R['REVISION'],maps=[],game_run=False,rendered=False,editor_opened=False)
    def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
    for target in [TARGET]+SUBJECTS:
        rel=target.removeprefix('/Game/');sources=[PROJECT/'Content'/(rel+'.umap')]
        for category in ('__ExternalActors__','__ExternalObjects__'):
            folder=PROJECT/'Content'/category/rel
            if folder.exists():sources.extend(p for p in folder.rglob('*') if p.is_file())
        for source in sources:
            dest=backup/source.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    for source in (FLOW/'Config/catalog.json',FLOW/'Config/layout-bank-v1.json',FLOW/'Config/original-entry-actors.json'):
        dest=backup/source.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    report['backup']=str(backup);record()
    try:
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
        generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
        if len(generators)!=1:raise RuntimeError('Expected one generator')
        g=generators[0];catalog=json.loads(g.get_editor_property('module_catalog_json'))
        (backup/'catalog-before.json').write_text(json.dumps(catalog,ensure_ascii=False),encoding='utf8')
        contract=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash']
        bank=catalog['facility_flow']['layout_bank'];old_hash=contract(catalog)
        if old_hash!=bank['contract_sha1']:raise RuntimeError('Existing layout-bank contract has changed')
        placements=copy.deepcopy(bank['entries']);data=R['bindings']()
        report['catalog_changes']=R['apply_catalog'](catalog)
        assets={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
        for parts in data['additional_parts'].values():
            for part in parts:
                a=u.load_asset(part['mesh'])
                if not a:raise RuntimeError('Missing landing lamp mesh')
                assets[a.get_path_name()]=a
        actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
        for label,b in data['fixed'].items():
            if label not in actors:raise RuntimeError('Missing fixed light: '+label)
            c=actors[label].get_component_by_class(u.LocalLightComponent)
            for prop in W['COMMON']:c.get_editor_property(prop)
        report['fixed']=[]
        for label,b in data['fixed'].items():
            a=W['apply'](world,actors[label],b);report['fixed'].append(W['snapshot'](a))
        bank['fixture_lighting_update']=dict(revision=R['REVISION'],source_contract_sha1=old_hash,placement_data_changed=False)
        bank['contract_sha1']=contract(catalog)
        if bank['entries']!=placements:raise RuntimeError('Unexpected placement mutation')
        g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False));g.set_editor_property('module_assets',list(assets.values()))
        u.EditorAssetLibrary.set_metadata_tag(world,'Dungeon.FixtureLighting',R['REVISION'])
        save(world,TARGET)
        (FLOW/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
        (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(bank,ensure_ascii=False,separators=(',',':')),encoding='utf8')
        original=json.loads((FLOW/'Config/original-entry-actors.json').read_text('utf8'))
        R['apply_fixed_config'](original)
        (FLOW/'Config/original-entry-actors.json').write_text(json.dumps(original,ensure_ascii=False,indent=2),encoding='utf8')
        report.update(stage='production_saved',bank_contract_sha1=bank['contract_sha1'],catalog_light_count=sum(len(m['lights']) for m in catalog['modules']),portal_variants_checked=data['portal_variants_checked'])
        report['maps'].append(dict(path=TARGET,saved=True,fixed_lights=13));record()
        for target in SUBJECTS:
            world=u.EditorLoadingAndSavingUtils.load_map(target)
            changes=W['apply_subject'](world)
            if len(changes)!=53:raise RuntimeError('Expected 53 subject lamps after splitting three tunnel lights')
            u.EditorAssetLibrary.set_metadata_tag(world,'Dungeon.FixtureLighting',R['REVISION'])
            save(world,target);report['maps'].append(dict(path=target,saved=True,lights=changes));record()
        report['stage']='map_saved';record()
        print('DUNGEON_FIXTURE_LIGHTING_SAVED',len(report['catalog_changes']),'catalog actions;',len(report['fixed']),'fixed lights;',len(report['maps']),'maps;',report['bank_contract_sha1'])
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if previous and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(previous)

if __name__=='__main__':main()
