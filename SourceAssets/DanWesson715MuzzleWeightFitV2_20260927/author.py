"""Rebuild the DW715 target weight from the game's shroud silhouette.

Game render geometry only. Keeps the installed mount and FX exit unchanged.
"""
import bpy
import bmesh
import json
import math
from pathlib import Path
from mathutils import Vector
import numpy as np

OUT = Path(__file__).parent
PREVIOUS = OUT.parent / 'DanWesson715MuzzleModels20260927'
SOURCE = json.loads((PREVIOUS / 'source_frame.json').read_text(encoding='utf-8'))
HOST = json.loads(Path(SOURCE['source_snapshot']).read_text(encoding='utf-8'))
KEY = 'dw715_target_muzzle_weight'
DEST = '/Game/Weapons/DanWesson715/MuzzleModels20260927'
EXPORT = OUT / 'Exports'
EXPORT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
donor = OUT.parent / 'DanWesson715GripBrake20260927/DW715_GripBrake_Editable.blend'
with bpy.data.libraries.load(str(donor), link=False) as (src, dst):
    dst.materials = ['DW715_Steel', 'DW715_DarkSteel']
STEEL, DARK = dst.materials
# Match the less diffuse polished finish of this gun, without changing shared UE materials.
principled = next(n for n in STEEL.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
rough = principled.inputs['Roughness']
if rough.is_linked:
    origin = rough.links[0].from_socket
    scale = STEEL.node_tree.nodes.new('ShaderNodeMath')
    scale.operation = 'MULTIPLY'
    scale.inputs[1].default_value = .2
    STEEL.node_tree.links.new(origin, scale.inputs[0])
    STEEL.node_tree.links.new(scale.outputs[0], rough)
else:
    rough.default_value *= .2


def select(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.hide_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def mesh(name, vertices, faces):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    ob = bpy.data.objects.new(name, data)
    scene.collection.objects.link(ob)
    data.materials.append(STEEL)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(data)
    bm.free()
    return ob


def triangulate(ob):
    select(ob)
    m = ob.modifiers.new('Export triangles', 'TRIANGULATE')
    m.keep_custom_normals = True
    bpy.ops.object.modifier_apply(modifier=m.name)


def loft(name, rings):
    n = len(rings[0][1])
    verts = [(x, y, z) for x, points in rings for y, z in points]
    faces = [(j*n+i, j*n+(i+1)%n, (j+1)*n+(i+1)%n, (j+1)*n+i)
             for j in range(len(rings)-1) for i in range(n)]
    faces += [tuple(reversed(range(n))), tuple((len(rings)-1)*n+i for i in range(n))]
    ob = mesh(name, verts, faces)
    triangulate(ob)
    return ob


def subtract(ob, cutter, label):
    select(ob)
    m = ob.modifiers.new(label, 'BOOLEAN')
    m.operation = 'DIFFERENCE'
    m.solver = 'EXACT'
    m.object = cutter
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


frame = np.array(SOURCE['ue_mount_matrix'])
host_vertices = (np.array(HOST['positions']) - frame[:3, 3]) @ frame[:3, :3]
host_vertices *= np.array([.01, -.01, .01])
host_faces = np.array(HOST['triangles'], dtype=int)
keep = [i for i, m in enumerate(HOST['materials'])
        if HOST['slots'][m] in ('M_DW715_Hero_Steel', 'M_DW715_Hero_Frame')]
triangles = host_vertices[host_faces[keep]]


def hull(points):
    pts = sorted(set((round(y, 8), round(z, 8)) for y, z in points))
    def cross(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lo, hi = [], []
    for p in pts:
        while len(lo)>1 and cross(lo[-2], lo[-1], p)<=0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi)>1 and cross(hi[-2], hi[-1], p)<=0: hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def section(x):
    crossing = triangles[(triangles[:, :, 0].min(axis=1)<x) & (triangles[:, :, 0].max(axis=1)>x)]
    points = []
    for tri in crossing:
        for i in range(3):
            a, b = tri[i], tri[(i+1)%3]
            if (a[0]-x)*(b[0]-x)<0:
                p = a+(b-a)*((x-a[0])/(b[0]-a[0]))
                points.append(p[1:])
    return hull(points)


CENTER = np.array([-.000071, -.0048])
COUNT = 96


def radial_profile(poly):
    result = []
    for i in range(COUNT):
        a = i*2*math.pi/COUNT
        d = np.array([math.cos(a), math.sin(a)])
        hits = []
        for j, p in enumerate(poly):
            p, q = np.array(p), np.array(poly[(j+1)%len(poly)])
            e = q-p
            m = np.column_stack((d, -e))
            if abs(np.linalg.det(m))<1.e-12: continue
            t, u = np.linalg.solve(m, p-CENTER)
            if t>0 and -.00001<=u<=1.00001: hits.append(t)
        if not hits: raise RuntimeError('Missing source contour at radial section')
        result.append(CENTER+d*max(hits))
    return np.array(result)


def smooth(t):
    t = max(0, min(1, t))
    return t*t*(3-2*t)


# The real shroud narrows towards the underside. Follow that profile instead of
# enclosing its empty corners in a rectangular block. Rear margin grows gradually.
base = radial_profile(section(-.018))
outer_rings = []
xs = [-.040, -.0395, -.039, -.038, -.036, -.034, -.031, -.028, -.024,
      -.020, -.014, -.008, -.003, .001, .004, .007, .009, .0102, .011, .0115, .0117]
for x in xs:
    shoulder = smooth((x+.040)/.022)
    front = smooth((x-.002)/.0097)
    host = radial_profile(section(min(x, -.004))) if x<-.018 else base.copy()
    points = []
    for i, p in enumerate(host):
        delta = p-CENTER
        direction = delta/np.linalg.norm(delta)
        bottom = max(0, -direction[1])
        thickness = .00013 + shoulder*(.00105 + .00055*bottom)
        # A rolled front shoulder creates a rounded nose instead of a square slab.
        nose = .0009*smooth((x-.009)/.0027)
        q = p+direction*(thickness-nose)
        # The upper edge blends into the original shroud below its sight rib.
        q[1] = min(q[1], .0103-.0024*front)
        points.append(q)
    outer_rings.append((x, points))
weight = loft(KEY, outer_rings)

# The interior follows actual sections independently, so the tapered rear edge
# meets the native surface all around instead of leaving a full-width top trench.
inner_rings = []
for x in [-.044, -.041, -.040, -.038, -.034, -.028, -.020, -.014, -.008, -.004, -.002, -.001, .00035]:
    profile = radial_profile(section(min(x, -.001)))
    direction = profile-CENTER
    profile += direction/np.linalg.norm(direction, axis=1)[:, None]*.000045
    inner_rings.append((x, profile))
subtract(weight, loft('Conforming inner contact', inner_rings), 'Native shroud overlap')

# Render-only bore and sight clearance; no extra sight or ornamental block.
bpy.ops.mesh.primitive_cylinder_add(vertices=80, radius=.00473, depth=.065,
    end_fill_type='NGON', location=(-.010, 0, .00017), rotation=(0, math.pi/2, 0))
opening = bpy.context.object
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
subtract(weight, opening, 'Visible front opening')
select(weight)
bevel = weight.modifiers.new('Continuous edge rounding', 'BEVEL')
bevel.width = .00038
bevel.segments = 4
bevel.limit_method = 'ANGLE'
bevel.angle_limit = math.radians(24)
bevel.use_clamp_overlap = True
bevel.harden_normals = True
bpy.ops.object.modifier_apply(modifier=bevel.name)
weight.data.materials.append(DARK)
weight.data.update()
for p in weight.data.polygons:
    p.use_smooth = True
    if math.hypot(p.center.y, p.center.z-.00017)<.00494:
        p.material_index = 1
bm = bmesh.new()
bm.from_mesh(weight.data)
for e in bm.edges:
    if e.is_manifold: e.smooth = e.calc_face_angle(0)<math.radians(38)
bm.to_mesh(weight.data)
bm.free()
uv = weight.data.uv_layers.new(name='Physical10cm')
for p in weight.data.polygons:
    axis = max(range(3), key=lambda a: abs(p.normal[a]))
    axes = (0, 2) if axis==1 else (1, 2) if axis==0 else (0, 1)
    for li in p.loop_indices:
        co = weight.data.vertices[weight.data.loops[li].vertex_index].co
        uv.data[li].uv = (co[axes[0]]/.1, co[axes[1]]/.1)
select(weight)
normal = weight.modifiers.new('Polished contour normals', 'WEIGHTED_NORMAL')
normal.keep_sharp = True
normal.weight = 40
bpy.ops.object.modifier_apply(modifier=normal.name)
triangulate(weight)
weight['part_id'] = KEY
weight['mount_reference'] = 'WPN_SOCKET_Muzzle; unchanged installed +X frame'
weight['revision'] = 'V2 contoured lower shroud; feathered rear shoulder'
weight['usage'] = 'Game render mesh only; no collision or fabrication geometry'

lod_collection = bpy.data.collections.new('ExportLODs')
scene.collection.children.link(lod_collection)
group = bpy.data.objects.new('SM_'+KEY, None)
lod_collection.objects.link(group)
group['fbx_type'] = 'LodGroup'
lods = []
for level, ratio in [(0, 1), (1, .55), (2, .28)]:
    ob = weight.copy()
    ob.data = weight.data.copy()
    ob.name = 'SM_'+KEY+'_LOD'+str(level)
    lod_collection.objects.link(ob)
    ob.parent = group
    if level:
        select(ob)
        dec = ob.modifiers.new('Distant reduction', 'DECIMATE')
        dec.ratio = ratio
        dec.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=dec.name)
    lods.append(ob)
select(group)
for ob in lods: ob.select_set(True)
fbx = EXPORT / ('SM_'+KEY+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True,
    object_types={'MESH', 'EMPTY'}, axis_forward='-Y', axis_up='Z', bake_anim=False,
    mesh_smooth_type='FACE', use_tspace=False, use_custom_props=True)
for ob in lods: ob.hide_set(True)
group.hide_set(True)
lod_collection.hide_render = True

# Preserve a real host reference for editing; it is never exported or rendered.
used = sorted({v for i in keep for v in HOST['triangles'][i]})
remap = {v: i for i, v in enumerate(used)}
reference = mesh('DW715_HOST_REFERENCE', host_vertices[used].tolist(),
    [tuple(remap[v] for v in reversed(HOST['triangles'][i])) for i in keep])
reference.display_type = 'WIRE'
reference.hide_render = True
reference.hide_select = True
select(weight)
bpy.ops.file.pack_all()
source_path = OUT / (KEY+'_Editable.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(source_path))
report = {'revision': 'V2', 'host_asset': SOURCE['host_asset'],
    'source_snapshot': SOURCE['source_snapshot'], 'ue_mount_matrix': SOURCE['ue_mount_matrix'],
    'game_tested': False, 'parts': {KEY: {'fbx': str(fbx), 'source': str(source_path),
    'mesh': DEST+'/Meshes/SM_'+KEY, 'tip_cm': [1.17, 0, 0],
    'lod_triangles': [len(ob.data.polygons) for ob in lods],
    'materials': ['DW715_Steel', 'DW715_DarkSteel']}},
    'changes': ['Native tapered lower contour', 'Long feathered rear transition',
                'Conforming interior and open sight rib', 'Rolled nose and polished metal finish']}
(OUT / 'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('DW715_TARGET_WEIGHT_V2_AUTHORED '+str(report['parts'][KEY]['lod_triangles']), flush=True)
