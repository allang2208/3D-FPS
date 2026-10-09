"""Background import and scoped production-catalog save; no gameplay or preview."""
from pathlib import Path
from datetime import datetime
import json,runpy,importlib.util,shutil,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent;FLOW=ROOT.parent;PROJECT=FLOW.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
R=runpy.run_path(str(ROOT/'recipe.py'));REVISION=R['REVISION'];BASE=R['BASE']

def main():
    report=dict(stage='preparing',revision=REVISION,map=TARGET,tests_run=False,game_run=False,rendered=False,generated=False,editor_opened=False)
    def record():(ROOT/'latest-attempt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    record();previous=None
    try:
        if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
        editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE; no assets written')
        if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps; no assets written')
        previous=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else None
        backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
        files=[PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap']
        for category in ('__ExternalActors__','__ExternalObjects__'):
            folder=PROJECT/'Content'/category/'GameMaps/L_Dungeon_Randomized'
            if folder.exists():files.extend(p for p in folder.rglob('*') if p.is_file())
        for src in files:
            dest=backup/src.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
        report['backup']=str(backup);record()
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
        generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
        if len(generators)!=1:raise RuntimeError('Expected one production generator')
        generator=generators[0];before=generator.get_editor_property('module_catalog_json')
        (backup/'catalog-before.json').write_text(before,encoding='utf8')
        contract=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash']
        catalog=R['extend'](json.loads(before),contract)
        grille=u.load_asset(R['GRILLE'])
        if not grille:raise RuntimeError('Existing production iron grille is missing')
        manifest=json.loads((ROOT/'geometry.json').read_text('utf8'))
        spec=importlib.util.spec_from_file_location('front_entry_import',PROJECT/'SourceAssets/DungeonReceptionHall20261006/install.py')
        imp=importlib.util.module_from_spec(spec);spec.loader.exec_module(imp)
        imp.ROOT=ROOT;imp.BASE=BASE;imp.OWNER=REVISION;imp.MAN=manifest;imp.report=dict(saved_assets=[]);imp.record=lambda:None
        for item in manifest['meshes']:
            if u.EditorAssetLibrary.does_asset_exist(item['mesh']):
                mesh=u.load_asset(item['mesh'])
                if u.EditorAssetLibrary.get_metadata_tag(mesh,REVISION+'.Source')!=item['sha256']:raise RuntimeError('Preserve differing derived mesh '+item['mesh'])
        imp.meshes()
        for item in manifest['meshes']:
            if not item['nanite']:continue
            mesh=u.load_asset(item['mesh']);settings=mesh.get_editor_property('nanite_settings').copy()
            settings.set_editor_property('fallback_target',u.NaniteFallbackTarget.PERCENT_TRIANGLES)
            settings.set_editor_property('fallback_percent_triangles',1.0);settings.set_editor_property('fallback_relative_error',0.0)
            mesh.set_editor_property('nanite_settings',settings)
            if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Front entry mesh build failed '+item['name'])
            if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Front entry mesh save failed '+item['name'])
        report.update(stage='assets_saved',saved_assets=imp.report['saved_assets'],reused_grille=grille.get_path_name());record()
        # No generated rooms are instantiated while saving this recipe.
        dependencies={a.get_path_name():a for a in generator.get_editor_property('module_assets') if a}
        dependencies[grille.get_path_name()]=grille
        for item in manifest['meshes']:
            for path in [item['mesh'],*item['materials'].values()]:
                asset=u.load_asset(path)
                if not asset:raise RuntimeError('Missing dependency '+path)
                dependencies[asset.get_path_name()]=asset
        generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
        generator.set_editor_property('module_assets',list(dependencies.values()))
        dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
        owned=[p for p in dirty if p.get_name()==TARGET or any(p.get_name().lower().startswith('/game/'+folder+'/gamemaps/l_dungeon_randomized/') for folder in ('__externalactors__','__externalobjects__'))]
        if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Front entry external actor save failed')
        if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Front entry production map save failed')
        (FLOW/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
        (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(catalog['facility_flow']['layout_bank'],ensure_ascii=False,separators=(',',':')),encoding='utf8')
        report.update(stage='map_saved',bank_contract_sha1=catalog['facility_flow']['layout_bank']['contract_sha1'],
            relocated_lounge_centres_cm=[[-2290,1050,0],[-2290,-1050,0]],grille_fixed_closed=True,
            saved_packages=[p.get_name() for p in owned])
        record();(ROOT/'install-receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
        print('RECEPTION_FRONT_ENTRY_SAVED',TARGET,'reused closed grille, two clear lounge groups, corrected signs and frame seams')
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if previous and previous!=TARGET and previous.startswith('/Game/') and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(previous)

if __name__=='__main__':main()
