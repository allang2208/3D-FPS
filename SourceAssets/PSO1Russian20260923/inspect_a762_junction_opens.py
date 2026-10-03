"""Measure Body-Mount junction slits and mark exposed body openings for viz."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z = 0.1024

bpy.ops.wm.open_mainfile(filepath=str(O / 'PSO1_A762_Editable.blend'))
body = bpy.data.objects['PSO_ScopeBody']
mount = bpy.data.objects['PSO_ScopeMount']
scene = bpy.context.scene

# Bright mark material for exposed non-bore body edges (temporary viz object)
red = bpy.data.materials.new('MARK_OPEN')
red.use_nodes = True
red.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (1, 0.05, 0.05, 1)
red.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (1, 0.1, 0.05, 1)
red.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 5

mw = body.matrix_world
mm = mount.matrix_world
mv = [mm @ v.co for v in mount.data.vertices]
mf = [tuple(p.vertices) for p in mount.data.polygons]
mount_t = BVHTree.FromPolygons(mv, mf)

bm = bmesh.new(); bm.from_mesh(body.data); bm.edges.ensure_lookup_table()
# Build opaque without body (mount+lens collars) for coverage from others
lens = bpy.data.objects['PSO_ScopeLens']
lv = [lens.matrix_world @ v.co for v in lens.data.vertices]
lf = []
for p in lens.data.polygons:
    mat = lens.data.materials[p.material_index]
    if mat and 'OpticalGlass' in mat.name:
        continue
    lf.append(tuple(p.vertices))
cover = BVHTree.FromPolygons(mv + lv, mf + [tuple(len(mv)+i for i in f) for f in lf])

# Also body self-cover: use body tree for overlapping shell
bv = [mw @ v.co for v in body.data.vertices]
bf = [tuple(p.vertices) for p in body.data.polygons]
body_t = BVHTree.FromPolygons(bv, bf)

markers = []
junction = []
for e in bm.edges:
    if not e.is_boundary:
        continue
    mid_w = mw @ ((e.verts[0].co + e.verts[1].co) * 0.5)
    f = e.link_faces[0]
    n = (mw.to_3x3() @ f.normal).normalized()
    p = mid_w - DELTA
    r = math.hypot(p.x, p.z - AXIS_Z)
    if r < 0.023:
        continue
    covered = False
    for tree in (cover, body_t):
        h = tree.ray_cast(mid_w + n * 0.0005, n, 0.004)
        if h[0] is not None and h[3] > 0.0002:
            covered = True; break
    if covered:
        continue
    markers.append(mid_w)
    # Distance to mount
    loc, normal, index, dist = mount_t.find_nearest(mid_w)
    junction.append({
        'x': round(p.x, 4), 'y': round(p.y, 4), 'z': round(p.z, 4),
        'r': round(r, 4),
        'mount_mm': None if loc is None else round(dist * 1000, 2),
        'nx': round(n.x, 3), 'ny': round(n.y, 3), 'nz': round(n.z, 3),
    })
bm.free()

# Create marker mesh of small spheres / verts as a polyline cloud
me = bpy.data.meshes.new('OPEN_MARKERS')
me.from_pydata([tuple(p) for p in markers], [], [])
me.update()
ob = bpy.data.objects.new('OPEN_MARKERS', me)
scene.collection.objects.link(ob)
ob.data.materials.append(red)

# Hide adapters and receiver
for o in scene.objects:
    if o.type != 'MESH':
        continue
    keep = o.name in ('PSO_ScopeBody', 'PSO_ScopeMount', 'PSO_ScopeLens', 'OPEN_MARKERS')
    o.hide_render = not keep
    o.hide_set(not keep)

# Tint body vs mount for clarity
for o, col in ((body, (0.55, 0.55, 0.58, 1)), (mount, (0.75, 0.7, 0.45, 1))):
    m = bpy.data.materials.new('VIZ_'+o.name)
    m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = col
    o.data.materials.clear(); o.data.materials.append(m)

scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
sh = scene.display.shading
sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'
sh.show_backface_culling = True
sh.show_cavity = True; sh.cavity_type = 'BOTH'
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
scene.collection.objects.link(cam); scene.camera = cam; cam.data.lens = 70
target = DELTA + Vector((0.01, -0.05, 0.08))
for name, off in {
    'open_side': Vector((0.28, 0.0, 0.04)),
    'open_tq': Vector((0.22, -0.22, 0.12)),
    'open_mountside': Vector((0.30, -0.05, 0.02)),
    'open_leftside': Vector((-0.28, -0.05, 0.05)),
}.items():
    cam.location = target + off
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / ('A762_%s.png' % name))
    bpy.ops.render.render(write_still=True)

junction.sort(key=lambda d: (d['mount_mm'] is None, -(d['mount_mm'] or 0)))
clusters = {}
for j in junction:
    key = (round(j['x']*25)/25, round(j['y']*25)/25, round(j['z']*25)/25)
    c = clusters.setdefault(key, {'n': 0, 'mount_mm_min': 999, 'mount_mm_max': 0})
    c['n'] += 1
    if j['mount_mm'] is not None:
        c['mount_mm_min'] = min(c['mount_mm_min'], j['mount_mm'])
        c['mount_mm_max'] = max(c['mount_mm_max'], j['mount_mm'])
top = sorted(({'xyz': list(k), **v} for k, v in clusters.items()), key=lambda d: -d['n'])
result = {'exposed_body_edges': len(junction), 'clusters': top[:20], 'sample': junction[:30]}
(OUT / 'a762_junction_opens.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('A762_JUNCTION_OPENS', json.dumps(result), flush=True)
