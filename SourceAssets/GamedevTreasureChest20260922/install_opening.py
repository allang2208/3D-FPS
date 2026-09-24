"""Add the continuous animation reference to the saved dungeon without regenerating it."""
import json
from pathlib import Path
import unreal as u

HERE = Path(__file__).parent
PROJECT = HERE.parents[1]
TARGET = '/Game/GameMaps/L_Dungeon_Randomized'
UE = u.get_editor_subsystem(u.UnrealEditorSubsystem)
ED = u.get_editor_subsystem(u.LevelEditorSubsystem)
AA = u.get_editor_subsystem(u.EditorActorSubsystem)
if UE.get_game_world():
    raise RuntimeError('Map integration needs editor mode; preserve the running game.')
previous = UE.get_editor_world().get_path_name().split('.')[0]
if previous != TARGET:
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Cannot switch away from an unsaved map')
    if not ED.load_level(TARGET):
        raise RuntimeError('Cannot load target dungeon')
config = json.loads((PROJECT/'Content/ColdSteelData/treasure_chest_assets.json').read_text(encoding='utf-8-sig'))
opening = u.load_asset(config['opening'])
if not opening:
    raise RuntimeError('Continuous opening asset unavailable')
generator = next((a for a in AA.get_all_level_actors()
                  if a.get_class().get_name() == 'AuthoredDungeonGenerator'
                  and a.get_actor_label() == 'DGN_RouteGenerator'),None)
if generator is None:
    raise RuntimeError('Target route generator unavailable')
catalog = json.loads(generator.get_editor_property('module_catalog_json'))
count = 0
for module in catalog['modules']:
    for prop in module.get('props',[]):
        if prop.get('role') == 'treasure_chest':
            prop['opening_animation'] = opening.get_path_name()
            count += 1
if not count:
    raise RuntimeError('No treasure entries in the target generator')
references = {a.get_path_name():a for a in generator.get_editor_property('module_assets') if a}
references[opening.get_path_name()] = opening
generator.modify()
generator.set_editor_property('module_catalog_json',json.dumps(catalog))
generator.set_editor_property('module_assets',list(references.values()))
dirty = list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned = [p for p in dirty if '/gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):
    raise RuntimeError('Dungeon package save failed')
if not ED.save_current_level():
    raise RuntimeError('Dungeon map save failed')
receipt = dict(map=TARGET,opening=opening.get_path_name(),catalog_entries=count,
               saved=True,regenerated=False,tested=False)
(HERE/'opening_install_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('TREASURE_OPENING_MAP_SAVED '+json.dumps(receipt))
if previous != TARGET:
    ED.load_level(previous)
