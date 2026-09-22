"""Read-only verification of the built dungeon level: what is actually in the map."""
import json
import collections
import unreal as u

LEVEL = '/Game/GameMaps/L_Dungeon_Prototype'
editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
if not editor.load_level(LEVEL):
    raise RuntimeError('load_level failed')

actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()

report = {'total_actors': len(actors), 'by_class': {}, 'folders': collections.Counter(),
          'mesh_actors': 0, 'missing_mesh': [], 'bounds': None, 'world_partition': None}

mn = [1e9, 1e9, 1e9]
mx = [-1e9, -1e9, -1e9]
for a in actors:
    cls = a.get_class().get_name()
    report['by_class'][cls] = report['by_class'].get(cls, 0) + 1
    folder = str(a.get_folder_path())
    if folder and folder != '/':
        report['folders'][folder] += 1
    if isinstance(a, u.StaticMeshActor):
        report['mesh_actors'] += 1
        mesh = a.static_mesh_component.static_mesh
        if mesh is None:
            report['missing_mesh'].append(a.get_actor_label())
        try:
            o, e = a.get_actor_bounds(False)
            for k in range(3):
                mn[k] = min(mn[k], o[k] - e[k])
                mx[k] = max(mx[k], o[k] + e[k])
        except Exception:
            pass

report['folders'] = dict(report['folders'])
report['bounds'] = {'min': [round(v, 1) for v in mn], 'max': [round(v, 1) for v in mx]}
try:
    ws = world.get_world_settings()
    report['world_partition'] = str(ws.get_editor_property('world_partition_settings') is not None)
    report['default_game_mode'] = str(ws.get_editor_property('default_game_mode'))
except Exception as e:
    report['world_partition'] = 'err ' + str(e)

# Stair opening must be empty on floor 1, and the stair piece must exist.
labels = {a.get_actor_label() for a in actors}
report['has_stairs'] = 'stairs_up' in labels
report['hole_cell_empty'] = 'landing1_floor_7_1' not in labels
report['door_count'] = len([l for l in labels if l.startswith('bdoorframe_')])
report['wall_count'] = len([l for l in labels if l.startswith('bwall_')])
report['player_start'] = 'DungeonStart' in labels

u.log('DUNGEON_VERIFY ' + json.dumps(report))