"""Author the standalone buildable workbench from the dungeon WorkbenchKit.

Pipeline (headless Blender):
  1. open the authored kit blend, keep the table/lamp/bench-props subset (no wall parts,
     no coplanar BenchWear decal, no wall-socket power lead);
  2. decimate the heavy hero meshes to a buildable budget;
  3. relocate three wall tools (hammer, hand saw, adjustable wrench) onto the tabletop;
  4. author new desk clutter: two unrolled blueprints, two rolled scrolls, a stack of
     three books, an open book, a pencil, a brass fastener tray with nails;
  5. re-centre the assembly on its footprint, join to one mesh, triangulate, export FBX
     + manifest for the UE commandlet importer.

All geometry lives in the kit's local frame (metres): the bench occupies
x in [-2.59,-0.17] (back edge at x=-0.17 toward the old wall), y in [-2.59,0],
tabletop at z=0.939. Config anchors (cm) map to blend as (x, y) -> (-x/100, -y/100).

Run:
  "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --python-exit-code 1 \
      --python SourceAssets/WorkbenchBuildable20260924/Scripts/author_standalone.py
"""
from pathlib import Path
import bpy, json, math, re, random
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
KIT_ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkbenchKit20260921')
KIT_BLEND = str(KIT_ROOT / 'Authored/DungeonWorkbenchKit.blend')
KIT_MANIFEST = json.loads((KIT_ROOT / 'Authored/manifest.json').read_text(encoding='utf-8'))
OUT = ROOT / 'Authored'
OUT.mkdir(exist_ok=True)
TEX = OUT / 'Textures'
rng = random.Random(21921)
TABLE_Z = 0.939

KIT_MAT = {}
for comp in KIT_MANIFEST['components']:
    for slot, src in comp['material_paths'].items():
        if src:
            KIT_MAT[re.sub(r'\.\d{3}$', '', slot)] = src

KEEP = ['Bench_BenchTop', 'Sculpt_BenchFrame', 'Fab_BenchRetained', 'Bench_TaskLamp',
        'LampFlex', 'Sculpt_Rag', 'Fab_Bench_Wrench', 'Fab_Bench_Screwdriver',
        'Fab_Bench_Pliers', 'Fab_Bench_Chisel', 'Bottle_OilCan', 'Bottle_Degreaser']
DECIMATE = {'Fab_BenchRetained': 0.18, 'Bench_TaskLamp': 0.20, 'Sculpt_BenchFrame': 0.40,
            'Bench_BenchTop': 0.28, 'Sculpt_Rag': 0.25, 'Bottle_OilCan': 0.35,
            'Bottle_Degreaser': 0.45, 'LampFlex': 0.35, 'Fab_Wall_Hand_Saw': 0.40}
# wall tools re-used as tabletop items: (pre-rot euler deg, config xy cm, yaw deg)
RELOCATE = {
    'Fab_Wall_Hammer': ((90, 0, 0), (48, 200), 15),
    'Fab_Wall_Adjustable_Wrench': ((90, 0, 0), (42, 232), -32),
    'Fab_Wall_Hand_Saw': ((0, 90, 0), (200, 199), 88),
}

bpy.ops.wm.open_mainfile(filepath=KIT_BLEND)
for ob in bpy.data.objects:
    if ob.type == 'MESH':
        ob.hide_set(False)

def obj_for(cid):
    return bpy.data.objects.get('SM_WBK_' + cid)

def active(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob

def bake(ob):
    active(ob)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

def data_bbox(me):
    mn = [min(v.co[i] for v in me.vertices) for i in range(3)]
    mx = [max(v.co[i] for v in me.vertices) for i in range(3)]
    return mn, mx

def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)

def place(me, x_cm, y_cm, yaw=0.0, z_base=None, eps=0.001):
    """Rotate about own centre then drop so the bbox bottom sits at z_base (default tabletop)."""
    me.transform(Matrix.Rotation(math.radians(yaw), 4, 'Z'))
    mn, mx = data_bbox(me)
    tz = TABLE_Z if z_base is None else z_base
    me.transform(Matrix.Translation(Vector((-x_cm / 100.0 - (mn[0] + mx[0]) / 2,
                                           -y_cm / 100.0 - (mn[1] + mx[1]) / 2,
                                           tz + eps - mn[2]))))
    me.update()

# ---------------------------------------------------------------- keep + decimate
parts = []
for cid in KEEP:
    ob = obj_for(cid)
    assert ob, 'missing kit component ' + cid
    parts.append(ob)
    r = DECIMATE.get(cid)
    if r:
        active(ob)
        m = ob.modifiers.new('build_decimate', 'DECIMATE')
        m.ratio = r
        m.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=m.name)
        print('DECIMATED', cid, '->', tri_count(ob))

# ---------------------------------------------------------------- relocate wall tools
for cid, (rot, target_xy, yaw) in RELOCATE.items():
    ob = obj_for(cid)
    assert ob, 'missing wall tool ' + cid
    bake(ob)
    ob.data.transform(Matrix.Rotation(math.radians(rot[0]), 4, 'X') @
                      Matrix.Rotation(math.radians(rot[1]), 4, 'Y'))
    place(ob.data, target_xy[0], target_xy[1], yaw, eps=0.0015)
    parts.append(ob)
    print('RELOCATED', cid, 'to', target_xy)

# ---------------------------------------------------------------- clutter materials
def load_mat(name, texfile, rough, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = rough
    if 'Metallic' in bsdf.inputs:
        bsdf.inputs['Metallic'].default_value = metal
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(str(TEX / texfile))
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return m

mat_paper = load_mat('WBKC_Paper', 'T_WBKC_Blueprint_BaseColor.png', 0.82)
mat_books = load_mat('WBKC_Books', 'T_WBKC_Books_BaseColor.png', 0.55)
mat_misc = load_mat('WBKC_Misc', 'T_WBKC_Misc_BaseColor.png', 0.40, metal=0.6)

SWATCH = (0.0215, 0.9785)          # plain-paper corner of the blueprint sheet (Blender v-up)
# Atlas quadrants, converted for Blender UVs (v = 1 - PIL_y/H).
# books atlas (3 cols x 2 rows, PIL): row0 red/navy/green leather, row1 text page/page block/brown
BOOK_RED = (0.0, 0.5, 1 / 3, 1.0)
BOOK_NAVY = (1 / 3, 0.5, 2 / 3, 1.0)
BOOK_LEATHER_GREEN = (2 / 3, 0.5, 1.0, 1.0)
BOOK_TEXT_PAGE = (0.0, 0.0, 1 / 3, 0.5)
BOOK_PAGE_BLOCK = (1 / 3, 0.0, 2 / 3, 0.5)
BOOK_BROWN = (2 / 3, 0.0, 1.0, 0.5)
# misc atlas (PIL quadrants): top-left brass, top-right steel, bottom-left wood, bottom-right yellow
MISC_BRASS = (0.0, 0.5, 0.5, 1.0)
MISC_STEEL = (0.5, 0.5, 1.0, 1.0)
MISC_WOOD = (0.0, 0.0, 0.5, 0.5)
MISC_YELLOW = (0.5, 0.0, 1.0, 0.5)

def uv_rect(me, rect, mode='box'):
    """Project UVs into the atlas rect, always on a layer literally named 'UVMap'
    (primitives in a Chinese-locale file create 'UV贴图'; FBX/UE read UV0 = UVMap)."""
    if 'UVMap' not in me.uv_layers:
        if len(me.uv_layers):
            me.uv_layers[0].name = 'UVMap'
        else:
            me.uv_layers.new(name='UVMap')
    lay = me.uv_layers['UVMap']
    me.uv_layers.active = lay
    u0, v0, u1, v1 = rect
    mn, mx = data_bbox(me)
    sx = max(1e-6, mx[0] - mn[0]); sy = max(1e-6, mx[1] - mn[1])
    for p in me.polygons:
        horiz = abs(p.normal.z) > 0.7
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if mode == 'box' and horiz:
                uv = (u0 + (co.x - mn[0]) / sx * (u1 - u0), v0 + (co.y - mn[1]) / sy * (v1 - v0))
            elif mode == 'side' and not horiz:
                ang = math.atan2(co.y, co.x)
                t = (co.z - mn[2]) / max(1e-6, mx[2] - mn[2])
                uv = (u0 + (ang / math.tau + 0.5) * (u1 - u0), v0 + t * (v1 - v0))
            else:
                uv = SWATCH if mode == 'side' else (u0 + (u1 - u0) * .5, v0 + (v1 - v0) * .5)
            lay.data[li].uv = uv
    me.update()

def new_box(name, sx, sy, sz, mat, rect, rot_y=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = (sx, sy, sz)
    bake(ob)
    if rot_y:
        ob.data.transform(Matrix.Rotation(math.radians(rot_y), 4, 'Y'))
    ob.data.materials.append(mat)
    uv_rect(ob.data, rect)
    return ob

def new_cyl(name, r, depth, mat, rect, axis='z', verts=16, mode='box'):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth)
    ob = bpy.context.active_object
    ob.name = name
    bake(ob)
    ob.data.materials.append(mat)
    uv_rect(ob.data, rect, mode=mode)          # parameterised around Z before any axis turn
    if axis == 'x':
        ob.data.transform(Matrix.Rotation(math.radians(90), 4, 'Y'))
    elif axis == 'y':
        ob.data.transform(Matrix.Rotation(math.radians(90), 4, 'X'))
    ob.data.update()
    return ob

def join(objs, name):
    active(objs[0])
    for o in objs[1:]:
        o.select_set(True)
    bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    return ob

clutter = []

# --- two unrolled blueprint sheets (main work area)
a = new_box('clutter_blueprint_a', 0.62, 0.44, 0.0012, mat_paper, (0, 0, 1, 1))
place(a.data, 58, 150, 8); clutter.append(a)
b = new_box('clutter_blueprint_b', 0.30, 0.21, 0.0012, mat_paper, (0.08, 0.08, 0.92, 0.92))
place(b.data, 55, 14, -24); clutter.append(b)

# --- rolled scrolls (return section), axis along X after yaw
s1 = new_cyl('clutter_scroll_1', 0.022, 0.30, mat_paper, (0, 0, 1, 1), axis='x', verts=14, mode='side')
place(s1.data, 115, 196, 12); clutter.append(s1)
s2 = new_cyl('clutter_scroll_2', 0.019, 0.26, mat_paper, (0.15, 0.15, 0.85, 0.85), axis='x', verts=14, mode='side')
place(s2.data, 112, 243, -8); clutter.append(s2)

# --- stack of three books (return section) + page blocks
def book(idx, sx, sy, sz, rect, x, y, yaw, z_base):
    cover = new_box('clutter_book_%d' % idx, sx, sy, sz, mat_books, rect)
    place(cover.data, x, y, yaw, z_base=z_base, eps=0.001)
    pages = new_box('clutter_book_%d_pages' % idx, sx * 0.94, sy * 0.95, sz * 0.70, mat_books, BOOK_PAGE_BLOCK)
    place(pages.data, x, y, yaw, z_base=z_base, eps=0.001 + sz * 0.15)
    return join([cover, pages], 'clutter_book_%d' % idx)

bk1 = book(1, 0.245, 0.175, 0.042, BOOK_RED, 205, 225, 10, TABLE_Z); clutter.append(bk1)
bk2 = book(2, 0.235, 0.165, 0.036, BOOK_NAVY, 203, 227, 3, TABLE_Z + 0.043); clutter.append(bk2)
bk3 = book(3, 0.225, 0.155, 0.040, BOOK_LEATHER_GREEN, 207, 223, -14, TABLE_Z + 0.080); clutter.append(bk3)

# --- open book (return section): two page slabs in a shallow V over a leather cover
pl = new_box('ob_page_l', 0.168, 0.235, 0.009, mat_books, BOOK_TEXT_PAGE, rot_y=7)
pl.data.transform(Matrix.Translation(Vector((-0.084, 0, 0.016))))
pr = new_box('ob_page_r', 0.168, 0.235, 0.009, mat_books, BOOK_TEXT_PAGE, rot_y=-7)
pr.data.transform(Matrix.Translation(Vector((0.084, 0, 0.016))))
cov = new_box('ob_cover', 0.355, 0.245, 0.006, mat_books, BOOK_LEATHER_GREEN)
cov.data.transform(Matrix.Translation(Vector((0, 0, 0.004))))
spn = new_box('ob_spine', 0.020, 0.245, 0.022, mat_books, BOOK_LEATHER_GREEN)
spn.data.transform(Matrix.Translation(Vector((0, 0, 0.004))))
obk = join([cov, pl, pr, spn], 'clutter_openbook')
place(obk.data, 138, 210, -5); clutter.append(obk)

# --- pencil: hex body + wood tip cone + graphite point (near main blueprint)
body = new_cyl('pc_body', 0.0038, 0.150, mat_misc, MISC_YELLOW, axis='x', verts=6)
bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.0038, radius2=0.0007, depth=0.020,
                                location=(-0.085, 0, 0), rotation=(0, math.radians(-90), 0))
cone = bpy.context.active_object; cone.name = 'pc_tip'; bake(cone)
cone.data.materials.append(mat_misc); uv_rect(cone.data, MISC_WOOD)
bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.0007, depth=0.006,
                                    location=(-0.098, 0, 0), rotation=(0, math.radians(90), 0))
graph = bpy.context.active_object; graph.name = 'pc_graphite'; bake(graph)
graph.data.materials.append(mat_misc); uv_rect(graph.data, MISC_STEEL)
pen = join([body, cone, graph], 'clutter_pencil')
place(pen.data, 40, 118, 34, eps=0.0005); clutter.append(pen)

# --- brass tray + nails (main table, far end)
tray = new_cyl('clutter_tray', 0.090, 0.016, mat_misc, MISC_BRASS, verts=24)
place(tray.data, 70, 235, 0, eps=0.001); clutter.append(tray)
mn, mx = data_bbox(tray.data)
tray_top = mx[2]
tray_cx, tray_cy = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2
nails = []
for i in range(7):
    shaft = new_cyl('n_%d_shaft' % i, 0.0016, 0.030, mat_misc, MISC_STEEL, verts=8)
    head = new_cyl('n_%d_head' % i, 0.0042, 0.0018, mat_misc, MISC_STEEL, verts=8)
    head.data.transform(Matrix.Translation(Vector((0, 0, 0.0159))))
    nail = join([shaft, head], 'clutter_nail_%d' % i)
    nail.data.transform(Matrix.Rotation(math.radians(90), 4, 'X'))
    fx, fy = rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05)
    yaw = rng.uniform(0, 180)
    nail.data.transform(Matrix.Rotation(math.radians(yaw), 4, 'Z'))
    m2, x2 = data_bbox(nail.data)
    nail.data.transform(Matrix.Translation(Vector((tray_cx + fx - (m2[0] + x2[0]) / 2,
                                                   tray_cy + fy - (m2[1] + x2[1]) / 2,
                                                   tray_top + 0.0016 - m2[2]))))
    nails.append(nail)
clutter.extend(nails)

# ---------------------------------------------------------------- final assembly
allparts = parts + clutter
canon = {}
for ob in allparts:
    for i, m in enumerate(ob.data.materials):
        if not m:
            continue
        key = re.sub(r'\.\d{3}$', '', m.name)
        canon.setdefault(key, m)
        if m is not canon[key]:
            ob.data.materials[i] = canon[key]

bpy.ops.object.select_all(action='DESELECT')
for ob in allparts:
    ob.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
final = bpy.context.active_object
final.name = 'SM_WBStandalone_Workbench'
final.data.name = 'SM_WBStandalone_Workbench'

mn, mx = data_bbox(final.data)
cx, cy, cz = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, mn[2]
final.data.transform(Matrix.Translation(Vector((-cx, -cy, -cz))))
final.matrix_world = Matrix.Identity(4)
final.data.update()

active(final)
bpy.ops.object.shade_smooth()
try:
    bpy.ops.object.shade_auto_smooth(angle=math.radians(40))
except Exception as e:
    print('AUTO_SMOOTH_UNAVAILABLE', e)
tri = final.modifiers.new('Export triangulation', 'TRIANGULATE')
tri.keep_custom_normals = True
bpy.ops.object.modifier_apply(modifier=tri.name)

mn, mx = data_bbox(final.data)
bounds = {'min': [round(v * 100, 1) for v in mn], 'max': [round(v * 100, 1) for v in mx]}
slots = [re.sub(r'[._]\d{3}$', '', m.name) for m in final.data.materials if m]
slot_sources = {s: KIT_MAT.get(s) for s in slots}
missing = [s for s, v in slot_sources.items() if not v and not s.startswith('WBKC_')]
if missing:
    raise RuntimeError('No material source for slots: %s' % missing)
fbx = OUT / 'SM_WBStandalone_Workbench.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH'},
                         axis_forward='-Y', axis_up='Z', mesh_smooth_type='FACE',
                         use_tspace=True, bake_anim=False, add_leaf_bones=False)
manifest = {
    'id': 'Workbench_Standalone',
    'name': 'SM_WBStandalone_Workbench',
    'fbx': str(fbx),
    'triangles': tri_count(final),
    'vertices': len(final.data.vertices),
    'bounds_cm': bounds,
    'slots': slots,
    'slot_sources': slot_sources,
    'new_materials': {
        'WBKC_Paper': {'texture': str(TEX / 'T_WBKC_Blueprint_BaseColor.png'), 'roughness': 0.82, 'metallic': 0.0},
        'WBKC_Books': {'texture': str(TEX / 'T_WBKC_Books_BaseColor.png'), 'roughness': 0.55, 'metallic': 0.0},
        'WBKC_Misc': {'texture': str(TEX / 'T_WBKC_Misc_BaseColor.png'), 'roughness': 0.40, 'metallic': 0.6},
    },
    'source_blend': str(OUT / 'StandaloneWorkbench.blend'),
}
(OUT / 'manifest_build.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('STANDALONE_TRIS', manifest['triangles'], 'BOUNDS', bounds, 'SLOTS', len(slots))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'StandaloneWorkbench.blend'))
print('STANDALONE_AUTHORED')
