"""Blender (background): A762 defects in the seated (runtime idle) pose. Diagnostic only.

blender -b --factory-startup -P diagnose_seated.py -- <out_dir> [--repair <repair.json>]

Builds the gun (arms excluded) from the bind-pose dump moved into the idle pose
(seated.py), then
- counts see-through faces: first hits of orthographic rays from 642 directions whose
  geometric normal faces away from the viewer (culled by the single-sided materials);
- renders Workbench close-ups with backface culling on, colour per slot
  (receiver grey, trigger green, bolt purple, magazine blue, grip orange, rebuilt blue-grey),
  see-through faces yellow.
With --repair, applies a repair plan (deleted triangles, moved vertices, added parts)
before diagnosing, so the result can be compared with the current mesh.
Coordinates: Blender object = UE cm with Y mirrored.
"""
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import seated  # noqa: E402

args = sys.argv[sys.argv.index('--') + 1:]
out_dir = Path(args[0])
out_dir.mkdir(parents=True, exist_ok=True)
repair = json.loads(Path(args[args.index('--repair') + 1]).read_text(encoding='utf-8')) if '--repair' in args else None

h, pos, st, tri, mat, bone, gun = seated.load()
names = h['slots']
pts = st.copy()
keep = gun.copy()
extra_v, extra_t, extra_m = [], [], []
if repair:
    for vid, p in repair.get('move_vertices', {}).items():
        v = int(vid)
        # Moves are authored in bind pose; seat them like their vertex.
        pts[v] = seated.seat_points(np.array([p]), bone[v])[0]
    keep[np.array(repair.get('delete_triangles', []), dtype=int)] = False
    for part in (repair.get('add_parts', []) if '--no-parts' not in args else []):
        base = len(pts) + len(extra_v)
        extra_v.extend(part['vertices'])
        extra_t.extend([[base + i for i in t] for t in part['triangles']])
        extra_m.extend([names.index(part['slot'])] * len(part['triangles']))
if extra_v:
    pts = np.vstack([pts, np.array(extra_v)])
tris = np.vstack([tri[keep]] + ([np.array(extra_t)] if extra_t else []))
mats = np.concatenate([mat[keep]] + ([np.array(extra_m)] if extra_m else []))
if '--hide' in args:
    hide = [names.index(s) for s in args[args.index('--hide') + 1].split(',')]
    sel = ~np.isin(mats, hide)
    tris, mats = tris[sel], mats[sel]
if '--two-sided' in args:
    # Emulate two-sided material overrides: add reversed copies of those slots' triangles.
    two = [names.index(s) for s in args[args.index('--two-sided') + 1].split(',')]
    sel = np.isin(mats, two)
    tris = np.vstack([tris, tris[sel][:, [0, 2, 1]]])
    mats = np.concatenate([mats, mats[sel]])
co = pts * np.array([1.0, -1.0, 1.0])
# UE's left-handed frame mirrored into Blender's right-handed one keeps the dump winding
# outward (checked: first hits are overwhelmingly front-facing).
tris_bl = tris

me = bpy.data.meshes.new('A762_SEATED')
me.from_pydata(co.tolist(), [], tris_bl.tolist())
me.update()
ob = bpy.data.objects.new('A762_SEATED', me)
bpy.context.scene.collection.objects.link(ob)
F = len(me.polygons)
P = co[tris_bl]
fn = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
area = 0.5 * np.linalg.norm(fn, axis=1)
fn /= np.maximum(2 * area, 1e-12)[:, None]

tree = BVHTree.FromPolygons([tuple(p) for p in co], tris_bl.tolist(), all_triangles=True)
lo, hi = co[np.unique(tris_bl)].min(0), co[np.unique(tris_bl)].max(0)
center = Vector(((lo + hi) / 2).tolist())
radius = float(np.linalg.norm(hi - lo) / 2) * 1.05
front = np.zeros(F, np.int32)
back = np.zeros(F, np.int32)
golden = math.pi * (3 - math.sqrt(5))
n_dirs, grid = 642, 120
for i in range(n_dirs):
    y = 1 - 2 * (i + 0.5) / n_dirs
    r = math.sqrt(1 - y * y)
    d = Vector((math.cos(golden * i) * r, y, math.sin(golden * i) * r))
    u = d.orthogonal().normalized()
    v = d.cross(u)
    dn = np.array(d[:])
    for a in np.linspace(-radius, radius, grid):
        for b in np.linspace(-radius, radius, grid):
            hit, _, index, _ = tree.ray_cast(center - d * radius * 2 + u * a + v * b, d, radius * 4)
            if hit is None:
                continue
            if np.dot(fn[index], dn) > 0:
                back[index] += 1
            else:
                front[index] += 1
see = (back > 0) & (back >= front)
print('ORIENTATION front-hits %d back-hits %d' % (front.sum(), back.sum()), flush=True)
report = {'repair': bool(repair), 'triangles': int(F), 'front_hits': int(front.sum()), 'back_hits': int(back.sum()), 'slots': {}}
for idx in np.unique(mats):
    s = mats == idx
    e = {'faces': int(s.sum()), 'see_through_faces': int((s & see).sum()),
         'see_through_area_cm2': round(float(area[s & see].sum()), 3)}
    if (s & see).any():
        q = P[s & see].reshape(-1, 3) * np.array([1, -1, 1])
        e['see_through_bbox_ue'] = [round(float(x), 2) for x in (*q.min(0), *q.max(0))]
    report['slots'][names[idx]] = e
    if e['see_through_faces']:
        print('SEE_THROUGH', names[idx].ljust(30), e, flush=True)
tag = 'repaired' if repair else 'current'
(out_dir / ('seated_diagnosis_%s.json' % tag)).write_text(json.dumps(report, indent=1), encoding='utf-8')

palette = {'M_A762_Receiver': (0.6, 0.6, 0.6), 'M_A762_Bolt': (0.75, 0.3, 0.8), 'M_A762_Trigger': (0.15, 0.7, 0.25),
           'M_A762_FactoryRearGrip': (0.85, 0.5, 0.15), 'M_A762_Magazine_Rebuilt': (0.3, 0.45, 0.85),
           'M_A762_MagazineEdge_Rebuilt': (0.2, 0.35, 0.75), 'M_A762_MagazineInside_Rebuilt': (0.1, 0.2, 0.5),
           'M_A762_FrontAssembly_Rebuilt': (0.55, 0.85, 0.9), 'M_A762_UpperReceiver03': (0.5, 0.45, 0.7),
           'M_A762_SightInner': (0.3, 0.3, 0.3), 'M_A762_Inside': (0.2, 0.2, 0.2)}
color = np.tile(np.array([0.55, 0.6, 0.62, 1.0]), (F, 1))
for name, rgb in palette.items():
    if name in names:
        color[mats == names.index(name)] = [*rgb, 1.0]
attr = me.color_attributes.new('DIAG', 'FLOAT_COLOR', 'CORNER')
me.color_attributes.active_color = attr

scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
sh = scene.display.shading
sh.light = 'STUDIO'
sh.color_type = 'VERTEX'
sh.show_backface_culling = True
scene.render.resolution_x, scene.render.resolution_y = 1600, 900
scene.render.film_transparent = False
cam_data = bpy.data.cameras.new('DiagCam')
cam_data.type = 'ORTHO'
cam = bpy.data.objects.new('DiagCam', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
# Views in UE cm (target, view direction from target towards camera, up axis, width).
views = {
    'junction_left': ((5.3, -23.5, -8.0), (-1, 0, 0), 16.0),
    'junction_right': ((5.3, -23.5, -8.0), (1, 0, 0), 16.0),
    'junction_left_low': ((5.3, -23.5, -8.0), (-1, 0, -0.6), 16.0),
    'junction_right_low': ((5.3, -23.5, -8.0), (1, 0, -0.6), 16.0),
    'body_left': ((5.3, -22.0, -6.0), (-1, 0, 0), 36.0),
    'body_right': ((5.3, -22.0, -6.0), (1, 0, 0), 36.0),
    'collar_zoom_right': ((6.9, -24.5, -6.8), (1, 0, 0), 5.0),
    'collar_zoom_left': ((3.9, -24.5, -6.8), (-1, 0, 0), 5.0),
    'rear_zoom_right': ((6.9, -19.6, -8.4), (1, 0, 0), 5.0),
    'rear_zoom_left': ((3.9, -19.6, -8.4), (-1, 0, 0), 5.0),
}
if '--views' in args:
    wanted = args[args.index('--views') + 1].split(',')
    views = {k: v for k, v in views.items() if k in wanted}
if '--probe' in args:
    # --probe view:px,py;px,py...  prints the slot and UE position under given pixels.
    view_name, spec = args[args.index('--probe') + 1].split(':')
    target, side, width = views[view_name]
    t = Vector((target[0], -target[1], target[2]))
    d = Vector((side[0], -side[1], side[2])).normalized()
    rot = (-d).to_track_quat('-Z', 'Y').to_matrix()
    right, up = rot.col[0], rot.col[1]
    res_x, res_y = scene.render.resolution_x, scene.render.resolution_y
    for pair in spec.split(';'):
        px, py = [float(v) for v in pair.split(',')]
        ox = (px / res_x - 0.5) * width
        oy = (0.5 - py / res_y) * width * res_y / res_x
        origin = t + d * 80 + right * ox + up * oy
        hit, _, index, _ = tree.ray_cast(origin, -d, 400)
        if hit is None:
            print('PROBE', pair, 'miss', flush=True)
        else:
            print('PROBE', pair, names[mats[index]], 'tri', index, 'ue', [round(hit.x, 3), round(-hit.y, 3), round(hit.z, 3)], flush=True)
marked = color.copy()
marked[see] = [1.0, 0.85, 0.0, 1.0]
for variant, colours in (('slots', color), ('seethrough', marked)):
    attr.data.foreach_set('color', np.repeat(colours, 3, axis=0).astype(np.float32).ravel())
    me.update()
    for name, (target, side, width) in views.items():
        t = Vector((target[0], -target[1], target[2]))
        d = Vector((side[0], -side[1], side[2])).normalized()
        cam.location = t + d * 80
        # Look at the target with world Z up.
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        cam_data.ortho_scale = width
        cam_data.clip_end = 400
        scene.render.filepath = str(out_dir / ('%s_%s_%s.png' % (tag, variant, name)))
        bpy.ops.render.render(write_still=True)
print('SEATED_DIAGNOSIS_DONE', tag, flush=True)
