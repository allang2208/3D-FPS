"""Read the production maps and refresh the existing hills portal save, without gameplay.

Run with UnrealEditor-Cmd -run=pythonscript -script=<absolute path> -nullrhi.
The original world save is retained beside the receipt. Never deletes terrain edits.
"""
import json
from pathlib import Path
import secrets
import shutil
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/HillsChapelEntry20261115'
OUT.mkdir(parents=True, exist_ok=True)
RECEIPT = OUT / 'world-refresh.json'
if RECEIPT.exists():
    raise RuntimeError('This refresh already completed; retain its world identity.')

report = {'gameplay_started': False, 'maps_saved': False}
world = u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_TemperateHills_Initial')
if not world:
    raise RuntimeError('Hills map did not load')
actors = u.GameplayStatics.get_all_actors_of_class(world, u.Actor)
hills = [a for a in actors if isinstance(a, u.TemperateHillsWorld)]
if len(hills) != 1:
    raise RuntimeError('Expected one production hills generator')
terrain = hills[0]
assets = terrain.get_editor_property('assets')
report['hills'] = {'actor': terrain.get_path_name(), 'assets': assets.get_path_name(),
                   'size_meters': terrain.get_editor_property('size_meters'),
                   'game_mode': str(world.get_world_settings().get_editor_property('default_game_mode'))}
for name in ('trees', 'rocks', 'graphs', 'grass', 'rainforest_grass', 'rainforest_carpet_grass',
             'forest_ferns', 'rainforest_herbs'):
    report['hills'][name] = [str(v) for v in assets.get_editor_property(name)]
report['weather'] = [{'class': a.get_class().get_path_name(), 'name': a.get_name()}
                     for a in actors if isinstance(a, u.FPSWeatherManager) or 'Ultra_Dynamic' in a.get_class().get_name()]

world = u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_Dungeon_Randomized')
if not world:
    raise RuntimeError('Dungeon map did not load')
generators = u.GameplayStatics.get_all_actors_of_class(world, u.AuthoredDungeonGenerator)
if len(generators) != 1:
    raise RuntimeError('Expected one production dungeon generator')
catalog = json.loads(generators[0].get_editor_property('module_catalog_json'))
shrine = catalog['start_shrine']
if len(shrine['statues']) != 6:
    raise RuntimeError('Shrine pool changed; inspect before reuse')
config = ROOT / 'Content/ColdSteelData/shrines.json'
pool = {'statues': shrine['statues']}
if config.exists() and json.loads(config.read_text(encoding='utf-8-sig')) != pool:
    raise RuntimeError('Preserve existing shared shrine configuration')
config.write_text(json.dumps(pool, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
report['shrine_source'] = generators[0].get_path_name()
report['shrine_pool'] = [v['id'] for v in shrine['statues']]
report['shrine_assets'] = []
for choice in shrine['statues']:
    mesh = u.load_asset(choice['mesh'])
    if not mesh:
        raise RuntimeError('Missing shrine mesh: ' + choice['mesh'])
    report['shrine_assets'].append({'id': choice['id'], 'path': mesh.get_path_name(), 'bounds': str(mesh.get_bounding_box())})

slot = 'TemperateHills_World'
path = ROOT / 'Saved/SaveGames' / (slot + '.sav')
old = u.GameplayStatics.load_game_from_slot(slot, 0)
if old:
    report['previous'] = {key: old.get_editor_property(key) for key in ('seed', 'generator_version')}
    report['previous']['world_id'] = u.GuidLibrary.conv_guid_to_string(old.get_editor_property('world_id'))
    report['previous']['edit_count'] = len(old.get_editor_property('edits'))
    backup = OUT / 'Before/TemperateHills_World.sav'
    if backup.exists():
        if backup.read_bytes() != path.read_bytes():
            raise RuntimeError('World save changed since backup; retain both identities')
    else:
        shutil.copy2(path, backup)
    report['backup'] = str(backup)
seed = secrets.randbelow(2147483646) + 1
while old and seed == old.get_editor_property('seed'):
    seed = secrets.randbelow(2147483646) + 1
save = u.GameplayStatics.create_save_game_object(u.TemperateHillsSave)
save.set_editor_property('version', 3)
save.set_editor_property('seed', seed)
save.set_editor_property('generator_version', 2)
save.set_editor_property('world_id', u.GuidLibrary.new_guid())
if not u.GameplayStatics.save_game_to_slot(save, slot, 0):
    raise RuntimeError('World save failed')
report['current'] = {'slot': slot, 'seed': seed, 'world_id': u.GuidLibrary.conv_guid_to_string(save.get_editor_property('world_id')), 'generator_version': 2}
report['saved'] = True
RECEIPT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('HILLS_CHAPEL_REFRESH ' + json.dumps(report['current']))
