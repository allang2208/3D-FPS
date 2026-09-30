"""Blender (background): diagnostic before/after views of the A762 geometry plans (not a look render).

blender -b --factory-startup -P preview_geometry.py -- <out_dir> [before|after]
Seated pose, custom split normals, Workbench studio light with specular, uniform grey, so
surface lumps, facets and bevels show as they would in a satin highlight.
"""
import array
import json
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import seated  # noqa: E402

args = sys.argv[sys.argv.index('--') + 1:]
out_dir, mode = Path(args[0]), args[1]
out_dir.mkdir(parents=True, exist_ok=True)
KEY = 'A762_AfterRepair'
h, pos, st, tri, mat, bone, gun = seated.load(KEY)
_, _, _, _, _, nrm = seated.read_geometry(seated.GEOMETRY / (KEY + '.bin'))
P = st.copy()
N = nrm.astype(np.float64).copy()
keep = gun.copy()
extra_p, extra_t, extra_n = [], [], []
if mode == 'after':
    with open(HERE / 'Bake' / 'denoise_plan.bin', 'rb') as f:
        head = json.loads(f.readline())
        buf = f.read()
    o = 0

    def take(code, n):
        global o
        a = np.frombuffer(buf, dtype=code, count=n, offset=o)
        o += a.nbytes
        return a
    moved = take(np.int32, head['moved'])
    mp = take(np.float32, head['moved'] * 3).reshape(-1, 3)
    for b in np.unique(bone[moved]):
        s = bone[moved] == b
        P[moved[s]] = seated.seat_points(mp[s], b)
    nt = take(np.int32, head['normal_triangles'])
    N[nt] = take(np.float32, head['normal_triangles'] * 9).reshape(-1, 3, 3)
    with open(HERE / 'Bake' / 'rebuild_parts.bin', 'rb') as f:
        head = json.loads(f.readline())
        buf = f.read()
    o = 0
    slot_bone = {}
    for i, s in enumerate(h['slots']):
        v = np.unique(tri[mat == i])
        if len(v):
            slot_bone[s] = bone[v[0]]
    for part in head['parts']:
        pp = take(np.float32, part['vertices'] * 3).reshape(-1, 3).astype(np.float64)
        tt = take(np.int32, part['triangles'] * 3).reshape(-1, 3)
        nn = take(np.float32, part['triangles'] * 9).reshape(-1, 3, 3)
        take(np.float32, part['triangles'] * 6)
        if part['mode'] == 'replace':
            keep &= mat != h['slots'].index(part['slot'])
        b = slot_bone[part['slot']]
        Rm = seated.seat_points(np.eye(3) + 0.0, b) - seated.seat_points(np.zeros((1, 3)), b)
        extra_t.append(tt + len(P) + sum(len(x) for x in extra_p))
        extra_p.append(seated.seat_points(pp, b))
        extra_n.append(nn @ Rm)
T = np.vstack([tri[keep]] + extra_t)
V = np.vstack([P] + extra_p) * np.array([1.0, -1.0, 1.0])
CN = np.concatenate([N[keep]] + extra_n) * np.array([1.0, -1.0, 1.0])
me = bpy.data.meshes.new('A762')
me.from_pydata(V.tolist(), [], T.tolist())
me.update()
me.shade_smooth()
me.normals_split_custom_set(CN.reshape(-1, 3).tolist())
ob = bpy.data.objects.new('A762', me)
bpy.context.scene.collection.objects.link(ob)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'SINGLE'
sh.single_color = (0.55, 0.56, 0.58)
sh.show_specular_highlight = True
sh.show_backface_culling = False
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
cam_data = bpy.data.cameras.new('C')
cam_data.type = 'ORTHO'
cam = bpy.data.objects.new('C', cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
views = {'receiver_left': ((5.3, -22.0, -5.0), (-1, 0, 0.25), 30.0),
         'receiver_right': ((5.3, -22.0, -5.0), (1, 0, 0.25), 30.0),
         'front_detail': ((5.3, -31.0, -4.0), (-1, -0.2, 0.3), 9.0),
         'stock': ((5.3, 6.0, -6.0), (1, 0, 0.2), 30.0),
         'muzzle': ((5.3, -60.0, -3.0), (-1, 0, 0.2), 30.0)}
for name, (target, side, width) in views.items():
    t = Vector((target[0], -target[1], target[2]))
    d = Vector((side[0], -side[1], side[2])).normalized()
    cam.location = t + d * 80
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cam_data.ortho_scale = width
    cam_data.clip_end = 400
    sc.render.filepath = str(out_dir / ('%s_%s.png' % (mode, name)))
    bpy.ops.render.render(write_still=True)
print('A762_PREVIEW_DONE', mode, flush=True)
