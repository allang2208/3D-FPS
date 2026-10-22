"""Kukri (Fab, powers28) -> grip-centred game mesh, editable blend, FBX and inventory icon.

Run: blender -b --factory-startup --python author_kukri_model.py

Local frame of the exported mesh (UE static-mesh space, centimetres):
  origin = centre of the closed right fist on the handle centreline,
  +Z     = handle centreline towards the blade tip,
  +X     = cutting edge (the concave belly) side, perpendicular to +Z,
  +Y     = flat of the blade.
The first-person rig attaches the mesh to WPN_root with the identity transform, so
WPN_root is authored as this grip frame in every kukri clip.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix

P = Path(__file__).resolve().parent
SRC = Path(r"D:\FPS3D\VaultCache\FabLibrary\Kukri-0a08e297\fbx\kukri_extracted")
SCALE = 1.65            # source is 23.4 cm without lanyard; game kukri ~38.6 cm
GRIP_X_ORIG = -1.3      # source cm along the length axis (tip -X, pommel +X)
GRIP_FIT = (-4.0, 2.4)  # source cm: straight handle section used for the centreline fit
OUT_FBX = P / 'Export' / 'SM_Kukri.fbx'
OUT_BLEND = P / 'Kukri_Editable.blend'
ICON = P / 'Icons' / 'ue_kukri.png'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(SRC / 'Model' / 'kukri.fbx'))
obj = bpy.data.objects['kukri']
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
me = obj.data
cm = [v.co * 100.0 for v in me.vertices]     # source centimetres, x = length axis, z = edge(-)/spine(+)

# Handle centreline: mid height of each slice through the straight grip section.
xs, zs = [], []
for i in range(16):
    a = GRIP_FIT[0] + (GRIP_FIT[1] - GRIP_FIT[0]) * i / 16
    b = GRIP_FIT[0] + (GRIP_FIT[1] - GRIP_FIT[0]) * (i + 1) / 16
    sl = [v for v in cm if a <= v.x <= b]
    if len(sl) < 4:
        continue
    xs.append((a + b) / 2)
    zs.append((min(v.z for v in sl) + max(v.z for v in sl)) / 2)
n = len(xs)
mx, mz = sum(xs) / n, sum(zs) / n
slope = sum((x - mx) * (z - mz) for x, z in zip(xs, zs)) / sum((x - mx) ** 2 for x in xs)
origin = Vector((GRIP_X_ORIG, 0.0, mz + slope * (GRIP_X_ORIG - mx)))
blade = Vector((-1.0, 0.0, -slope)).normalized()           # towards the tip
edge = Vector((0.0, 0.0, -1.0))
edge = (edge - blade * edge.dot(blade)).normalized()
flat = blade.cross(edge)                                     # Y = Z x X
R = Matrix((edge, flat, blade))                             # rows: new axes in source space
xf = Matrix.Translation(Vector()) @ (R.to_4x4()) @ Matrix.Translation(-origin)
for v in me.vertices:
    p = xf @ (v.co * 100.0)
    v.co = p * SCALE / 100.0                                 # metres in Blender, centimetres in UE
me.update()
obj.name = obj.data.name = 'SM_Kukri'


def fix_blade_normals(mesh, angle_deg=22.0):
    """V5 (user: blade still a 'mosaic').  The Fab low-poly carries one smooth normal across the flat,
    the grind bevel and the edge (corner/face deviation median 20 deg, p90 47 deg); the baked normal map
    only hides that when the engine reproduces the baker's exact tangent frame, otherwise the flat
    shows its triangles.  On the steel islands (metallic >= 0.5 in Textures/T_Kukri_ORM.png) rebuild
    the corner normals from face normals smoothed only below angle_deg, so flats are flat and the grind
    line stays crisp; the wood/brass/cord corners keep the Fab normals their bake was made for."""
    import numpy as np
    img = bpy.data.images.load(str(P / 'Textures' / 'T_Kukri_ORM.png'))
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    metal = px.reshape(h, w, 4)[:, :, 2]          # Blender rows start at the bottom (v = 0)
    uv = mesh.uv_layers[0].data
    steel = []
    for p in mesh.polygons:
        u = sum(uv[i].uv.x for i in p.loop_indices) / p.loop_total
        v = sum(uv[i].uv.y for i in p.loop_indices) / p.loop_total
        steel.append(metal[min(h - 1, max(0, int(v * h))), min(w - 1, max(0, int(u * w)))] >= .5)
    cos_lim = math.cos(math.radians(angle_deg))
    vert_faces = [[] for _ in mesh.vertices]
    for p in mesh.polygons:
        if steel[p.index]:
            for vi in p.vertices:
                vert_faces[vi].append(p.index)
    old = [Vector(c.vector) for c in mesh.corner_normals]
    new = list(old)
    for p in mesh.polygons:
        if not steel[p.index]:
            continue
        fn = p.normal
        for li in p.loop_indices:
            vi = mesh.loops[li].vertex_index
            acc = Vector()
            for fi in vert_faces[vi]:
                q = mesh.polygons[fi]
                if q.normal.dot(fn) >= cos_lim:
                    acc += q.normal * q.area
            new[li] = acc.normalized() if acc.length > 1e-12 else fn.copy()
    mesh.normals_split_custom_set([tuple(n) for n in new])
    bpy.data.images.remove(img)
    return sum(steel), len(steel)


steel_faces, all_faces = fix_blade_normals(me)
print('KUKRI_NORMALS steel faces %d / %d rebuilt' % (steel_faces, all_faces), flush=True)
mat = me.materials[0]
mat.name = 'M_Kukri'

# Measurements in the final frame (cm) for the runtime/authoring contract.
fin = [v.co * 100.0 for v in me.vertices]
def rng(axis):
    return [round(min(getattr(v, axis) for v in fin), 3), round(max(getattr(v, axis) for v in fin), 3)]
blade_pts = [v for v in fin if v.z > 9.0]
tip = max(fin, key=lambda v: v.z)
handle_pts = [v for v in fin if -4.0 < v.z < 4.0]
info = dict(scale=SCALE, grip_origin_source_cm=list(origin), handle_slope=slope,
            bounds_cm=dict(x=rng('x'), y=rng('y'), z=rng('z')),
            tip_cm=[round(tip.x, 3), round(tip.y, 3), round(tip.z, 3)],
            handle_height_cm=round(max(v.x for v in handle_pts) - min(v.x for v in handle_pts), 3),
            handle_thickness_cm=round(max(v.y for v in handle_pts) - min(v.y for v in handle_pts), 3),
            profile=[(z, round(max((abs(v.y) for v in fin if z - 1 <= v.z < z + 1), default=0) * 2, 2),
                      round(min((v.x for v in fin if z - 1 <= v.z < z + 1), default=0), 2),
                      round(max((v.x for v in fin if z - 1 <= v.z < z + 1), default=0), 2))
                     for z in range(-16, 26, 2)],
            triangles=sum(len(p.vertices) - 2 for p in me.polygons),
            frame='UE static mesh: +Z blade, +X edge, origin = right-fist grip centre')

# Material for Blender previews/icons (UE builds its own Substrate material).
tex = SRC / 'Textures' / 'PBR'
mat.use_nodes = True
nt = mat.node_tree
for node in list(nt.nodes):
    nt.nodes.remove(node)
out = nt.nodes.new('ShaderNodeOutputMaterial')
bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
def image(name, colour):
    node = nt.nodes.new('ShaderNodeTexImage')
    node.image = bpy.data.images.load(str(tex / name))
    node.image.colorspace_settings.name = 'sRGB' if colour else 'Non-Color'
    return node
nt.links.new(image('kukri_BaseColor.png', True).outputs['Color'], bsdf.inputs['Base Color'])
nt.links.new(image('kukri_Metallic.png', False).outputs['Color'], bsdf.inputs['Metallic'])
nt.links.new(image('kukri_Roughness.png', False).outputs['Color'], bsdf.inputs['Roughness'])
nm = nt.nodes.new('ShaderNodeNormalMap')
nt.links.new(image('kukri_Normal.png', False).outputs['Color'], nm.inputs['Color'])
nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])

OUT_FBX.parent.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT_FBX), use_selection=True, object_types={'MESH'},
                         mesh_smooth_type='FACE', use_tspace=True, path_mode='STRIP',
                         apply_unit_scale=True, bake_space_transform=False, add_leaf_bones=False)

# Inventory icon: 1x3 vertical cell art (256x768), blade up, 91% of the height.
ICON.parent.mkdir(exist_ok=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 256, 768
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = -2.6
scene.world = bpy.data.worlds.new('Kukri menu studio')
scene.world.use_nodes = True
bg = next(nd for nd in scene.world.node_tree.nodes if nd.type == 'BACKGROUND')
bg.inputs['Color'].default_value = (.2, .2, .2, 1)
bg.inputs['Strength'].default_value = .65
cam = bpy.data.objects.new('IconCamera', bpy.data.cameras.new('IconCamera'))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.type = 'ORTHO'
cam.data.clip_start = .001
# Look along +Y at the flat, blade up (same camera basis as the existing melee inventory art).
cam.rotation_euler = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0))).to_euler()
cam_dir = Vector((0, 1, 0))
pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
centre = sum(pts, Vector()) / 8
height = max(p.z for p in pts) - min(p.z for p in pts)
width = max(p.x for p in pts) - min(p.x for p in pts)
cam.location = centre - cam_dir * 1.5
cam.data.ortho_scale = max(height / .91, width / .91 * 3.0)
cam.data.sensor_fit = 'VERTICAL'
for name, offset, energy, size in [('Key', (-.38, -.60, .35), 95, .75), ('Fill', (.32, -.42, -.15), 45, .65), ('Rim', (-.12, .28, .30), 65, .5)]:
    lamp = bpy.data.objects.new(name, bpy.data.lights.new(name, 'AREA'))
    scene.collection.objects.link(lamp)
    lamp.data.energy = energy
    lamp.data.shape = 'DISK'
    lamp.data.size = size
    lamp.location = centre + Vector(offset)
    lamp.rotation_euler = (centre - lamp.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = str(ICON)
bpy.ops.render.render(write_still=True)

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
(P / 'model.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
print('KUKRI_MODEL ' + json.dumps(info), flush=True)

