"""Remove the treasury floor accent from the saved catalog without generating a layout."""
import json
from datetime import datetime
from pathlib import Path
import unreal as u

PROJECT = Path(__file__).resolve().parents[2]
TARGET = '/Game/GameMaps/L_Dungeon_Randomized'
PLATE = '/Game/Dungeons/Treasure20260922/Meshes/SM_RS_Treasure_Accents'
if Path(u.Paths.project_dir()).resolve() != PROJECT:
    raise RuntimeError('Wrong project')
ue = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue and ue.get_game_world():
    raise RuntimeError('Preserve active play; treasure floor update pending')

def dirty_packages():
    return list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + list(
        u.EditorLoadingAndSavingUtils.get_dirty_content_packages())

initial_dirty = {p.get_name() for p in dirty_packages()}
if any('/gamemaps/l_dungeon_randomized' in name.lower() for name in initial_dirty):
    raise RuntimeError('Preserve unsaved dungeon changes')
world = ue.get_editor_world() if ue else None
if not world or world.get_path_name().split('.')[0] != TARGET:
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Preserve unsaved current map')
    world = u.EditorLoadingAndSavingUtils.load_map(TARGET)
if not world:
    raise RuntimeError('Cannot load dungeon catalog')
generators = u.GameplayStatics.get_all_actors_of_class(world, u.AuthoredDungeonGenerator)
if len(generators) != 1:
    raise RuntimeError('Expected one saved dungeon generator')
generator = generators[0]
previous = generator.get_editor_property('module_catalog_json')
catalog = json.loads(previous)
treasure = next(m for m in catalog['modules'] if m['id'] == 'Treasure')
receipt_dir = PROJECT / 'Saved/TreasureFloorRemoval' / datetime.now().strftime('%Y%m%d-%H%M%S')
receipt_dir.mkdir(parents=True, exist_ok=False)
(receipt_dir / 'catalog-before.json').write_text(previous, encoding='utf-8')
old_parts = treasure['parts']
treasure['parts'] = [p for p in old_parts if p['mesh'].split('.')[0] != PLATE]
removed_parts = len(old_parts) - len(treasure['parts'])
chest_delta = 0.0
for prop in treasure.get('props', []):
    if prop.get('role') == 'treasure_chest' and abs(prop['position'][2] - 0.8) < 0.001:
        chest_delta = -0.8
        prop['position'][2] = 0

generator.modify()
generator.set_editor_property('module_catalog_json', json.dumps(catalog, ensure_ascii=False))
generator.set_editor_property('module_assets', [a for a in generator.get_editor_property('module_assets')
    if a and a.get_path_name().split('.')[0] != PLATE])

# Update only existing generated preview components, without rebuilding the dungeon.
cleared_components = []
lowered_chests = []
for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
    if not actor.actor_has_tag('DungeonRouteGenerated'):
        continue
    for component in actor.get_components_by_class(u.StaticMeshComponent):
        mesh = component.get_editor_property('static_mesh')
        if mesh and mesh.get_path_name().split('.')[0] == PLATE:
            actor.modify()
            component.modify()
            component.set_static_mesh(None)
            cleared_components.append(component.get_path_name())
    if chest_delta and actor.actor_has_tag('DungeonTreasureChest') and any(
            str(tag).startswith('DungeonModule.') and str(tag).endswith('.Treasure')
            for tag in actor.get_editor_property('tags')):
        actor.modify()
        location = actor.get_actor_location()
        location.z += chest_delta
        actor.set_actor_location(location, False, True)
        lowered_chests.append(actor.get_path_name())

owned = [p for p in dirty_packages() if p.get_name() not in initial_dirty
    and '/gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if not owned or not u.EditorLoadingAndSavingUtils.save_packages(owned, False):
    raise RuntimeError('Treasure floor package save failed')

# Keep the production catalog export in step with the saved generator.
(PROJECT / 'SourceAssets/DungeonRoutes20260922/Config/catalog.json').write_text(
    json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
receipt = dict(stage='saved', map=TARGET, removed_catalog_parts=removed_parts,
    chest_height_cm=0, cleared_preview_components=cleared_components,
    lowered_preview_chests=lowered_chests,
    saved_packages=[p.get_name() for p in owned], tests_run=False)
(receipt_dir / 'saved.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('TREASURE_FLOOR_REMOVED ' + json.dumps(receipt, ensure_ascii=False))
