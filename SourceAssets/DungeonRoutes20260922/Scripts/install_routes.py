"""Create the random route map from the approved start, then install native generator."""
import unreal as u,json,gc,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];TARGET='/Game/GameMaps/L_Dungeon_Randomized';SOURCE='/Game/GameMaps/L_Dungeon_AuthoredExpansion'
E=u.EditorAssetLibrary;AA=u.get_editor_subsystem(u.EditorActorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem);UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if UE.get_game_world():raise RuntimeError('Preserve running play before random dungeon integration')
generator_class=u.load_class(None,'/Script/FPSGAME.AuthoredDungeonGenerator');cabinet_class=u.load_class(None,'/Script/FPSGAME.DungeonStorageCabinet')
if not generator_class or not cabinet_class:raise RuntimeError('Regular native build and editor reload are required before writing new classes to the map')
u.get_default_object(generator_class).get_editor_property('layout_manifest_json')
current=UE.get_editor_world().get_path_name().split('.')[0]
if current!=TARGET and u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved current map')
if not E.does_asset_exist(TARGET):
    copy=E.duplicate_asset(SOURCE,TARGET)
    if not copy or not E.save_loaded_asset(copy,False):raise RuntimeError('Cannot preserve the approved start in a new map')
    del copy;gc.collect()
if current!=TARGET and not ED.load_level(TARGET):raise RuntimeError('Cannot open random route map')
catalog=json.loads((ROOT/'Config/catalog.json').read_text(encoding='utf-8'))
fluid=json.loads((ROOT/'Receipts/fluid-materials.json').read_text())
assets={}
for m in catalog['modules']:
    for p in m['parts']:
        if 'PipePusTongue' in p['mesh']:p['materials']=[fluid['M_RoutePusSheet']]
        elif 'PipePusDrops' in p['mesh']:p['materials']=[fluid['M_RoutePusDrops']]
        elif 'PipePusPuddle' in p['mesh']:p['materials']=[fluid['MI_RoutePusPuddle']]
        elif 'PusChannel' in p['mesh']:p['materials']=[fluid['MI_RoutePusChannel']]
        for path in [p['mesh']]+p['materials']:
            if path and path not in assets:
                assets[path]=u.load_asset(path)
                if not assets[path]:raise RuntimeError('Missing authored dependency '+path)
treasure_extension=runpy.run_path(str(ROOT.parent/'DungeonTreasure20260922/Scripts/extend_catalog.py'))
for path in treasure_extension['asset_paths'](catalog):
    if path not in assets:
        assets[path]=u.load_class(None,path) if path.endswith('_C') else u.load_asset(path)
        if not assets[path]:raise RuntimeError('Missing treasure dependency '+path)
actors={a.get_actor_label():a for a in AA.get_all_level_actors()}
g=actors.get('DGN_RouteGenerator') or AA.spawn_actor_from_class(generator_class,u.Vector(0,0,0))
g.modify();g.set_actor_label('DGN_RouteGenerator');g.set_folder_path('DungeonRoutes');g.set_editor_property('module_catalog_json',json.dumps(catalog));g.set_editor_property('module_assets',list(assets.values()));g.set_editor_property('preview_seed',92247);g.set_editor_property('randomize_on_entry',True)
g.call_method('GeneratePreview')
if not g.actor_has_tag('DungeonAssembly.Ready') or g.actor_has_tag('DungeonAssembly.Failed'):raise RuntimeError('Assembly did not complete; do not save partial dungeon contents')
# Only after production generation succeeds, remove the three previous fixed room instances.
for label,a in actors.items():
    if label.startswith(('DGN_RS_','DGN_B_')) or label=='DGN_Prop_GoddessStatue_01':AA.destroy_actor(a)

# Red wheeled tool cabinet: keep authored components and transforms; only change owner/class.
old=next((a for label,a in actors.items() if label.startswith('DGN_A_') and 'ToolCart' in label),None)
storage=actors.get('DGN_Start_WarehouseCabinet')
if not storage:
    if not old:raise RuntimeError('Original red tool cabinet was not found; preserve start layout')
    source=old.get_component_by_class(u.StaticMeshComponent);center,extent=old.get_actor_bounds(False)
    # Original workshop meshes carry world positions in their vertices; keep their transform
    # relative to a cabinet-centred interaction actor, avoiding a reach origin at world zero.
    pivot=u.Vector(center.x,center.y,center.z-extent.z)
    storage=AA.spawn_actor_from_class(cabinet_class,pivot)
    c=storage.get_editor_property('cabinet_mesh');c.set_static_mesh(source.static_mesh);c.set_world_transform(source.get_world_transform(),False,True)
    for i in range(source.get_num_materials()):c.set_material(i,source.get_material(i))
    AA.destroy_actor(old)
storage.modify();storage.set_actor_label('DGN_Start_WarehouseCabinet');storage.set_folder_path('DungeonStart/Workshop')
storage.set_editor_property('tags',list(set(list(storage.tags)+[u.Name('DungeonStorageCabinet'),u.Name('DungeonStart.Warehouse')])));
# Drawer fronts are separate visual detail meshes. Keep them, and make the cabinet body
# the trace target; nearby tools and the rest of the workbench remain untouched.
for label,a in actors.items():
    if label.startswith('DGN_A_') and 'CartDetail' in label:
        c=a.get_component_by_class(u.StaticMeshComponent)
        if c:c.modify();c.set_collision_profile_name('NoCollision')
    if label.startswith('DGN_A_') and ('Workbench' in label or 'EmbeddedPlinth' in label):
        a.modify();a.set_editor_property('tags',list(set(list(a.tags)+[u.Name('DungeonStart.Workbench' if 'Workbench' in label else 'DungeonStart.Shrine')])));

statue=actors.get('DGN_Start_ShrineStatue') or AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector(1910,-995,51),u.Rotator(pitch=0,yaw=90,roll=0))
statue.modify();statue.set_actor_label('DGN_Start_ShrineStatue');statue.set_folder_path('DungeonStart/Shrine');statue.static_mesh_component.set_static_mesh(u.load_asset('/Game/Dungeons/GoddessStatue20260922/Meshes/SM_GoddessStatue_Diana'));statue.static_mesh_component.set_collision_profile_name('BlockAll');statue.set_editor_property('tags',[u.Name('DungeonStart.Shrine'),u.Name('FutureBlessingAndQuest')])
transition_state=runpy.run_path(str(ROOT.parent/'DungeonDoorTransitions20260922/Scripts/apply_start_connection.py'),run_name='__main__')
del transition_state;gc.collect()
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in dirty if '/gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Cannot save random dungeon actors')
if not ED.save_current_level():raise RuntimeError('Cannot save random dungeon map')
(ROOT/'Receipts/install.json').write_text(json.dumps(dict(stage='map_saved',map=TARGET,description=g.get_editor_property('layout_description'),saved_packages=len(owned),tests_run=False),indent=2))
(ROOT/'Receipts/installed-layout.json').write_text(g.get_editor_property('layout_manifest_json'))
print('RANDOM_DUNGEON_MAP_SAVED',g.get_editor_property('layout_description'))
