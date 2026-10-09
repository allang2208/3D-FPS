"""Import the open connector and restore the original fixed start; never play."""
from pathlib import Path
import json, runpy, importlib.util, shutil, hashlib, traceback
import unreal as u
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
REVISION='original_workshop_shrine_entry_20261008'

def restore_scene(world, generator, catalog, report):
    aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    original=json.loads((ROOT/'Config/original-entry-actors.json').read_text('utf8'))
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    cache={}
    def asset(path):
        if path not in cache:
            cache[path]=u.load_asset(path)
            if not cache[path]:raise RuntimeError('Original entrance asset missing: '+path)
        return cache[path]
    # Resolve every source before changing the scene; retain the native services.
    for item in original['actors']:
        if item.get('existing_service') and item['label'] not in actors:
            raise RuntimeError('Original service actor missing: '+item['label'])
        if item.get('mesh'):asset(item['mesh'])
        for path in item.get('materials',[]):
            if path:asset(path)
        if item.get('decal'):asset(item['decal']['material'])
    report['restored_actors']=[]
    for item in original['actors']:
        name=item['label'];a=actors.get(name)
        if not a:a=aa.spawn_actor_from_class(getattr(u,item['class_name']),u.Vector(*item['position']))
        if not a:raise RuntimeError('Cannot restore '+name)
        a.modify();a.set_actor_label(name);a.set_folder_path('DungeonStart/OriginalEntry')
        a.set_actor_location_and_rotation(u.Vector(*item['position']),u.Rotator(**item['rotation']),False,True)
        # Retain native service component transforms, meshes and properties.
        if not item.get('existing_service'):a.set_actor_scale3d(u.Vector(*item['scale']))
        a.set_actor_hidden_in_game(False);a.set_is_temporarily_hidden_in_editor(False)
        tags=list(a.tags)
        for tag in item['tags']+[REVISION]:
            if u.Name(tag) not in tags:tags.append(u.Name(tag))
        a.set_editor_property('tags',tags)
        if item.get('mesh'):
            c=a.static_mesh_component;c.modify();c.set_mobility(u.ComponentMobility.STATIC)
            c.set_static_mesh(asset(item['mesh']));c.set_editor_property('override_materials',[])
            for i,path in enumerate(item['materials']):
                if path:c.set_material(i,asset(path))
            c.set_visibility(True);c.set_cast_shadow(item['cast_shadow'])
            c.set_collision_profile_name('BlockAll' if item['collision'] else 'NoCollision')
            a.set_actor_enable_collision(item['collision'])
        if item.get('light'):
            c=a.get_component_by_class(u.LightComponent);c.modify();c.set_mobility(u.ComponentMobility.MOVABLE)
            c.set_editor_property('intensity_units',u.LightUnits.LUMENS)
            for key,value in item['light'].items():
                if key=='color':c.set_light_color(u.LinearColor(*value,1))
                else:c.set_editor_property(key,value)
            c.set_editor_property('max_draw_distance',2200.)
            c.set_editor_property('max_distance_fade_range',500.)
            c.set_visibility(True)
        if item.get('decal'):
            c=a.get_component_by_class(u.DecalComponent);c.modify()
            c.set_decal_material(asset(item['decal']['material']))
            c.set_editor_property('decal_size',u.Vector(*item['decal']['size']))
            c.set_editor_property('sort_order',item['decal']['sort']);c.set_visibility(True)
        report['restored_actors'].append(name)
    for name in original['omitted_retired_labels']:
        if name in actors:
            a=actors[name];a.modify();a.set_actor_hidden_in_game(True)
            a.set_is_temporarily_hidden_in_editor(True);a.set_actor_enable_collision(False)
    # Only the previous prefix preview is disposable. The restored scene persists
    # through generation; it must never receive DungeonRouteGenerated.
    for a in list(u.GameplayStatics.get_all_actors_of_class(world,u.Actor)):
        if a.actor_has_tag('DungeonFacilityEntryPreview'):aa.destroy_actor(a)
    entry=next(m for m in catalog['modules'] if m['id']==catalog['facility_flow']['entrance'])
    for p in entry['parts']:
        a=aa.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*catalog['start_position']),u.Rotator(pitch=0,yaw=0,roll=0))
        a.set_actor_label('FacilityFlow_Entry_'+p['mesh'].rsplit('_',1)[-1])
        a.set_folder_path('Dungeon/FixedEntryPreview');a.set_owner(generator)
        a.set_editor_property('tags',[u.Name('DungeonRouteGenerated'),u.Name('DungeonFacilityEntryPreview')])
        c=a.static_mesh_component;c.set_static_mesh(asset(p['mesh']))
        c.set_collision_profile_name('BlockAll' if p['collision'] else 'NoCollision')

def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ed and ed.get_game_world():raise RuntimeError('Preserve active PIE')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    report=dict(stage='preparing',map=TARGET,revision=REVISION,tests_run=False,generated=False,game_run=False,rendered=False)
    receipt=ROOT/'Receipts/original-entry-restore-20261008.json'
    def record():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    previous=ed.get_editor_world().get_path_name().split('.')[0] if ed and ed.get_editor_world() else None
    try:
        record()
        # Back up the map AND external actor/object packages, not only the umap.
        backup=ROOT/'Snapshots/OriginalEntry20261008'
        report['backups']=[]
        sources=[PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap']
        for category in ('__ExternalActors__','__ExternalObjects__'):
            folder=PROJECT/'Content'/category/'GameMaps/L_Dungeon_Randomized'
            if folder.exists():sources.extend(p for p in folder.rglob('*') if p.is_file())
        for path in sources:
            dest=backup/path.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists():shutil.copy2(path,dest)
            report['backups'].append(str(dest))
        record()
        spec=importlib.util.spec_from_file_location('entry_restore_import',PROJECT/'SourceAssets/DungeonReceptionHall20261006/install.py')
        imp=importlib.util.module_from_spec(spec);spec.loader.exec_module(imp)
        imp.ROOT=ROOT;imp.BASE='/Game/Dungeons/FacilityFlow20261007';imp.OWNER=REVISION
        imp.MAN=json.loads((ROOT/'geometry-open-rear.json').read_text('utf8'))
        imp.report=dict(saved_assets=[]);imp.record=lambda:None
        imp.meshes();report['saved_assets']=imp.report['saved_assets']
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
        generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
        if len(generators)!=1:raise RuntimeError('Expected one production generator')
        g=generators[0];before=g.get_editor_property('module_catalog_json')
        (ROOT/'Sources/entry-restore-live-catalog.json').write_text(before,encoding='utf8')
        if not (backup/'catalog-before.json').exists():(backup/'catalog-before.json').write_text(before,encoding='utf8')
        catalog=runpy.run_path(str(ROOT/'restore_entry_recipe.py'))['extend'](json.loads(before))
        restore_scene(world,g,catalog,report)
        assets={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
        for path in report['saved_assets']:
            a=u.load_asset(path);assets[a.get_path_name()]=a
        g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
        g.set_editor_property('module_assets',list(assets.values()))
        g.set_editor_property('tags',[t for t in g.tags if str(t) not in ('DungeonAssembly.Ready','DungeonAssembly.Failed')])
        report['stage']='scene_authored';record()
        dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
        owned=[p for p in dirty if p.get_name()==TARGET or any(p.get_name().lower().startswith('/game/'+folder+'/gamemaps/l_dungeon_randomized/') for folder in ('__externalactors__','__externalobjects__'))]
        if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Original entry actor package save failed')
        if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Original entry map save failed')
        (ROOT/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
        (ROOT/'Config/layout-bank-v1.json').write_text(json.dumps(catalog['facility_flow']['layout_bank'],ensure_ascii=False,separators=(',',':')),encoding='utf8')
        report.update(stage='map_saved',start_socket_cm=catalog['start_position'],player_start_cm=[140,-205,102],
            bank_entries=len(catalog['facility_flow']['layout_bank']['entries']),bank_contract_sha1=catalog['facility_flow']['layout_bank']['contract_sha1'],
            saved_packages=[p.get_name() for p in owned])
        record();print('ORIGINAL_ENTRY_RESTORED_AND_SAVED',len(report['restored_actors']),TARGET)
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if previous and previous!=TARGET and previous.startswith('/Game/') and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
            u.EditorLoadingAndSavingUtils.load_map(previous)

if __name__=='__main__':main()
