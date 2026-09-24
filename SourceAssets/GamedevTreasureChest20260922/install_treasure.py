"""Swap only treasure-chest visuals/catalogue entries; preserve warehouse actors and loot rules."""
import json,sys
from pathlib import Path
HERE=Path(__file__).parent;PROJECT=HERE.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
config=json.loads((PROJECT/'Content/ColdSteelData/treasure_chest_assets.json').read_text(encoding='utf-8'))
def update_catalog(catalog):
    count=0
    for module in catalog['modules']:
        for prop in module.get('props',[]):
            if prop.get('role')!='treasure_chest':continue
            prop.update(skeletal_mesh=config['mesh'],closed_animation=config['close'],material_overrides=config['materials'],
                        collision_extent=config['collision_extent'],collision_center=config['collision_center'],
                        identity=config['identity'],yaw=90)
            if config.get('opening'):prop['opening_animation']=config['opening']
            count+=1
    return count
catalog_path=PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json'
catalog=json.loads(catalog_path.read_text(encoding='utf-8'));source_count=update_catalog(catalog)
catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
if '--source-only' in sys.argv:
    print('TREASURE_SOURCE_CATALOG_UPDATED '+str(source_count))
    raise SystemExit(0)
import unreal as u
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if UE.get_game_world():raise RuntimeError('Preserve running game; map asset integration needs editor mode.')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps; source catalogue updated, map integration still pending.')
previous=UE.get_editor_world().get_path_name().split('.')[0]
if previous!=TARGET and not ED.load_level(TARGET):raise RuntimeError('Cannot open target dungeon map')
actors=AA.get_all_level_actors()
generator=next((a for a in actors if a.get_class().get_name()=='AuthoredDungeonGenerator' and a.get_actor_label()=='DGN_RouteGenerator'),None)
if generator is None:raise RuntimeError('Route generator not found; preserve map')
catalog=json.loads(generator.get_editor_property('module_catalog_json'));catalog_count=update_catalog(catalog)
if catalog_count==0:raise RuntimeError('No treasure prop to replace; preserve map')
sk=u.load_asset(config['mesh']);closed=u.load_asset(config['close']);opened=u.load_asset(config['open'])
if not all((sk,closed,opened)):raise RuntimeError('Imported treasure dependencies are not available')
references={a.get_path_name():a for a in generator.get_editor_property('module_assets') if a}
for a in (sk,closed,opened):references[a.get_path_name()]=a
if config.get('opening'):
    opening=u.load_asset(config['opening'])
    if not opening:raise RuntimeError('Continuous opening animation not imported')
    references[opening.get_path_name()]=opening
generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(catalog));generator.set_editor_property('module_assets',list(references.values()))
count=0
for actor in actors:
    if u.Name('DungeonTreasureChest') not in actor.tags:continue
    component=actor.get_component_by_class(u.SkeletalMeshComponent)
    if component is None:continue
    actor.modify();component.modify()
    if u.Name('GamedevTreasureChest') not in actor.tags:
        rotation=actor.get_actor_rotation();rotation.yaw+=180;actor.set_actor_rotation(rotation,False)
    actor.set_editor_property('tags',list(dict.fromkeys(list(actor.tags)+[u.Name('GamedevTreasureChest')])))
    component.set_skeletal_mesh_asset(sk);component.set_editor_property('override_materials',[])
    component.play_animation(closed,False);component.set_position(0.0,False);component.set_play_rate(0.0);component.set_component_tick_enabled(False)
    for box in actor.get_components_by_class(u.BoxComponent):
        box.modify();box.set_box_extent(u.Vector(*config['collision_extent']),False)
        box.set_relative_location(u.Vector(*config['collision_center']),False,False)
    count+=1
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in dirty if '/gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Dungeon package save failed')
if not ED.save_current_level():raise RuntimeError('Dungeon map save failed')
receipt=dict(map=TARGET,saved=True,catalog_entries=catalog_count,existing_chests_updated=count,source_entries=source_count,
             warehouse_changed=False,loot_rules_changed=False,preview_regenerated=False,tested=False)
(HERE/'install_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('TREASURE_MAP_SAVED '+json.dumps(receipt))
if previous!=TARGET:ED.load_level(previous)
