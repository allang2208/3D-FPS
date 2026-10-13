"""Save reception atrium reach only; no gameplay, render or acceptance checks."""
from pathlib import Path
from datetime import datetime
import json,runpy,shutil,traceback
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
FLOW=PROJECT/'SourceAssets/DungeonFacilityFlow20261007'
R=runpy.run_path(str(PROJECT/'SourceAssets/ReceptionLighting20261009/recipe.py'))
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
SUBJECTS=['/Game/GameMaps/Design/L_ReceptionHall_Subject',
    '/Game/GameMaps/Design/L_FacilityTransit_Subject',
    '/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject']

def save(world,target):
    dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    suffix=target.removeprefix('/Game/').lower()+'/'
    owned=[p for p in dirty if p.get_name()==target or any(p.get_name().lower().startswith('/game/'+folder+'/'+suffix) for folder in ('__externalactors__','__externalobjects__'))]
    if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Scoped package save failed: '+target)
    if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Map save failed: '+target)

def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    playing=bool(ed.get_game_world())
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    previous=ed.get_editor_world().get_path_name().split('.')[0] if ed.get_editor_world() else None
    # During PIE, edit the saved asset worlds already held by this editor.
    # Do not switch its active map or touch the UEDPIE duplicate.
    load_world=u.load_asset if playing else u.EditorLoadingAndSavingUtils.load_map
    report=dict(stage='preparing',revision=R['COVERAGE_REVISION'],maps=[],game_run=False,rendered=False,tested=False)
    (ROOT/'Receipts').mkdir(parents=True,exist_ok=True)
    def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
    for path in [PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap') for target in [TARGET]+SUBJECTS]+[FLOW/'Config/catalog.json',FLOW/'Config/layout-bank-v1.json']:
        dest=backup/path.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    report['backup']=str(backup);record()
    try:
        world=load_world(TARGET)
        generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
        if len(generators)!=1:raise RuntimeError('Expected one production generator')
        generator=generators[0];raw=generator.get_editor_property('module_catalog_json')
        (backup/'actual-catalog-before.json').write_text(raw,encoding='utf8')
        catalog=json.loads(raw)
        contract=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash']
        bank=catalog['facility_flow']['layout_bank'];old_hash=contract(catalog)
        if bank['contract_sha1']!=old_hash:raise RuntimeError('Preserve inconsistent layout bank; unrelated authoring may be in progress')
        module=next(m for m in catalog['modules'] if m['id']=='FacilityReceptionHall')
        report['changes']=R['apply_coverage'](module)
        bank['contract_sha1']=contract(catalog)
        bank['reception_coverage_update']=dict(revision=R['COVERAGE_REVISION'],source_contract_sha1=old_hash,placement_data_changed=False)
        generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
        save(world,TARGET)
        (FLOW/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
        (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(bank,ensure_ascii=False,separators=(',',':')),encoding='utf8')
        report['maps'].append(dict(path=TARGET,saved=True,lights=len(report['changes'])));record()
        ids={c['id'] for c in report['changes']}
        for target in SUBJECTS:
            world=load_world(target)
            actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
            changes=[]
            for key in sorted(ids):
                actor=actors['Reception_'+key];light=actor.get_component_by_class(u.LocalLightComponent)
                changes.append(dict(id=key,radius_before=light.attenuation_radius,intensity=light.intensity,shadows_before=light.cast_shadows))
                actor.modify();light.modify();R['apply_subject_coverage'](light)
            save(world,target)
            report['maps'].append(dict(path=target,saved=True,lights=len(changes),changes=changes));record()
        report.update(stage='maps_saved',bank_contract_sha1=bank['contract_sha1'],radius_cm=R['MAIN_RADIUS_CM'],brightness_changed=False,cone_changed=False)
        record();print('RECEPTION_COVERAGE_SAVED',len(report['maps']),'maps; atrium radius',R['MAIN_RADIUS_CM'],'cm; intensity unchanged')
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if not playing and previous and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
            u.EditorLoadingAndSavingUtils.load_map(previous)

if __name__=='__main__':main()
