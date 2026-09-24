"""Read installed boss navigation inputs without starting play or saving assets."""
import json
from pathlib import Path
import unreal as u

root = Path(__file__).resolve().parents[1]
def properties(obj, names):
    values = {}
    for name in names:
        try:
            values[name] = str(obj.get_editor_property(name))
        except Exception:
            pass
    return values

report = {'meshes': {}, 'runtime_tested': False}
for kind in ('Floors', 'GalleryDeck', 'StairWest', 'StairEast', 'GalleryRails'):
    mesh = u.load_asset('/Game/Dungeons/BossHall20260922/Meshes/SM_RS_BossPumpHall_'+kind)
    body = mesh.get_editor_property('body_setup')
    report['meshes'][kind] = {
        'body': properties(body, ['collision_trace_flag']),
        'nanite': str(mesh.get_editor_property('nanite_settings')),
        'navigation': properties(mesh, ['has_navigation_data', 'nav_collision']),
    }
nav = u.get_default_object(u.RecastNavMesh)
report['recast_defaults'] = properties(nav, ['nav_mesh_resolution_params', 'agent_radius', 'agent_height', 'default_query_extent', 'runtime_generation'])
boss = u.get_default_object(u.load_class(None, '/Game/Monsters/HandBrain/BP_HandBrain.BP_HandBrain_C'))
report['boss'] = properties(boss, ['walk_speed', 'aggro_radius', 'leash_radius'])
report['movement'] = properties(boss.get_editor_property('character_movement'), ['nav_agent_props', 'max_step_height'])
path = root/'Receipts/navigation-inputs-20260923.json'
path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('BOSS_NAVIGATION_INPUTS', json.dumps(report), flush=True)
