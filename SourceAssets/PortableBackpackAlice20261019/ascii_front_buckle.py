import bpy
import bmesh
import os

ROOT = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "AliceBackpack_uv_bevel.blend"))
obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
bm = bmesh.new(); bm.from_mesh(obj.data); bm.faces.ensure_lookup_table()
metal = [f for f in bm.faces if f.material_index == 3]
remaining = set(metal); comps = []
while remaining:
    seed = remaining.pop(); stack = [seed]; comp = [seed]
    while stack:
        f = stack.pop()
        for e in f.edges:
            for nf in e.link_faces:
                if nf in remaining and nf.material_index == 3:
                    remaining.remove(nf); stack.append(nf); comp.append(nf)
    comps.append(comp)
comps.sort(key=lambda c: -len(c))

def bbox(comp):
    vs = {v for f in comp for v in f.verts}
    return [min(v.co[i] for v in vs) for i in range(3)], [max(v.co[i] for v in vs) for i in range(3)]

def project(comp, axis_a, axis_b, cols=60, rows=48):
    vals = [v for f in comp for v in f.verts]
    loa = min(v.co[axis_a] for v in vals); hia = max(v.co[axis_a] for v in vals)
    lob = min(v.co[axis_b] for v in vals); hib = max(v.co[axis_b] for v in vals)
    grid = [[" " for _ in range(cols)] for _ in range(rows)]
    def cell(a, b):
        ca = int((a - loa) / (hia - loa + 1e-12) * (cols - 1))
        rb = int((b - lob) / (hib - lob + 1e-12) * (rows - 1))
        return ca, rows - 1 - rb
    for f in comp:
        vs = list(f.verts)
        for i in range(1, len(vs) - 1):
            tri = [vs[0], vs[i], vs[i + 1]]
            pts = [cell(v.co[axis_a], v.co[axis_b]) for v in tri]
            minx = max(0, min(p[0] for p in pts)); maxx = min(cols - 1, max(p[0] for p in pts))
            miny = max(0, min(p[1] for p in pts)); maxy = min(rows - 1, max(p[1] for p in pts))
            for x in range(minx, maxx + 1):
                for y in range(miny, maxy + 1):
                    grid[y][x] = "#"
    print("PROJ range %.4f..%.4f %.4f..%.4f" % (loa, hia, lob, hib))
    for row in grid: print("|" + "".join(row) + "|")

for idx, comp in enumerate(comps):
    lo, hi = bbox(comp)
    c = [(lo[i] + hi[i]) / 2 for i in range(3)]
    d = [hi[i] - lo[i] for i in range(3)]
    if abs(c[0] + 0.0617) < 0.005:
        print("=== FRONT_LEFT comp", idx, "faces", len(comp), "c", [round(x, 4) for x in c], "d", [round(x, 4) for x in d])
        print("--- XZ front ---"); project(comp, 0, 2)
        print("--- YZ side ---"); project(comp, 1, 2)
bm.free()