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
        spec=importlib.util.spec_from_file_location('night_edge_import',PROJECT/'SourceAssets/DungeonReceptionHall20261006/install.py')
        imp=importlib.util.module_from_spec(spec);spec.loader.exec_module(imp)
        imp.ROOT=ROOT;imp.BASE=BASE;imp.OWNER=REVISION;imp.report=dict(saved_assets=[]);imp.record=lambda:None
        bake=json.loads((ROOT/'bake-receipt.json').read_text('utf8'))
        if bake['stage']!='six_faces_baked':raise RuntimeError('Complete the six-face production bake first')
        material=runpy.run_path(str(ROOT/'materials.py'))['install'](imp)
        manifest=json.loads((ROOT/'geometry.json').read_text('utf8'));imp.MAN=manifest
        imp.meshes()
        report.update(stage='assets_saved',saved_assets=imp.report['saved_assets']);record()
        dependencies={a.get_path_name():a for a in generator.get_editor_property('module_assets') if a}
        dependencies[material.get_path_name()]=material
        for item in manifest['meshes']:
            for path in [item['mesh'],*item['materials'].values()]:
                asset=imp.asset(path);dependencies[asset.get_path_name()]=asset
        generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
        generator.set_editor_property('module_assets',list(dependencies.values()))
        dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
        owned=[p for p in dirty if p.get_name()==TARGET or any(p.get_name().lower().startswith('/game/'+folder+'/gamemaps/l_dungeon_randomized/') for folder in ('__externalactors__','__externalobjects__'))]
        if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Night street external actor save failed')
        if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Night street production map save failed')
        (FLOW/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
        (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(catalog['facility_flow']['layout_bank'],ensure_ascii=False,separators=(',',':')),encoding='utf8')
        report.update(stage='map_saved',bank_contract_sha1=catalog['facility_flow']['layout_bank']['contract_sha1'],
            six_faces_baked=True,production_bake_rendered=True,acceptance_rendered=False,cubemap_face_size=2048,flat_border_fill_removed=True,grille_fixed_closed=True,
            saved_packages=[p.get_name() for p in owned])
        record();(ROOT/'install-receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
        print('RECEPTION_CONTINUOUS_CUBEMAP_SAVED',TARGET,'six baked directions and physical entrance reveals')
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if previous and previous!=TARGET and previous.startswith('/Game/') and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(previous)

if __name__=='__main__':main()
