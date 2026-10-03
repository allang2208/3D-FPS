"""Locate the rectangular housing opening (not thin-tube) via under-cam miss rays + boundary loops."""
import bpy, bmesh, json, math
from pathlib import Path
from collections import defaultdict
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z = 0.1024

bpy.ops.wm.open_mainfile(filepath=str(OUT / 'PSO1_A762_Editable.before-tuck.blend'))
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world
verts = [(mw @ v.co) - DELTA for v in body.data.vertices]
faces = [tuple(p.vertices) for p in body.data.polygons]
tree = BVHTree.FromPolygons(verts, faces)

# Under camera same as silhouette
target = Vector((0.0, -0.04, 0.10))
cam_loc = target + Vector((0.12, -0.05, -0.22))
direction = (target - cam_loc).normalized()
z_axis = -direction
x_axis = z_axis.cross(Vector((0, 0, 1))); x_axis.normalize()
y_axis = z_axis.cross(x_axis).normalized()
half_w, half_h, steps = 0.22, 0.14, 80
misses = []
hits_near = []
for iy in range(steps):
    for ix in range(steps):
        u = (ix/(steps-1))*2-1; v = (iy/(steps-1))*2-1
        dir_w = (direction + x_axis*(u*half_w) + y_axis*(v*half_h)).normalized()
        # sample point along ray at expected body distance
        h = tree.ray_cast(cam_loc, dir_w, 0.8)
        # plane at mid depth for miss labeling
        # approximate intersection with plane through target perpendicular to direction
        denom = dir_w.dot(direction)
        if abs(denom) < 1e-8:
            continue
        t = (target - cam_loc).dot(direction) / denom
        plane_pt = cam_loc + dir_w * t
        if h[0] is None:
            # only keep misses near body ROI
            if -0.08 < plane_pt.x < 0.08 and -0.10 < plane_pt.y < 0.06 and 0.04 < plane_pt.z < 0.14:
                misses.append(plane_pt.copy())
        else:
            hp = h[0]
            if -0.08 < hp.x < 0.08 and -0.10 < hp.y < 0.06 and 0.04 < hp.z < 0.14:
                hits_near.append(hp.copy())

# bbox of miss cluster
def bbox(pts):
    return {
        'x': [round(min(p.x for p in pts),4), round(max(p.x for p in pts),4)],
        'y': [round(min(p.y for p in pts),4), round(max(p.y for p in pts),4)],
        'z': [round(min(p.z for p in pts),4), round(max(p.z for p in pts),4)],
        'n': len(pts),
    }

miss_bb = bbox(misses) if misses else None

# Boundary edges whose midpoint falls in expanded miss bbox
bm = bmesh.new(); bm.from_mesh(body.data)
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
for v in bm.verts:
    v.co = (mw @ v.co) - DELTA

if misses:
    xmin,xmax = miss_bb['x']; ymin,ymax = miss_bb['y']; zmin,zmax = miss_bb['z']
    pad = 0.008
    xmin-=pad; xmax+=pad; ymin-=pad; ymax+=pad; zmin-=pad; zmax+=pad
else:
    xmin,xmax,ymin,ymax,zmin,zmax = 0.0,0.06,-0.08,0.02,0.05,0.12

roi_edges = []
for e in bm.edges:
    if not e.is_boundary:
        continue
    mid = (e.verts[0].co + e.verts[1].co) * 0.5
    if xmin <= mid.x <= xmax and ymin <= mid.y <= ymax and zmin <= mid.z <= zmax:
        roi_edges.append(e)

# Walk closed loops among roi_edges (and allow stepping outside briefly via any boundary)
used = set(); loops = []
for e0 in roi_edges:
    if e0.index in used:
        continue
    # walk full boundary loop from e0
    loop = []; e = e0; v = e.verts[0]; guard = 0
    while e.index not in used and guard < 20000:
        used.add(e.index); loop.append(e); v = e.other_vert(v); guard += 1
        nxt = None
        for e2 in v.link_edges:
            if e2.is_boundary and e2.index not in used:
                nxt = e2; break
        if nxt is None:
            break
        e = nxt
    if len(loop) < 8:
        continue
    pts = [e.verts[0].co for e in loop] + [e.verts[1].co for e in loop]
    cx = sum(p.x for p in pts)/len(pts)
    cy = sum(p.y for p in pts)/len(pts)
    cz = sum(p.z for p in pts)/len(pts)
    rs = [math.hypot(p.x, p.z-AXIS_Z) for p in pts]
    # fraction of loop edges in ROI
    in_roi = sum(1 for e in loop if e in roi_edges)
    loops.append({
        'n': len(loop), 'in_roi': in_roi,
        'c': [round(cx,4), round(cy,4), round(cz,4)],
        'cr': round(math.hypot(cx, cz-AXIS_Z),4),
        'r': [round(min(rs),4), round(max(rs),4)],
        'x': [round(min(p.x for p in pts),4), round(max(p.x for p in pts),4)],
        'y': [round(min(p.y for p in pts),4), round(max(p.y for p in pts),4)],
        'z': [round(min(p.z for p in pts),4), round(max(p.z for p in pts),4)],
    })
loops.sort(key=lambda L: (-L['in_roi'], -L['n']))

# Also list faces whose center is near miss bbox (shell faces around hole)
face_roi = []
for f in bm.faces:
    c = f.calc_center_median()
    if xmin <= c.x <= xmax and ymin <= c.y <= ymax and zmin <= c.z <= zmax:
        face_roi.append({
            'i': f.index, 'n': len(f.verts),
            'c': [round(c.x,4), round(c.y,4), round(c.z,4)],
            'r': round(math.hypot(c.x, c.z-AXIS_Z),4),
            'area': round(f.calc_area(), 7),
        })
face_roi.sort(key=lambda d: d['r'])

report = {
    'miss_bbox': miss_bb,
    'roi_boundary_edges': len(roi_edges),
    'loops_top': loops[:12],
    'face_roi_count': len(face_roi),
    'face_roi_r_sample': face_roi[:15] + face_roi[-10:],
}
bm.free()
(OUT / 'a762_housing_hole.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('HOUSING_HOLE', json.dumps({
    'miss_bbox': miss_bb,
    'roi_edges': len(roi_edges),
    'loops': loops[:6],
}), flush=True)
