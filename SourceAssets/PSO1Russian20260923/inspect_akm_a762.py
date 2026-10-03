"""Read-only geometry check of AKM/A762 PSO against the PKM seam and burr lessons.

Hollows: lens object still carrying the 340 collar triangles as glass, or real
boundary edges on the shell. Burrs: body vertices outside the tube cylinder that
are not the kept side clamp (the PKM leftover feet and left jaw plates).
"""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
OUT.mkdir(exist_ok=True)
# Placements baked into the side-mount editable blends (author.py).
DELTAS = {'AKM': Vector((0.010, -0.035, 0.035)), 'A762': Vector((0.010, -0.015, 0.035))}
AXIS_Z, TUBE_R = 0.1024, 0.0203


def source_co(host, ob, co):
    return (ob.matrix_world @ co) - DELTAS[host]


def analyze(host):
    path = O / ('PSO1_%s_Editable.blend' % host)
    bpy.ops.wm.open_mainfile(filepath=str(path))
    report = {'host': host, 'blend': str(path), 'objects': []}
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH' or ob.hide_render:
            continue
        me = ob.data
        slots = [m.name if m else '' for m in me.materials]
        counts = {}
        for p in me.polygons:
            name = slots[p.material_index] if p.material_index < len(slots) else '?'
            counts[name] = counts.get(name, 0) + 1
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        boundary = [e for e in bm.edges if e.is_boundary]
        nonmanifold = [e for e in bm.edges if not e.is_manifold]
        # Group boundary edges by 2 cm bins in source space so a hole has a place.
        bins = {}
        for e in boundary:
            c = source_co(host, ob, (e.verts[0].co + e.verts[1].co) / 2)
            key = (round(c.x * 50) / 50, round(c.y * 50) / 50, round(c.z * 50) / 50)
            bins[key] = bins.get(key, 0) + 1
        outside = []
        for v in me.vertices:
            p = source_co(host, ob, v.co)
            r = math.hypot(p.x, p.z - AXIS_Z)
            if r > TUBE_R + 0.0015:
                outside.append((round(p.x, 4), round(p.y, 4), round(p.z, 4), round(r, 4)))
        # Same windows the PKM tuck used, in source coordinates.
        foot = jaw = 0
        jaw_max_r = 0.0
        foot_min_z = 9.0
        for v in me.vertices:
            p = source_co(host, ob, v.co)
            if p.z < 0.072 and -0.095 < p.y < 0.05:
                foot += 1
                foot_min_z = min(foot_min_z, p.z)
            if p.x > 0.0195 and -0.16 < p.y < 0.06 and p.z < 0.135:
                jaw += 1
                jaw_max_r = max(jaw_max_r, math.hypot(p.x, p.z - AXIS_Z))
        # Glass faces that do not cover the optical axis are the see-through collar.
        glass_faces = []
        for p in me.polygons:
            name = slots[p.material_index] if p.material_index < len(slots) else ''
            if 'Glass' in name or 'Lens' in name:
                glass_faces.append(p)
        covers = offaxis = 0
        for p in glass_faces:
            pts = [source_co(host, ob, me.vertices[i].co) for i in p.vertices]
            # Project onto the XZ plane around the tube axis and test winding cover of (0, AXIS_Z).
            axis = Vector((0, AXIS_Z))
            signs = []
            for a, b in zip(pts, pts[1:] + pts[:1]):
                signs.append((b.x - a.x) * (AXIS_Z - a.z) - (b.z - a.z) * (0 - a.x))
            if signs and (min(signs) >= -1e-9 or max(signs) <= 1e-9):
                covers += 1
            else:
                offaxis += 1
        top_bins = sorted(bins.items(), key=lambda kv: -kv[1])[:12]
        report['objects'].append({
            'name': ob.name,
            'verts': len(me.vertices),
            'faces': len(me.polygons),
            'materials': counts,
            'boundary_edges': len(boundary),
            'nonmanifold_edges': len(nonmanifold),
            'boundary_bins': [{'xyz': list(k), 'n': n} for k, n in top_bins],
            'outside_tube_verts': len(outside),
            'outside_sample': outside[:8],
            'pkm_foot_window_verts': foot,
            'foot_min_z': None if foot == 0 else round(foot_min_z, 4),
            'pkm_left_jaw_window_verts': jaw,
            'jaw_max_radius': round(jaw_max_r, 4),
            'glass_faces': len(glass_faces),
            'glass_covering_axis': covers,
            'glass_off_axis': offaxis,
        })
        bm.free()
    return report


reports = [analyze(h) for h in ('AKM', 'A762')]
(OUT / 'report.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')
print('PSO_INSPECT_DONE', flush=True)
