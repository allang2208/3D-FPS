"""Save only the transit locker and mop placements; no game or render run."""
from pathlib import Path
from datetime import datetime
import json, runpy, shutil, traceback
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
FLOW=PROJECT/'SourceAssets/DungeonFacilityFlow20261007'
RECIPE=ROOT/'recipe.py'
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
R=runpy.run_path(str(RECIPE))
save=runpy.run_path(str(PROJECT/'SourceAssets/ReceptionCoverage20261009/install.py'))['save']


def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    playing=bool(editor.get_game_world())
    previous=editor.get_editor_world().get_path_name().split('.')[0] if editor.get_editor_world() else None
    targets=(TARGET,*R['SUBJECTS'])
    dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    for package in dirty:
        name=package.get_name().lower()
        for target in targets:
            suffix=target.removeprefix('/Game/').lower()+'/'
            if name==target.lower() or any(name.startswith('/game/'+folder+'/'+suffix) for folder in ('__externalactors__','__externalobjects__')):
                raise RuntimeError('Preserve unsaved target package '+package.get_name())
    if not playing and u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Preserve unsaved current map before switching')
    # An existing PIE instance is left alone. The saved editor asset worlds are
    # the production inputs for the next dungeon instance, never UEDPIE worlds.
    load_world=u.load_asset if playing else u.EditorLoadingAndSavingUtils.load_map
    backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
    for target in targets:
        relative=target.removeprefix('/Game/')
        paths=[PROJECT/'Content'/(relative+'.umap')]
        paths.extend(PROJECT/'Content'/folder/relative for folder in ('__ExternalActors__','__ExternalObjects__'))
        for path in paths:
            if not path.exists():continue
            dest=backup/path.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True)
            if path.is_dir():shutil.copytree(path,dest)
            else:shutil.copy2(path,dest)
    for name in ('catalog.json','layout-bank-v1.json'):
        path=FLOW/'Config'/name;dest=backup/path.relative_to(PROJECT)
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    report=dict(stage='prepared',revision=R['REVISION'],backup=str(backup),maps=[],existing_game_running=playing,tested=False)
    def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    record()
    try:
        world=load_world(TARGET)
        generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
        if len(generators)!=1:raise RuntimeError('Expected one saved production generator')
        generator=generators[0]
        raw=generator.get_editor_property('module_catalog_json')
        (backup/'actual-catalog-before.json').write_text(raw,encoding='utf8')
        catalog=json.loads(raw)
        contract=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash']
        bank=catalog['facility_flow']['layout_bank']
        if bank['contract_sha1']!=contract(catalog):raise RuntimeError('Preserve inconsistent layout-bank source')
        module=next(m for m in catalog['modules'] if m['id']=='FacilityTransit')
        changes=R['apply_module'](module)
        bank['contract_sha1']=contract(catalog)
        generator.modify()
        generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
        save(world,TARGET)
        (FLOW/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
        (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(bank,ensure_ascii=False,separators=(',',':')),encoding='utf8')
        report['maps'].append(dict(path=TARGET,saved=True,changes=changes))
        report['stage']='production_saved';record()
        for target in R['SUBJECTS']:
            world=load_world(target)
            if not world:raise RuntimeError('Cannot load saved subject '+target)
            changes=R['apply_subject'](world)
            save(world,target)
            report['maps'].append(dict(path=target,saved=True,changes=changes));record()
        report['stage']='maps_saved';record()
        print('TRANSIT_EQUIPMENT_CLEARANCE_SAVED '+json.dumps(report['maps'],ensure_ascii=False))
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if not playing and previous and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
            u.EditorLoadingAndSavingUtils.load_map(previous)


if __name__=='__main__':main()
