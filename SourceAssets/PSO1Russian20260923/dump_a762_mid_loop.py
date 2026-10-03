"""Dump the mid-tube 56-edge body boundary loop in source coordinates."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z = 0.1024

bpy.ops.wm.open_mainfile(filepath=str(O / 'PSO1_A762_Editable.blend'))
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world
bm = bmesh.new(); bm.from_mesh(body.data); bm.edges.ensure_lookup_table()

def src(co):
    return (mw @ co) - DELTA

# Find the loop whose center is near (0, -0.052, 0.094)
boundary = [e for e in bm.edges if e.is_boundary]
used = set(); target = None
for e0 in boundary:
    if e0.index in used:
        continue
    loop = []; e = e0; v = e.verts[0]; guard = 0
    while e.index not in used and guard < 10000:
        used.add(e.index); loop.append(e); v = e.other_vert(v)
        nxt = None
        for e2 in v.link_edges:
            if e2.is_boundary and e2.index not in used:
                nxt = e2; break
        if nxt is None:
            break
        e = nxt; guard += 1
    pts = [src(vv.co) for ed in loop for vv in ed.verts]
    if not pts:
        continue
    cx = sum(p.x for p in pts)/len(pts); cy = sum(p.y for p in pts)/len(pts); cz = sum(p.z for p in pts)/len(pts)
    if abs(cy + 0.0517) < 0.01 and abs(cz - 0.094) < 0.015 and len(loop) > 40:
        # unique verts ordered
        rem = set(loop); e = loop[0]; ordered = [e.verts[0], e.verts[1]]; rem.remove(e)
        while rem:
            end = ordered[-1]; found = None
            for e2 in list(rem):
                if end in e2.verts:
                    found = e2; break
            if not found:
                break
            rem.remove(found); ordered.append(found.other_vert(end))
        if ordered[0] == ordered[-1]:
            ordered = ordered[:-1]
        coords = []
        for vv in ordered:
            p = src(vv.co)
            ang = math.atan2(p.z - AXIS_Z, p.x)
            coords.append({'x': round(p.x,5), 'y': round(p.y,5), 'z': round(p.z,5),
                           'r': round(math.hypot(p.x, p.z-AXIS_Z),5), 'ang_deg': round(math.degrees(ang),1),
                           'vi': vv.index})
        target = {'edges': len(loop), 'verts': len(ordered), 'coords': coords}
        break

(OUT / 'a762_mid_loop.json').write_text(json.dumps(target, indent=2), encoding='utf-8')
print('A762_MID_LOOP', json.dumps({k: target[k] for k in ('edges','verts')} | {'first10': target['coords'][:10], 'ang_range': [min(c['ang_deg'] for c in target['coords']), max(c['ang_deg'] for c in target['coords'])], 'y_range': [min(c['y'] for c in target['coords']), max(c['y'] for c in target['coords'])], 'r_range': [min(c['r'] for c in target['coords']), max(c['r'] for c in target['coords'])]}), flush=True)
bm.free()
