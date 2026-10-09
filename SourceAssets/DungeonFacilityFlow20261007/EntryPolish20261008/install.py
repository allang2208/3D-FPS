"""Import entry detail and save only the live production catalog + entry preview."""
from pathlib import Path
from datetime import datetime
import json, runpy, importlib.util, shutil, traceback
import unreal as u

ROOT=Path(__file__).resolve().parent; FLOW=ROOT.parent; PROJECT=FLOW.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
R=runpy.run_path(str(ROOT/'recipe.py'))
REVISION=R['REVISION']; BASE=R['BASE']

def main():
    report=dict(stage='preparing',revision=REVISION,map=TARGET,tests_run=False,
        game_run=False,rendered=False,generated=False,editor_opened=False)
    receipt=ROOT/'install-receipt.json'
    def record():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    record()
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    previous=None
    try:
        if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE; no assets written')
        if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps; no assets written')
        previous=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else None
        backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
        sources=[PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap']
        for category in ('__ExternalActors__','__ExternalObjects__'):
            folder=PROJECT/'Content'/category/'GameMaps/L_Dungeon_Randomized'
            if folder.exists():sources.extend(p for p in folder.rglob('*') if p.is_file())
        for src in sources:
            dest=backup/src.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
        report['backup']=str(backup);record()
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
        generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
        if len(generators)!=1:raise RuntimeError('Expected one production generator')
        generator=generators[0];before=generator.get_editor_property('module_catalog_json')
        (backup/'catalog-before.json').write_text(before,encoding='utf8')
        contract=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash']
        catalog=R['extend'](json.loads(before),contract)
        manifest=json.loads((ROOT/'geometry.json').read_text('utf8'))
        spec=importlib.util.spec_from_file_location('entry_polish_import',PROJECT/'SourceAssets/DungeonReceptionHall20261006/install.py')
        imp=importlib.util.module_from_spec(spec);spec.loader.exec_module(imp)
        imp.ROOT=ROOT;imp.BASE=BASE;imp.OWNER=REVISION;imp.MAN=manifest
        imp.report=dict(saved_assets=[]);imp.record=lambda:None
        # New versioned names. Re-running can reuse only byte-identical inputs.
        for item in manifest['meshes']:
            if u.EditorAssetLibrary.does_asset_exist(item['mesh']):
                a=u.load_asset(item['mesh'])
                if u.EditorAssetLibrary.get_metadata_tag(a,REVISION+'.Source')!=item['sha256']:
                    raise RuntimeError('Preserve existing entry mesh with a different source: '+item['mesh'])
        imp.meshes()
        # Keep the fine guard/rib geometry in the conventional fallback too.
        # Automatic fallback simplification collapses small isolated triangles
        # and produces zero tangent bases even when the authored source is sound.
        for item in manifest['meshes']:
            if not item['nanite']:continue
            mesh=u.load_asset(item['mesh']);settings=mesh.get_editor_property('nanite_settings').copy()
            settings.set_editor_property('fallback_target',u.NaniteFallbackTarget.PERCENT_TRIANGLES)
            settings.set_editor_property('fallback_percent_triangles',1.0)
            settings.set_editor_property('fallback_relative_error',0.0)
            mesh.set_editor_property('nanite_settings',settings)
            if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Entry fallback build failed '+item['name'])
            if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Entry fallback save failed '+item['name'])
        report['saved_assets']=imp.report['saved_assets'];report['stage']='assets_saved';record()
        dependencies={a.get_path_name():a for a in generator.get_editor_property('module_assets') if a and not a.get_path_name().startswith(BASE+'/')}
        for item in manifest['meshes']:
            for path in [item['mesh'],*item['materials'].values()]:
                a=u.load_asset(path)
                if not a:raise RuntimeError('Missing entry dependency '+path)
                dependencies[a.get_path_name()]=a
        # Add only our two passage parts to the existing authoring preview.
        # They share the existing generator-owned cleanup tags at runtime.
        aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
        actors=list(u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor))
        for item in manifest['meshes']:
            if not item['kind'].startswith('Passage'):continue
            label='FacilityFlow_EntryPolish_'+item['kind']
            actor=next((a for a in actors if a.get_actor_label()==label),None)
            if not actor:actor=aa.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*catalog['start_position']))
            actor.modify();actor.set_actor_label(label);actor.set_actor_location(u.Vector(*catalog['start_position']),False,True)
            actor.set_folder_path('Dungeon/FixedEntryPreview');actor.set_owner(generator)
            actor.set_editor_property('tags',[u.Name('DungeonRouteGenerated'),u.Name('DungeonFacilityEntryPreview'),u.Name(REVISION)])
            component=actor.static_mesh_component;component.set_static_mesh(u.load_asset(item['mesh']))
            component.set_collision_profile_name('NoCollision');component.set_cast_shadow(item['cast_shadow'])
        generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
        generator.set_editor_property('module_assets',list(dependencies.values()))
        dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
        owned=[p for p in dirty if p.get_name()==TARGET or any(p.get_name().lower().startswith('/game/'+folder+'/gamemaps/l_dungeon_randomized/') for folder in ('__externalactors__','__externalobjects__'))]
        if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Entry external actor save failed')
        if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Entry map save failed')
        (FLOW/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
        (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(catalog['facility_flow']['layout_bank'],ensure_ascii=False,separators=(',',':')),encoding='utf8')
        report.update(stage='map_saved',new_lights=3,existing_lights_changed=2,
            bank_contract_sha1=catalog['facility_flow']['layout_bank']['contract_sha1'],
            saved_packages=[p.get_name() for p in owned])
        record();print('ENTRY_POLISH_SAVED',TARGET,'4 meshes, 3 new local lamps, 2 existing lamps adjusted')
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if previous and previous!=TARGET and previous.startswith('/Game/') and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
            u.EditorLoadingAndSavingUtils.load_map(previous)

if __name__=='__main__':main()
