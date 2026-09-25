"""Bounded refinement of the M4 grip against the accepted AKM profile, with the
receiver clearance measured in the same pass.

All measurements are world space: magazine and receiver BVHs come from the posed
meshes and the hand parts from the posed arm mesh, so a candidate correction is
exactly the world transform  D @ F @ C @ F^-1 @ D^-1  that the authoring pass
applies (F = shell frame in rest space, D = magazine carrier deform).

Objective: per-part median gap versus the accepted AKM wrap (frame 76) plus a
guard that keeps the hand off the receiver while the magazine is seated
(frames 76 / 88 / 95).  Values are millimetres; bounds are 10 mm / 12 deg.
"""
import bpy, json, math, random, sys
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
sys.path.insert(0, str(O))
import grip_lib as G

DIGITS = G.DIGITS
PARTS = ['hand_l'] + [f'{d}_{k}_l' for d in DIGITS for k in ('01', '02', '03')]


def open_blend(path):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    return bpy.data.objects['SK_M4_Infima']


def pose_dict(rig):
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


def eval_world(obj, dg):
    e = obj.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    verts = [M @ v.co for v in me.vertices]
    polys = [list(p.vertices) for p in me.polygons]
    e.to_mesh_clear()
    return verts, polys


def eval_parts(rig, arms, dg):
    e = arms.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    groups = [g.name for g in arms.vertex_groups]
    parts = {p: [] for p in PARTS}
    for v in me.vertices:
        best, w = None, 0.0
        for g in v.groups:
            if g.weight > w:
                best, w = groups[g.group], g.weight
        if best in parts:
            parts[best].append(M @ v.co)
    e.to_mesh_clear()
    return parts


def profile(parts, tree):
    out = {}
    for p, pts in parts.items():
        if not pts:
            continue
        d = []
        pen = 0.0
        for q in pts:
            loc, nor, _, dist = tree.find_nearest(q)
            if loc is None:
                continue
            inside = (q - loc).dot(nor) < 0
            d.append(-dist if inside else dist)
            # only trust the nearest-face inside test close to the surface
            if inside and dist < 0.025:
                pen = max(pen, min(30.0, dist * 1000))
        d.sort()
        out[p] = {'med': d[len(d) // 2] * 1000, 'p05': d[len(d) // 20] * 1000,
                  'min': d[0] * 1000, 'pen_mm': pen}
    return out


def make(p):
    t = Vector(p[:3]); rx, ry, rz = p[3:]
    return Matrix.Translation(t) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Rotation(ry, 4, 'Y') @ Matrix.Rotation(rx, 4, 'X')


# ------------------------------------------------------------- AKM target -----
rig = open_blend(S / 'AKMReloadPolish20260911/base/A_AKM_reload.blend')
bpy.context.scene.frame_set(148); bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
mv, mp = eval_world(bpy.data.objects['AKM_FactoryMagazine_Preview'], dg)
tree = BVHTree.FromPolygons(mv, mp, all_triangles=False)
TARGET = profile(eval_parts(rig, bpy.data.objects['SK_Manny_Arms_Export'], dg), tree)
print('AKM target  ' + json.dumps({k: round(v['med'], 2) for k, v in TARGET.items()}), flush=True)

# ----------------------------------------------------------- M4 current -------
rig = open_blend(S / 'ExtMagContact20260919/A_M4_ExtContact_reload.blend')
arms = bpy.data.objects['SK_Manny_Arms_Export']
mag = bpy.data.objects['M4_Magazine Light.003_Export']
body = bpy.data.objects['M4_M4 Body_Export']
restb = rig.data.bones['WPN_SOCKET_Magazine'].matrix_local
shell = None
FRAMES = [76, 88, 95]
samples = {}
bpy.context.scene.frame_set(FRAMES[0]); bpy.context.view_layer.update()
shell = G.Shell(G.shell_points(rig, mag),
                well_hint=rig.matrix_world @ rig.data.bones['WPN_SOCKET_Magazine'].head_local,
                palm_hint=rig.matrix_world @ rig.pose.bones['hand_l'].matrix.translation)
h = shell.height(G.knuckle_rest(rig, pose_dict(rig), G.deform(rig, pose_dict(rig))))
Frest = shell.frame_matrix(h)
for f in FRAMES:
    bpy.context.scene.frame_set(f); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    pose = pose_dict(rig)
    D = G.deform(rig, pose)
    mv, mp = eval_world(mag, dg)
    bv, bp = eval_world(body, dg)
    samples[f] = {
        'delta': D @ Frest,           # posed shell frame
        'mag': BVHTree.FromPolygons(mv, mp, all_triangles=False),
        'body': BVHTree.FromPolygons(bv, bp, all_triangles=False),
        'parts': eval_parts(rig, arms, dg),
    }
print('M4 f%d before ' % FRAMES[0] + json.dumps({k: round(v['med'], 2) for k, v in
      profile(samples[FRAMES[0]]['parts'], samples[FRAMES[0]]['mag']).items()}), flush=True)

KEYS = [p for p in TARGET if p in samples[FRAMES[0]]['parts'] and p != 'hand_l']


def cost(C, w_pen=0.05, w_body=0.12):
    c = 0.0; info = {}
    for i, f in enumerate(FRAMES):
        s = samples[f]
        base = s['delta']
        delta = base @ C @ base.inverted()
        parts = {k: [delta @ p for p in v] for k, v in s['parts'].items()}
        magp = profile(parts, s['mag'])
        info[f] = {'mag': {k: round(v['med'], 2) for k, v in magp.items()}}
        if i == 0:
            c += sum((magp[k]['med'] - TARGET[k]['med']) ** 2 for k in KEYS)
            for v in magp.values():
                c += w_pen * max(0.0, -v['p05'] - 1.0) ** 2
        bodyp = profile(parts, s['body'])
        pen = max(v['pen_mm'] for v in bodyp.values())
        info[f]['body_pen_mm'] = round(pen, 2)
        c += w_body * pen * pen
    return c, info


ident = Matrix.Identity(4)
best = (ident, cost(ident)[1], cost(ident)[0])
print('cost identity %.3f  body pen %s' % (best[2], json.dumps({k: v['body_pen_mm'] for k, v in best[1].items()})), flush=True)
random.seed(11)
lim = (0.010, 0.010, 0.010, math.radians(12), math.radians(12), math.radians(12))
grid = [Matrix.Identity(4)]
for _ in range(700):
    grid.append(make([random.uniform(-1, 1) * lim[i] for i in range(6)]))
for C in grid:
    c, info = cost(C)
    if c < best[2]:
        best = (C, info, c)
C0 = best[0]
for it in range(5):
    scale = 0.45 ** (it + 1)
    improved = True
    while improved:
        improved = False
        e = C0.to_euler()
        for i in range(6):
            for s in (-1, 1):
                p = list(C0.to_translation()) + [e[0], e[1], e[2]]
                p[i] += s * lim[i] * scale
                C = make(p)
                c, info = cost(C)
                if c < best[2]:
                    best = (C, info, c); C0 = C; improved = True
print('best cost %.3f' % best[2], flush=True)
print('best T %s  euler %s' % ([round(v * 1000, 3) for v in best[0].to_translation()],
                               [round(math.degrees(v), 3) for v in best[0].to_euler()]), flush=True)
for f in FRAMES:
    print('  f%-3d body_pen %.2f mm  mag %s' % (f, best[1][f]['body_pen_mm'], json.dumps(best[1][f]['mag'])), flush=True)
print('profile before ' + json.dumps({k: round(v['med'], 2) for k, v in
      profile(samples[FRAMES[0]]['parts'], samples[FRAMES[0]]['mag']).items()}), flush=True)
(O / 'refine.json').write_text(json.dumps({
    'akm_target_mm': {k: round(v['med'], 3) for k, v in TARGET.items()},
    'm4_before_mm': {k: round(v['med'], 3) for k, v in profile(samples[FRAMES[0]]['parts'], samples[FRAMES[0]]['mag']).items()},
    'm4_after_mm': best[1][FRAMES[0]]['mag'],
    'body_pen_before_mm': {str(f): round(max(v['pen_mm'] for v in profile(samples[f]['parts'], samples[f]['body']).values()), 2) for f in FRAMES},
    'body_pen_after_mm': {str(f): best[1][f]['body_pen_mm'] for f in FRAMES},
    'correction_translation_mm': [round(v * 1000, 4) for v in best[0].to_translation()],
    'correction_euler_deg': [round(math.degrees(v), 4) for v in best[0].to_euler()],
    'correction_matrix': [[round(v, 10) for v in row] for row in best[0]],
    'shell_height_mm': h * 1000, 'shell_length_mm': shell.length * 1000,
    'cost_before': round(cost(ident)[0], 4), 'cost_after': round(best[2], 4)}, indent=1))
print('REFINE_OK', flush=True)
