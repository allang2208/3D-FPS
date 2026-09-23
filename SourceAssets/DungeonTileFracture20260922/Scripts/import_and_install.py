"""Import the eight owned wall revisions and save their existing actor references."""
import json
import re
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[1]
BASE = '/Game/Dungeons/AtmosphereV2/TileFracture'
TARGET = '/Game/GameMaps/L_Dungeon_Prototype'
MAN = json.loads((ROOT/'Authored/geometry-manifest.json').read_text())
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
actors_api = u.get_editor_subsystem(u.EditorActorSubsystem)
level = u.get_editor_subsystem(u.LevelEditorSubsystem)
if not editor or editor.get_game_world():
    raise RuntimeError('Preserve active gameplay; wall installation needs editor mode')
before_dirty_maps = u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
if before_dirty_maps:
    raise RuntimeError('Preserve unsaved map packages: '+', '.join(p.get_path_name() for p in before_dirty_maps))
if Path(u.Paths.project_dir()).resolve() != ROOT.parents[1].resolve():
    raise RuntimeError('Wall installation connected to a different project')
if editor.get_editor_world().get_path_name().split('.')[0] != TARGET:
    if not level.load_level(TARGET):
        raise RuntimeError('Could not open dungeon for the authorized wall edit')
before_dirty_content = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(BASE+'/') for p in before_dirty_content):
    raise RuntimeError('Preserve unsaved edits to wall relief assets')
actors = {a.get_actor_label(): a for a in actors_api.get_all_level_actors()}
targets = []
for entry in MAN['objects']:
    actor = actors.get(entry['actor'])
    comp = actor.get_component_by_class(u.StaticMeshComponent) if actor else None
    if not comp or not comp.static_mesh:
        raise RuntimeError('Required wall actor missing: '+entry['actor'])
    new_path = BASE+'/Meshes/'+entry['name']
    existing = comp.static_mesh.get_path_name()
    if existing not in (entry['previous_mesh'], new_path+'.'+entry['name']):
        raise RuntimeError('Preserve independently replaced wall: '+entry['actor'])
    if any(comp.get_editor_property('override_materials')):
        raise RuntimeError('Preserve material overrides on wall: '+entry['actor'])
    targets.append((entry, actor, comp))
receipt = dict(stage='importing', map=TARGET, meshes={}, actors=[], tests_run=False, screenshots_taken=False)
(ROOT/'Receipts').mkdir(exist_ok=True)


def write():
    (ROOT/'Receipts/install.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def clean(name):
    return re.sub(r'[._][0-9]{3}$', '', name)


if not globals().get('WALL_SKIP_MESH_IMPORT', False):
    import runpy
    runpy.run_path(str(ROOT/'Scripts/import_meshes.py'), run_name='__main__')
mesh_receipt = json.loads((ROOT/'Receipts/meshes.json').read_text())
if mesh_receipt['stage'] != 'meshes_saved':
    raise RuntimeError('Mesh production is not complete')
receipt['meshes'] = mesh_receipt['meshes']

for entry, actor, comp in targets:
    previous = comp.static_mesh.get_path_name()
    actor.modify()
    comp.modify()
    comp.set_static_mesh(u.load_asset(receipt['meshes'][entry['name']]))
    receipt['actors'].append(dict(label=entry['actor'], previous_mesh=previous,
                                  mesh=comp.static_mesh.get_path_name()))
receipt['stage'] = 'scene_changed'
write()
if not level.save_current_level():
    raise RuntimeError('Wall map save failed; retain live scene changes')
receipt.update(stage='map_saved', saved_at=datetime.now().isoformat())
write()
print('CERAMIC_FRACTURE_INSTALLED '+json.dumps(receipt))
