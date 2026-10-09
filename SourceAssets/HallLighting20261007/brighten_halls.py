"""Save a moderate hall lighting lift in subjects and the production recipe.

No generation preview, gameplay, screenshot or regression is started.
"""
from pathlib import Path
from datetime import datetime
import json, runpy, copy, shutil, traceback
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
FLOW=PROJECT/'SourceAssets/DungeonFacilityFlow20261007'
P=runpy.run_path(str(ROOT/'profile.py'))
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
SUBJECTS=['/Game/GameMaps/Design/'+name for name in (
    'L_ReceptionHall_Subject','L_FacilityTransit_Subject','L_FacilityTransit_Alternate_Subject')]

def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    previous=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else None
    report=dict(stage='preparing',revision=P['REVISION'],maps=[],tests_run=False,game_run=False,rendered=False,generated=False)
    receipt=ROOT/'Receipts/brightness-20261008.json'
    def record():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    try:
        record()
        backup=ROOT/'Backups'/('brightness-save-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
        for path in [TARGET]+SUBJECTS:
            rel=path.removeprefix('/Game/')
            sources=[PROJECT/'Content'/(rel+'.umap')]
            for category in ('__ExternalActors__','__ExternalObjects__'):
                folder=PROJECT/'Content'/category/rel
                if folder.exists():sources.extend(p for p in folder.rglob('*') if p.is_file())
            for disk in sources:
                if not disk.exists():raise RuntimeError('Expected saved hall missing: '+str(disk))
                dest=backup/disk.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(disk,dest)
        report['backup']=str(backup);record()
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
        generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
        if len(generators)!=1:raise RuntimeError('Expected one production generator')
        g=generators[0];before=g.get_editor_property('module_catalog_json');catalog=json.loads(before)
        (backup/'catalog-before.json').write_text(before,encoding='utf8')
        hash_contract=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash']
        bank=catalog['facility_flow']['layout_bank']
        if bank['contract_sha1']!=hash_contract(catalog):
            raise RuntimeError('Preserve stale/unrelated layout bank; cannot rebind it for lighting')
        builders=runpy.run_path(str(FLOW/'extend_catalog.py'))
        reception,_=builders['reception_and_entry']()
        transit,_,_=builders['transit']()
        desired={m['id']:m for m in (reception,transit)}
        changes=[]
        def key(light):return (light.get('type','point'),tuple(round(v,5) for v in light['position']))
        for module in catalog['modules']:
            if module['id'] not in desired:continue
            targets={key(light):light for light in desired[module['id']]['lights']}
            for light in module['lights']:
                target=targets.get(key(light))
                if target is None:raise RuntimeError('Preserve unrecognized hall light '+module['id']+str(light['position']))
                changes.append(dict(module=module['id'],position=light['position'],before=light['intensity'],after=target['intensity']))
                # Preserve authored radii, shadows, phase/function and all other fields.
                light['intensity']=target['intensity']
            module['lighting_revision']=P['REVISION']
        old_contract=bank['contract_sha1']
        bank['contract_sha1']=hash_contract(catalog)
        bank['lighting_update']=dict(revision=P['REVISION'],source_contract_sha1=old_contract,
            placement_data_changed=False,regression_run=False)
        g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
        dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
        owned=[p for p in dirty if p.get_name()==TARGET or any(p.get_name().lower().startswith('/game/'+folder+'/gamemaps/l_dungeon_randomized/') for folder in ('__externalactors__','__externalobjects__'))]
        if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Production lighting actor save failed')
        if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Production lighting map save failed')
        (FLOW/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
        (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(bank,ensure_ascii=False,separators=(',',':')),encoding='utf8')
        report['maps'].append(dict(path=TARGET,saved=True,lights=len(changes)))
        report['production_changes']=changes;report['bank_contract_sha1']=bank['contract_sha1'];record()
        for path in SUBJECTS:
            world=u.EditorLoadingAndSavingUtils.load_map(path)
            if not world:raise RuntimeError('Cannot load hall '+path)
            changed=P['apply_world']()
            u.EditorAssetLibrary.set_metadata_tag(world,'HallLighting.Revision',P['REVISION'])
            if not u.EditorLoadingAndSavingUtils.save_map(world,path):raise RuntimeError('Hall save failed '+path)
            report['maps'].append(dict(path=path,saved=True,changes=changed));record()
        report['stage']='maps_saved';record()
        print('HALL_BRIGHTNESS_SAVED',len(report['maps']),'maps',len(changes),'production light entries')
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if previous and previous.startswith('/Game/') and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
            u.EditorLoadingAndSavingUtils.load_map(previous)

if __name__=='__main__':main()
