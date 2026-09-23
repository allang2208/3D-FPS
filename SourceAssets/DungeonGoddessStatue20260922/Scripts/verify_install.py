"""Read the saved map back in a fresh process and report what actually persisted.

The project rule is that a same-process read-back proves nothing; this opens
L_Dungeon_AuthoredExpansion from disk, finds the statue actor, and reports the
transform, mesh, material slot, collision and bounds it really has on disk.

Run:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 \
        -nosplash -nullrhi -abslog=<log>
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / 'Config' / 'diana.json').read_text(encoding='utf-8'))
PLACE = CFG['placement']
TARGET = CFG['target_map']

UE = u.get_editor_subsystem(u.UnrealEditorSubsystem)
ED = u.get_editor_subsystem(u.LevelEditorSubsystem)


def vec3(v):
    return [round(float(v.x), 2), round(float(v.y), 2), round(float(v.z), 2)]


def rot3(r):
    return [round(float(r.pitch), 2), round(float(r.yaw), 2), round(float(r.roll), 2)]


report = {'stage': 'verify_readback', 'map': TARGET, 'found': False, 'tests_run': False}
world = UE.get_editor_world()
if not world or world.get_path_name().split('.')[0] != TARGET:
    if not ED.load_level(TARGET):
        raise RuntimeError('Cannot open %s' % TARGET)

matches = []
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    if actor.get_actor_label() == PLACE['actor_label']:
        matches.append(actor)

report['matching_actors'] = len(matches)
if matches:
    actor = matches[0]
    component = actor.static_mesh_component
    mesh = component.static_mesh
    origin, extent = actor.get_actor_bounds(False)
    report.update({
        'found': True,
        'actor': {
            'label': actor.get_actor_label(),
            'class': actor.get_class().get_name(),
            'location_cm': vec3(actor.get_actor_location()),
            'rotation_deg': rot3(actor.get_actor_rotation()),
            'folder': str(actor.get_folder_path()),
            'tags': [str(t) for t in actor.get_editor_property('tags')],
            'mobility': str(component.get_editor_property('mobility')),
            'collision_profile': str(component.get_collision_profile_name()),
            'mesh': mesh.get_path_name() if mesh else None,
            'slot0_material': mesh.get_material(0).get_path_name() if mesh and mesh.get_material(0) else None,
            'material_slots': len(mesh.get_editor_property('static_materials')) if mesh else None,
            'world_bounds_origin_cm': vec3(origin),
            'world_bounds_extent_cm': vec3(extent),
        },
    })
    if mesh:
        bounds = mesh.get_bounds()
        report['mesh_asset'] = {
            'nanite_enabled': bool(mesh.get_editor_property('nanite_settings').enabled),
            'collision_trace_flag': str(mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')),
            'simple_collision_shapes': len(mesh.get_editor_property('body_setup').get_editor_property('agg_geom').get_editor_property('box_elems'))
                                     + len(mesh.get_editor_property('body_setup').get_editor_property('agg_geom').get_editor_property('convex_elems')),
            'asset_size_cm': [round(float(bounds.box_extent.x) * 2, 2), round(float(bounds.box_extent.y) * 2, 2),
                              round(float(bounds.box_extent.z) * 2, 2)],
            'asset_origin_cm': vec3(bounds.origin),
        }
        for attr in ('get_num_triangles', 'get_triangle_count'):
            if hasattr(mesh, attr):
                try:
                    report['mesh_asset']['triangles_lod0'] = int(getattr(mesh, attr)(0))
                    break
                except Exception as exc:  # noqa: BLE001
                    report['mesh_asset']['triangles_lod0'] = 'unavailable: %s' % exc

(ROOT / 'Receipts' / 'verify.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print('GODDESS_STATUE_VERIFY', json.dumps(report, default=str))
