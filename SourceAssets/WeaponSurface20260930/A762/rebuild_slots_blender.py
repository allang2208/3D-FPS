"""Blender (background): items 4-6 replacement geometry for A762. Writes Bake/rebuild_parts.bin.

blender -b --factory-startup -P rebuild_slots_blender.py

4. Magazine shell (Magazine_Rebuilt, MagazineEdge_Rebuilt): one Catmull-Clark level with
   every edge sharper than CREASE_MAG creased, linear UVs, so the curved body stops reading as
   facets while ribs, lips and beads stay crisp.
5. Rebuilt hard-surface slots: edges sharper than BEVEL_ANGLE get a 2-segment round bevel of
   BEVEL_WIDTH (real machined edges are 0.3-0.5 mm; the rebuild used 0.14 mm).
6. AK rivets and pin heads on the receiver sheet, both sides (FrontAssembly_Rebuilt slot,
   WPN_root), placed by ray cast on the seated receiver and sunk slightly into it.
Corner normals: area-weighted within CREASE_NORMAL of each face, so bevels shade round and
flat faces stay flat. Every replaced slot is bound to one bone, so bind space is used.
Blender works in a Y-mirrored copy of UE space (the dump winding then faces outward).
"""
import json
import math
import sys
from pathlib import Path
import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import seated  # noqa: E402

KEY = 'A762_AfterRepair'
MAGAZINE = ('M_A762_Magazine_Rebuilt', 'M_A762_MagazineEdge_Rebuilt')
BEVELLED = ('M_A762_UpperReceiver03', 'M_A762_FrontAssembly_Rebuilt', 'M_A762_Flash_Hider', 'M_A762_Rail',
            'M_A762_RearSight03', 'M_A762_FrontSight_Rebuilt', 'M_A762_FactoryStock_Socket03',
            'M_A762_FactoryStock_Metal04', 'M_A762_FactoryStock_Rubber04', 'M_A762_FactoryStock_Seam04',
            'M_A762_Handguard03')
CREASE_MAG, BEVEL_ANGLE, BEVEL_WIDTH, CREASE_NORMAL = 35.0, 40.0, 0.035, 45.0
FLIP = np.array([1.0, -1.0, 1.0])
# (y, z, radius, height) in UE cm; both sides. Front trunnion triangle behind the
# receiver/front-block seam, centre support pair above the magazine catch, rear trunnion
# pair. The trigger group already has its own pin/lever detail, so no pins there.
RIVETS = [(-31.7, -4.1, 0.24, 0.07), (-30.3, -4.1, 0.24, 0.07), (-31.0, -5.55, 0.24, 0.07),
          (-19.6, -5.9, 0.22, 0.065), (-18.3, -5.9, 0.22, 0.065),
          (-5.4, -4.0, 0.24, 0.07), (-5.4, -5.4, 0.24, 0.07)]

h, pos, st, tri, mat, bone, gun = seated.load(KEY)
_, _, _, _, uv0, _ = seated.read_geometry(seated.GEOMETRY / (KEY + '.bin'))
report = {'key': KEY, 'parts': {}}


def build_bmesh(slot):
    sel = np.nonzero(mat == h['slots'].index(slot))[0]
    verts = np.unique(tri[sel])
    remap = -np.ones(len(pos), np.int64)
    remap[verts] = np.arange(len(verts))
    bm = bmesh.new()
    bv = [bm.verts.new(tuple(p)) for p in pos[verts].astype(np.float64) * FLIP]
    bm.verts.ensure_lookup_table()
    uvl = bm.loops.layers.uv.new('UV0')
    skipped = 0
    for t in sel:
        try:
            f = bm.faces.new([bv[remap[i]] for i in tri[t]])
        except ValueError:  # exact duplicate face
            skipped += 1
            continue
        for loop, uv in zip(f.loops, uv0[t]):
            loop[uvl].uv = (float(uv[0]), float(uv[1]))
    bm.normal_update()
    return bm, len(sel), skipped


def sharp_edges(bm, angle):
    c = math.cos(math.radians(angle))
    return [e for e in bm.edges if len(e.link_faces) == 2 and e.link_faces[0].normal.dot(e.link_faces[1].normal) < c]


def to_arrays(bm, smooth_angle):
    """Triangulates and returns UE-space arrays; corner normals come from Blender's
    smooth-by-angle plus a face-area Weighted Normal pass, so smooth regions share one
    normal per vertex, bevels shade round and large flat faces stay flat."""
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.verts.index_update()
    bm.normal_update()
    uvl = bm.loops.layers.uv['UV0']
    P = np.array([v.co[:] for v in bm.verts])
    T = np.array([[l.vert.index for l in f.loops] for f in bm.faces], np.int64)
    UV = np.array([[l[uvl].uv[:] for l in f.loops] for f in bm.faces])
    me = bpy.data.meshes.new('normals')
    bm.to_mesh(me)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    ob = bpy.data.objects.new('normals', me)
    bpy.context.scene.collection.objects.link(ob)
    wn = ob.modifiers.new('wn', 'WEIGHTED_NORMAL')
    wn.mode = 'FACE_AREA'
    wn.keep_sharp = True
    wn.weight = 50
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    cn = np.empty(len(ev.loops) * 3, np.float32)
    ev.corner_normals.foreach_get('vector', cn)
    N = cn.reshape(len(T), 3, 3).astype(np.float64)
    ob.to_mesh_clear()
    bpy.data.objects.remove(ob)
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    keep = area > 1e-10
    return P * FLIP, T[keep], N[keep] * FLIP, UV[keep]


def subdivide_magazine(bm):
    crease = bm.edges.layers.float.get('crease_edge') or bm.edges.layers.float.new('crease_edge')
    creased = sharp_edges(bm, CREASE_MAG)
    for e in creased:
        e[crease] = 1.0
    me = bpy.data.meshes.new('mag')
    bm.to_mesh(me)
    ob = bpy.data.objects.new('mag', me)
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new('sub', 'SUBSURF')
    mod.levels = mod.render_levels = 1
    mod.uv_smooth = 'NONE'
    mod.boundary_smooth = 'PRESERVE_CORNERS'
    mod.use_creases = True
    dg = bpy.context.evaluated_depsgraph_get()
    out = bmesh.new()
    out.from_mesh(ob.evaluated_get(dg).to_mesh())
    return out, len(creased)


def bevel(bm):
    edges = sharp_edges(bm, BEVEL_ANGLE)
    if edges:
        bmesh.ops.bevel(bm, geom=edges, offset=BEVEL_WIDTH, offset_type='OFFSET', segments=2, profile=0.5,
                        affect='EDGES', clamp_overlap=True, loop_slide=True)
    return len(edges)


parts = []
for slot in MAGAZINE + BEVELLED:
    bm, n_in, skipped = build_bmesh(slot)
    if slot in MAGAZINE:
        bm2, n_edges = subdivide_magazine(bm)
        bm.free()
        bm = bm2
        op, smooth = 'subdivide', CREASE_MAG
    else:
        n_edges = bevel(bm)
        op, smooth = 'bevel', CREASE_NORMAL
    P, T, N, UV = to_arrays(bm, smooth)
    bm.free()
    parts.append({'slot': slot, 'mode': 'replace', 'P': P, 'T': T, 'N': N, 'UV': UV})
    report['parts'][slot] = {'op': op, 'triangles_in': int(n_in), 'duplicate_faces_skipped': int(skipped),
                             'edges': int(n_edges), 'triangles_out': int(len(T)), 'vertices_out': int(len(P))}
    print('A762_REBUILD', slot, json.dumps(report['parts'][slot]), flush=True)

# 6. Rivets on the seated receiver (WPN_root parts: seated == bind).
tree = BVHTree.FromPolygons([tuple(p) for p in st], tri[gun].tolist(), all_triangles=True)
gun_mats = mat[gun]


def dome(center, axis, radius, height, seg=16, rings=4):
    """Spherical cap on `axis` plus a short skirt below the base; smooth normals."""
    axis = axis / np.linalg.norm(axis)
    t = np.cross(axis, [0.0, 0.0, 1.0] if abs(axis[2]) < 0.9 else [1.0, 0.0, 0.0])
    t /= np.linalg.norm(t)
    b = np.cross(axis, t)
    R = (radius ** 2 + height ** 2) / (2 * height)
    sc = center - axis * (R - height)  # sphere centre
    theta_max = math.asin(min(1.0, radius / R))
    verts, norms = [], []
    top = sc + axis * R
    verts.append(top)
    norms.append(axis)
    for r in range(1, rings + 1):
        th = theta_max * r / rings
        for s in range(seg):
            ph = 2 * math.pi * s / seg
            d = axis * math.cos(th) + (t * math.cos(ph) + b * math.sin(ph)) * math.sin(th)
            verts.append(sc + d * R)
            norms.append(d)
    base = len(verts)
    for s in range(seg):  # skirt 0.05 cm into the sheet
        ph = 2 * math.pi * s / seg
        rad = t * math.cos(ph) + b * math.sin(ph)
        verts.append(center + rad * radius - axis * 0.05)
        norms.append(rad)
    tris = []
    for s in range(seg):
        tris.append([0, 1 + s, 1 + (s + 1) % seg])
    for r in range(1, rings):
        o0, o1 = 1 + (r - 1) * seg, 1 + r * seg
        for s in range(seg):
            a, b2, c, d2 = o0 + s, o0 + (s + 1) % seg, o1 + (s + 1) % seg, o1 + s
            tris += [[a, d2, c], [a, c, b2]]
    o = 1 + (rings - 1) * seg
    for s in range(seg):
        a, b2 = o + s, o + (s + 1) % seg
        c, d2 = base + (s + 1) % seg, base + s
        tris += [[a, d2, c], [a, c, b2]]
    V = np.array(verts)
    T = np.array(tris)
    Nn = np.array(norms)
    # Rivets are built in UE space, where the dump winding has the right-handed cross product
    # pointing against the outward normal.
    a, b3, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    if np.einsum('ij,ij->i', np.cross(b3 - a, c - a), Nn[T].mean(1)).mean() > 0:
        T = T[:, ::-1]
    return V, T, Nn


rv, rt, rn = [], [], []
placed = []
for side, x0, d in (('left', -20.0, 1.0), ('right', 30.0, -1.0)):
    for y, z, radius, height in RIVETS:
        o = Vector((x0, y, z))  # UE space (the tree is built on the seated UE positions)
        hit, nrm, idx, _ = tree.ray_cast(o, Vector((d, 0, 0)), 60.0)
        if hit is None or h['slots'][gun_mats[idx]] not in ('M_A762_Receiver', 'M_A762_UpperReceiver03'):
            placed.append({'side': side, 'y': y, 'z': z, 'placed': False,
                           'hit': None if hit is None else h['slots'][gun_mats[idx]]})
            continue
        n = np.array(nrm[:])
        if n[0] * d > 0:
            n = -n
        V, T, Nn = dome(np.array(hit[:]) - n * 0.012, n, radius, height)
        rt.append(T + sum(len(x) for x in rv))
        rv.append(V)
        rn.append(Nn)
        placed.append({'side': side, 'y': y, 'z': z, 'placed': True, 'surface': h['slots'][gun_mats[idx]],
                       'normal_x': round(float(n[0]), 3)})
if rv:
    V = np.concatenate(rv)
    T = np.concatenate(rt)
    Nn = np.concatenate(rn)
    parts.append({'slot': 'M_A762_FrontAssembly_Rebuilt', 'mode': 'add', 'P': V, 'T': T,
                  'N': Nn[T], 'UV': np.zeros((len(T), 3, 2))})
report['rivets'] = placed
print('A762_RIVETS', json.dumps(placed), flush=True)

with open(HERE / 'Bake' / 'rebuild_parts.bin', 'wb') as f:
    head = {'key': KEY, 'triangle_count': int(len(tri)), 'vertex_count': int(len(pos)),
            'position_checksum': float(np.abs(pos.astype(np.float64)).sum()),
            'parts': [{'slot': p['slot'], 'mode': p['mode'], 'vertices': int(len(p['P'])), 'triangles': int(len(p['T']))}
                      for p in parts]}
    f.write((json.dumps(head) + '\n').encode('utf-8'))
    for p in parts:
        f.write(p['P'].astype(np.float32).tobytes())
        f.write(p['T'].astype(np.int32).tobytes())
        f.write(p['N'].astype(np.float32).tobytes())
        f.write(p['UV'].astype(np.float32).tobytes())
(HERE / 'Bake' / 'rebuild_report.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
print('A762_REBUILD_DONE', sum(p['triangles'] for p in head['parts']), flush=True)
