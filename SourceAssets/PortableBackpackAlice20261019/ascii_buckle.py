import bpy
import bmesh
import os

ROOT = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "AliceBackpack_uv_bevel.blend"))
obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
bm = bmesh.new(); bm.from_mesh(obj.data)
bm.faces.ensure_lookup_table()
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
# left side main + small = components with center x near -0.236
sel = []
for comp in comps:
    vs = {v for f in comp for v in f.verts}
    cx = sum(v.co.x for v in vs) / len(vs)
    if -0.245 < cx < -0.225:
        sel.append(comp)
faces = [f for comp in sel for f in comp]
print("SIDE_FACES", len(faces), "comps", [len(c) for c in sel])

def project(axis_a, axis_b, cols=52, rows=42):
    vals = [v for f in faces for v in f.verts]
    loa = min(v.co[axis_a] for v in vals); hia = max(v.co[axis_a] for v in vals)
    lob = min(v.co[axis_b] for v in vals); hib = max(v.co[axis_b] for v in vals)
    grid = [[" " for _ in range(cols)] for _ in range(rows)]
    def cell(a, b):
        ca = int((a - loa) / (hia - loa + 1e-12) * (cols - 1))
        rb = int((b - lob) / (hib - lob + 1e-12) * (rows - 1))
        return ca, rows - 1 - rb
    for f in faces:
        vs = list(f.verts)
        # fan triangles
        for i in range(1, len(vs) - 1):
            tri = [vs[0], vs[i], vs[i + 1]]
            pts = [cell(v.co[axis_a], v.co[axis_b]) for v in tri]
            minx = max(0, min(p[0] for p in pts)); maxx = min(cols - 1, max(p[0] for p in pts))
            miny = max(0, min(p[1] for p in pts)); maxy = min(rows - 1, max(p[1] for p in pts))
            # mark all cells in triangle bbox (silhouette overfill acceptable)
            for x in range(minx, maxx + 1):
                for y in range(miny, maxy + 1):
                    grid[y][x] = "#"
    print("PROJ a%d b%d range %.4f..%.4f %.4f..%.4f" % (axis_a, axis_b, loa, hia, lob, hib))
    for row in grid:
        print("|" + "".join(row) + "|")

print("=== SIDE (Y horizontal, Z vertical) ===")
project(1, 2)
print("=== FRONT (X horizontal, Z vertical) ===")
project(0, 2)
bm.free()