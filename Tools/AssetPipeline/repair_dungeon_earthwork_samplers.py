"""Repair/save only the four dungeon parents with recorded sampler compiler errors."""
import json
import importlib.util
from pathlib import Path
import unreal as u

project = Path('D:/FPS3D/FPSGAME')
source = project / 'SourceAssets/DungeonRuinEarthwork20260921'
spec = importlib.util.spec_from_file_location('dungeon_earthwork_materials', source / 'Scripts/earthwork_materials.py')
graphs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graphs)
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Gameplay is active; material repair was not started')
recipes = json.loads((source / 'Authored/manifest.json').read_text())['materials']
receipt = {'materials': {}, 'source_textures_modified': False, 'tests_run': False}
receipt_path = project / 'Saved/DungeonV4_20260926/earthwork-material-repair.json'
for name in ('Ridge', 'Gravel', 'Pebbles', 'PebblePatch'):
    path = '/Game/Dungeons/AtmosphereV2/RoomInteriors/Earthwork/Materials/M_Earth_' + name
    material = u.load_asset(path)
    if material is None:
        raise RuntimeError('Missing dungeon material: ' + path)
    samplers = graphs.build_graph(material, name, recipes[name], recipes)
    if not u.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Could not save: ' + path)
    receipt['materials'][name] = {'path': path, 'samplers': samplers, 'saved': True}
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('DUNGEON_EARTHWORK_SAVED ' + json.dumps(receipt))
