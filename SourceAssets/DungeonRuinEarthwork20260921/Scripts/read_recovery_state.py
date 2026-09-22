"""Read the saved earthwork state after the reported whole-PC freeze; no map writes."""
import json
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonRuinEarthwork20260921')
TARGET = '/Game/GameMaps/L_Dungeon_Prototype'
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
world = editor.get_editor_world()
game_world = editor.get_game_world()
if not world or world.get_path_name().split('.')[0] != TARGET:
    raise RuntimeError('Preserve current map: ' + (world.get_path_name() if world else 'None')
                       + '; gameplay world: ' + (game_world.get_path_name() if game_world else 'None'))
manifest = json.loads((ROOT / 'Authored/manifest.json').read_text())
assets = json.loads((ROOT / 'Receipts/asset-import.json').read_text())
actors = {}
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    actors.setdefault(actor.get_actor_label(), []).append(actor)
state = {
    'map': world.get_path_name(),
    'recorded_at': datetime.now().isoformat(),
    'game_world': game_world.get_path_name() if game_world else None,
    'dirty_maps': [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
    'actors': [], 'old_actors': [], 'issues': [],
    'tests_run': False, 'screenshots_taken': False, 'map_modified': False,
}
for entry in manifest['objects']:
    label = entry['actor']
    found = actors.get(label, [])
    if len(found) != 1:
        state['issues'].append({'actor': label, 'instances': len(found)})
        continue
    actor = found[0]
    component = actor.get_component_by_class(u.StaticMeshComponent)
    mesh = component.static_mesh if component else None
    item = {
        'label': label, 'mesh': mesh.get_path_name() if mesh else None,
        'hidden_in_game': actor.get_editor_property('hidden'),
        'hidden_in_editor': actor.is_temporarily_hidden_in_editor(),
        'visible': component.get_editor_property('visible') if component else False,
        'collision_profile': str(component.get_collision_profile_name()) if component else None,
        'location': list(actor.get_actor_location().to_tuple()),
        'scale': list(actor.get_actor_scale3d().to_tuple()),
        'materials': [component.get_material(i).get_path_name() if component.get_material(i) else None
                      for i in range(component.get_num_materials())] if component else [],
    }
    expected_materials = [assets['materials'][name] for name in entry['materials']]
    if (item['mesh'] != assets['meshes'][entry['name']] or item['hidden_in_game']
            or not item['visible'] or item['materials'] != expected_materials
            or item['collision_profile'] != ('BlockAll' if entry['collision'] else 'NoCollision')):
        state['issues'].append(item)
    state['actors'].append(item)
for label in manifest['hidden_previous']:
    found = actors.get(label, [])
    if len(found) != 1:
        state['issues'].append({'old_actor': label, 'instances': len(found)})
        continue
    actor = found[0]
    component = actor.get_component_by_class(u.StaticMeshComponent)
    item = {'label': label, 'hidden_in_game': actor.get_editor_property('hidden'),
            'visible': component.get_editor_property('visible'),
            'actor_collision': actor.get_actor_enable_collision()}
    if not item['hidden_in_game'] or item['visible'] or item['actor_collision']:
        state['issues'].append(item)
    state['old_actors'].append(item)
destination = ROOT / 'Receipts' / ('recovery-state-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')
destination.write_text(json.dumps(state, indent=2), encoding='utf-8')
print('EARTHWORK_RECOVERY_STATE ' + json.dumps({
    'map': state['map'], 'actors': len(state['actors']),
    'retained_old_actors': len(state['old_actors']),
    'issues': state['issues'], 'dirty_maps': state['dirty_maps'],
    'receipt': str(destination), 'map_modified': False,
}))
