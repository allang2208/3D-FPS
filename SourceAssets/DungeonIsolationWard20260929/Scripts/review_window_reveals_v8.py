"""Requested seam investigation on actual FBX or saved UE mesh triangles; no rendering.

Run in background Blender. UE readback is converted to author metres by its exporter.
Rays sample the mating planes away from bevels, through the full concrete depth.
"""
import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--ue-triangles', type=Path)
parser.add_argument('--output', required=True, type=Path)
parser.add_argument('--expect-fixed', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
cfg = json.loads((ROOT / 'Config/room.json').read_text(encoding='utf-8'))
trees = {}
stats = {}
bpy.ops.wm.read_factory_settings(use_empty=True)
ue_data = json.loads(args.ue_triangles.read_text(encoding='utf-8')) if args.ue_triangles else None
for kind in ('Walls', 'Frames', 'WindowGaskets'):
    if ue_data:
        triangles = ue_data['meshes'][kind]['triangles_m']
        # Keep UE centimetre precision when converting to metres. Casting to
        # float32 Vector here can collapse the smallest bevel triangles at
        # 30 m from the origin even though their saved vertices are distinct.
        vertices = [tuple(v) for triangle in triangles for v in triangle]
        faces = [(i, i + 1, i + 2) for i in range(0, len(vertices), 3)]
    else:
        bpy.ops.import_scene.fbx(filepath=str(ROOT / 'Authored' / ('SM_Ward_' + kind + '.fbx')))
        obj = next(o for o in bpy.context.selected_objects if o.type == 'MESH')
        vertices = [obj.matrix_world @ v.co for v in obj.data.vertices]
        faces = [tuple(f.vertices) for f in obj.data.polygons]
    seen = set()
    duplicate = degenerate = 0
    for f in faces:
        a, b, c = [vertices[i] for i in f]
        ab = [float(b[i])-float(a[i]) for i in range(3)]
        ac = [float(c[i])-float(a[i]) for i in range(3)]
        cross = (ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0])
        degenerate += sum(t*t for t in cross) < 1e-20
        key = tuple(sorted(tuple(round(float(t), 6) for t in vertices[i]) for i in f))
        duplicate += key in seen
        seen.add(key)
    stats[kind] = dict(triangles=len(faces), duplicate_triangles=duplicate, degenerate_triangles=degenerate)
    trees[kind] = BVHTree.FromPolygons(vertices, faces, all_triangles=True)


def hit(kind, start, direction):
    position, _, _, distance = trees[kind].ray_cast(Vector(start), Vector(direction), 4.0)
    if position is None:
        raise RuntimeError(f'Missing {kind} surface from {start} toward {direction}')
    return position, distance


edges = []
finished_sizes = []
gaskets = []
mullions = []
for room in cfg['rooms']:
    cx = room['window_x']
    cy = 4.5 if room['id'].startswith('N') else -4.5
    lo, hi, bottom, top = cx-1.7, cx+1.7, 1.55, 2.88
    # Six independent samples per edge, including both sides of the concrete reveal.
    samples = {
        'top': [((cx+dx, cy+dy, 2.3), (0, 0, 1)) for dx in (-.65, .65) for dy in (-.10, 0, .10)],
        'bottom': [((cx+dx, cy+dy, 2.3), (0, 0, -1)) for dx in (-.65, .65) for dy in (-.10, 0, .10)],
        'left': [((cx-.4, cy+dy, z), (-1, 0, 0)) for z in (1.95, 2.45) for dy in (-.10, 0, .10)],
        'right': [((cx+.4, cy+dy, z), (1, 0, 0)) for z in (1.95, 2.45) for dy in (-.10, 0, .10)],
    }
    for edge, probes in samples.items():
        gaps = [(hit('Walls', p, d)[1] - hit('Frames', p, d)[1])*1000 for p, d in probes]
        edges.append(dict(room=room['id'], edge=edge, samples=len(gaps),
                          min_clearance_mm=round(min(gaps), 4), max_clearance_mm=round(max(gaps), 4)))
    left = hit('Frames', (cx-.4, cy, 2.3), (-1, 0, 0))[0].x
    right = hit('Frames', (cx+.4, cy, 2.3), (1, 0, 0))[0].x
    low = hit('Frames', (cx+.65, cy, 2.3), (0, 0, -1))[0].z
    high = hit('Frames', (cx+.65, cy, 2.3), (0, 0, 1))[0].z
    finished_sizes.append(dict(room=room['id'], width_m=round(right-left, 6), height_m=round(high-low, 6)))
    # Gasket outer caps are deliberately buried in the frame instead of sharing its inner plane.
    outside = (
        ('top', (cx+.65, cy, top+.10), (0, 0, -1), 2, high, 1),
        ('bottom', (cx+.65, cy, bottom-.10), (0, 0, 1), 2, low, -1),
        ('left', (lo-.10, cy, 2.3), (1, 0, 0), 0, left, -1),
        ('right', (hi+.10, cy, 2.3), (-1, 0, 0), 0, right, 1),
    )
    for edge, p, d, axis, frame_plane, sign in outside:
        inset = (hit('WindowGaskets', p, d)[0][axis] - frame_plane)*sign*1000
        gaskets.append(dict(room=room['id'], edge=edge, buried_cap_mm=round(inset, 4)))
    gasket_top = hit('WindowGaskets', (cx+.65, cy, 2.3), (0, 0, 1))[0].z
    gasket_bottom = hit('WindowGaskets', (cx+.65, cy, 2.3), (0, 0, -1))[0].z
    mullion_top = hit('Frames', (cx, cy, top-.005), (0, 0, -1))[0].z
    mullion_bottom = hit('Frames', (cx, cy, bottom+.005), (0, 0, 1))[0].z
    mullions.append(dict(room=room['id'], top_buried_cap_mm=round((mullion_top-gasket_top)*1000, 4),
                         bottom_buried_cap_mm=round((gasket_bottom-mullion_bottom)*1000, 4)))

rear_edges = []
for room in cfg['rooms']:
    if 'rear_door_x' not in room:
        continue
    cx, cy = room['rear_door_x'], 12.5
    for edge, p, d in (
        ('top', (cx, cy, 2.5), (0, 0, 1)),
        ('left', (cx, cy, 1.5), (-1, 0, 0)),
        ('right', (cx, cy, 1.5), (1, 0, 0)),
    ):
        gap = (hit('Walls', p, d)[1] - hit('Frames', p, d)[1])*1000
        rear_edges.append(dict(room=room['id'], edge=edge, clearance_mm=round(gap, 4)))

checks = dict(
    window_clearance_5mm=all(4.8 <= e['min_clearance_mm'] <= e['max_clearance_mm'] <= 5.2 for e in edges),
    rear_door_clearance_5mm=all(4.8 <= e['clearance_mm'] <= 5.2 for e in rear_edges),
    finished_openings_unchanged=all(abs(s['width_m']-3.4)<.0001 and abs(s['height_m']-1.33)<.0001 for s in finished_sizes),
    gasket_caps_buried_3mm=all(2.8 <= g['buried_cap_mm'] <= 3.2 for g in gaskets),
    mullion_caps_buried_3mm=all(2.8 <= m[k] <= 3.2 for m in mullions for k in ('top_buried_cap_mm', 'bottom_buried_cap_mm')),
    no_duplicate_or_degenerate_triangles=all(s['duplicate_triangles']==0 and s['degenerate_triangles']==0 for s in stats.values()),
)
receipt = dict(source=str(args.ue_triangles) if ue_data else 'actual exported FBX roundtrip',
               revision=cfg['revision'], units='metres; reported clearances millimetres',
               mesh_stats=stats, window_edges=edges, finished_sizes=finished_sizes,
               gasket_caps=gaskets, mullion_caps=mullions, rear_door_edges=rear_edges,
               checks=checks, passed=all(checks.values()), rendered=False, gameplay_tested=False)
args.output.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('WARD_WINDOW_REVEAL_REVIEW', json.dumps(checks), flush=True)
if args.expect_fixed and not receipt['passed']:
    raise RuntimeError('Requested reveal geometry checks failed; see ' + str(args.output))
