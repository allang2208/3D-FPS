"""Find real hollow openings on A762 PSO_ScopeBody / Mount / Lens.

Focus: boundary loops on the body that are NOT the intentional optical bore
or covered by overlapping shells. No gun-adapter measurements.
"""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
OUT.mkdir(exist_ok=True)
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z = 0.1024

bpy.ops.wm.open_mainfile(filepath=str(O / 'PSO1_A762_Editable.blend'))

def src(ob, co):
    return (ob.matrix_world @ co) - DELTA

def analyze(ob):
    me = ob.data
    slots = [m.name if m else '' for m in me.materials]
    counts = {}
    for p in me.polygons:
        name = slots[p.material_index] if p.material_index < len(slots) else '?'
        counts[name] = counts.get(name, 0) + 1
    bm = bmesh.new(); bm.from_mesh(me); bm.edges.ensure_lookup_table(); bm.verts.ensure_lookup_table()
    boundary = [e for e in bm.edges if e.is_boundary]
    # Walk boundary loops
    used = set()
    loops = []
    for e0 in boundary:
        if e0.index in used:
            continue
        loop = []
        e = e0
        v = e.verts[0]
        while e.index not in used:
            used.add(e.index)
            loop.append(e)
            v = e.other_vert(v)
            nxt = None
            for e2 in v.link_edges:
                if e2.is_boundary and e2.index not in used:
                    nxt = e2; break
            if nxt is None:
                break
            e = nxt
        # Center / radius of loop in source space
        pts = []
        for e in loop:
            for vv in e.verts:
                pts.append(src(ob, vv.co))
        if not pts:
            continue
        cx = sum(p.x for p in pts) / len(pts)
        cy = sum(p.y for p in pts) / len(pts)
        cz = sum(p.z for p in pts) / len(pts)
        rs = [math.hypot(p.x - cx, p.z - cz) for p in pts]
        loops.append({
            'edges': len(loop),
            'center': [round(cx, 4), round(cy, 4), round(cz, 4)],
            'r_mean': round(sum(rs)/len(rs), 4) if rs else 0,
            'r_max': round(max(rs), 4) if rs else 0,
            'y_span': [round(min(p.y for p in pts), 4), round(max(p.y for p in pts), 4)],
            'z_span': [round(min(p.z for p in pts), 4), round(max(p.z for p in pts), 4)],
            'x_span': [round(min(p.x for p in pts), 4), round(max(p.x for p in pts), 4)],
        })
    bm.free()
    return {
        'name': ob.name,
        'verts': len(me.vertices),
        'faces': len(me.polygons),
        'materials': counts,
        'boundary_edges': len(boundary),
        'boundary_loops': sorted(loops, key=lambda L: -L['edges'])[:30],
    }

# Only scope parts
keep = ('PSO_ScopeBody', 'PSO_ScopeMount', 'PSO_ScopeLens')
reports = []
for name in keep:
    ob = bpy.data.objects.get(name)
    if ob:
        reports.append(analyze(ob))

# Outside ray coverage: from tube axis, shoot outward through body collar region.
# If a ray escapes without hitting opaque body/mount, that is a see-through hollow.
body = bpy.data.objects['PSO_ScopeBody']
mount = bpy.data.objects['PSO_ScopeMount']
lens = bpy.data.objects['PSO_ScopeLens']

def build_tree(ob, opaque_only=False):
    mw = ob.matrix_world
    verts = [mw @ v.co for v in ob.data.vertices]
    faces = []
    for p in ob.data.polygons:
        if opaque_only:
            mat = ob.data.materials[p.material_index]
            if mat and ('Glass' in mat.name or 'Lens' in mat.name):
                continue
        faces.append(tuple(p.vertices))
    return BVHTree.FromPolygons(verts, faces)

body_tree = build_tree(body)
mount_tree = build_tree(mount)
lens_opaque = build_tree(lens, opaque_only=True)

misses = []
ys = [-0.16, -0.12, -0.08, -0.04, 0.0, 0.04, 0.08, 0.12]
angles = 32
for y in ys:
    for i in range(angles):
        ang = 2 * math.pi * i / angles
        # direction in world = source + DELTA; axis at (0,y,AXIS_Z)+DELTA
        origin_src = Vector((0.0, y, AXIS_Z))
        direction = Vector((math.cos(ang), 0.0, math.sin(ang)))
        origin = origin_src + DELTA
        # start slightly inside tube
        start = origin + direction * 0.005
        hits = []
        for tree, label in ((body_tree, 'body'), (mount_tree, 'mount'), (lens_opaque, 'lens_opaque')):
            hit = tree.ray_cast(start, direction, 0.08)
            if hit[0] is not None:
                hits.append((hit[3], label))
        if not hits:
            misses.append({'y': y, 'ang_deg': round(ang * 180 / math.pi, 1)})

# Also sample near the known collar y bands from earlier inspect
report = {
    'objects': reports,
    'radial_escape_rays': len(ys) * angles,
    'radial_misses': len(misses),
    'miss_sample': misses[:40],
}
(OUT / 'a762_body_openings.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('A762_BODY_OPENINGS', json.dumps({
    'boundary': {r['name']: (r['boundary_edges'], len(r['boundary_loops'])) for r in reports},
    'radial_misses': len(misses),
    'top_loops': {r['name']: r['boundary_loops'][:5] for r in reports},
}), flush=True)
