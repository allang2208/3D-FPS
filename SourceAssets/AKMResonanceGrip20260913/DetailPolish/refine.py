"""Contour/detail polish for the AKM Resonance II visual game attachment.

Uses the last integrated editable mesh as a frozen authoring baseline. No
animation edits, game launch, preview rendering, or test harness is performed.
"""
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent
SOURCE = OUT / 'Before/AKM_ResonanceGrip_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
grip = bpy.data.objects['AKM_Resonance_ExistingGraspFrame']
steel = bpy.data.materials['AKM_Resonance_Steel']
for obj in list(scene.objects):
    if obj != grip:
        bpy.data.objects.remove(obj, do_unlink=True)

# Compact the forward nose only. The hand's grasp section, lower heel, rear
# support contact, and weapon-root origin remain fixed. Smoothstep makes the
# change fade into the diagonal instead of creating another clipping plane.
for v in grip.data.vertices:
    t = max(0., min(1., (-v.co.y - .3320) / (.3655564 - .3320)))
    w = t * t * (3. - 2. * t)
    v.co.y += .0080 * w
    center_x = .00079 - (v.co.z + .0155064) * .085
    v.co.x = center_x + (v.co.x - center_x) * (1. - .08 * w)
grip.data.update()
parts = [grip]

def select(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

def uv(obj, metal_only=False):
    select(obj)
    scene.tool_settings.mesh_select_mode = (False, False, True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    for f in obj.data.polygons:
        f.select = not metal_only or obj.data.materials[f.material_index] == steel
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.016)
    bpy.ops.object.mode_set(mode='OBJECT')
    active = obj.data.uv_layers.active
    # Boolean cutters can bring in a localized secondary UV layer. Retain the
    # freshly authored layer only, including the preserved polymer coordinates.
    for layer in list(obj.data.uv_layers):
        if layer != active:
            obj.data.uv_layers.remove(layer)
    obj.data.uv_layers.active.name = 'UVMap'
    obj.data.uv_layers.active.active_render = True

def normals(obj):
    select(obj)
    for f in obj.data.polygons:
        f.use_smooth = True
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(38), keep_sharp_edges=True)
    mod = obj.modifiers.new('Consistent weighted highlights', 'WEIGHTED_NORMAL')
    mod.keep_sharp = True
    bpy.ops.object.modifier_apply(modifier=mod.name)

def bevel(obj, width, segments=4):
    select(obj)
    mod = obj.modifiers.new('Fine rolled edge', 'BEVEL')
    mod.width = width
    mod.segments = segments
    mod.harden_normals = True
    bpy.ops.object.modifier_apply(modifier=mod.name)

def finish_topology(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    tolerance = 1e-7 if obj == grip else 3e-6
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=tolerance)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=tolerance)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()

def rounded_loop(points, distances, steps=6):
    result = []
    n = len(points)
    for i, p in enumerate(points):
        a, b, c = Vector(points[(i - 1) % n]), Vector(p), Vector(points[(i + 1) % n])
        distance = min(distances[i], (a - b).length * .35, (c - b).length * .35)
        start, end = b + (a - b).normalized() * distance, b + (c - b).normalized() * distance
        for j in range(steps + 1):
            t = j / steps
            result.append(tuple((1 - t) ** 2 * start + 2 * (1 - t) * t * b + t ** 2 * end))
    return result

def profile(name, outline, left, right):
    vertices = [(fn(y, z), y, z) for fn in [left, right] for y, z in outline]
    n = len(outline)
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    faces.extend((i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj.data.materials.append(steel)
    return obj

def width(y, z):
    height = max(0., min(1., (z + .0106) / .0364))
    # Keep the cap planar. Nose narrowing is already authored on the lower
    # frame; a second nonlinear width taper makes a twisted Boolean side face.
    return .0104 + .0002 * height

def center(z):
    return .00027 + .00053 * max(0., min(1., (z + .0106) / .0364))

outline = rounded_loop([
    (-.3565, -.0106), (-.3560, .0105), (-.3500, .0258),
    (-.2405, .0258), (-.2345, .0180), (-.2375, -.0106),
    (-.2500, -.0106), (-.2475, .0199),
    (-.3470, .0199), (-.3455, -.0106),
], [.00065, .0025, .0028, .0022, .0025, .00065, .00065, .0015, .0015, .00065])
upper = profile('AKM_Resonance_SweptUpperFrame', outline,
                lambda y, z: center(z) - width(y, z),
                lambda y, z: center(z) + width(y, z))
bevel(upper, .00042)
parts.append(upper)

def boolean(target, cutter, name):
    select(target)
    mod = target.modifiers.new(name, 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)

def capsule(a, b, radius, steps=12):
    a, b = Vector(a), Vector(b)
    direction = (b - a).normalized()
    angle = math.atan2(direction.y, direction.x)
    out = []
    for origin, start in [(b, angle - math.pi / 2), (a, angle + math.pi / 2)]:
        for i in range(steps + 1):
            t = start + i * math.pi / steps
            out.append((origin.x + math.cos(t) * radius, origin.y + math.sin(t) * radius))
    return out

# A shallow real recess follows the rail, adding a fine line without a raised
# strip or extra silhouette. It stays within the top web above the grasp opening.
groove = capsule((-.332, .02285), (-.259, .02285), .00068)
for side in [-1, 1]:
    x0, x1 = sorted([.0008 + side * .01008, .0008 + side * .014])
    cutter = profile('Rail channel cutter', groove, lambda y, z: x0, lambda y, z: x1)
    boolean(upper, cutter, 'Shallow rail-side channel')

def cylinder(name, x, y, z, radius, depth, vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
        location=(x, y, z), rotation=(0, math.pi / 2, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(steel)
    select(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj

# Recessed circular heads with genuine hexagonal sockets, nearly flush with the
# shaped side wall. Socket cavities are backed by the head; no through-hole.
for label, y, z in [('Front', -.3507, .0017), ('Rear', -.2433, .0020)]:
    for side in [-1, 1]:
        surface = center(z) + side * width(y, z)
        pocket = cylinder('Fastener pocket cutter', surface - side * .00030, y, z, .00205, .00110)
        boolean(upper, pocket, 'Shallow countersunk pocket')
        head = cylinder('AKM_Resonance_' + label + 'FlushHead', surface - side * .00018, y, z, .00180, .00072)
        bevel(head, .00012, 3)
        socket = cylinder('Hex socket cutter', surface + side * .00022, y, z, .00077, .00085, 6)
        boolean(head, socket, 'Recessed hex socket')
        parts.append(head)

# The top lips keep their existing handguard contact height and centers, but
# replace protruding rectangular tabs with narrower rounded trapezoid shoulders.
for label, y in [('Front', -.330), ('Rear', -.270)]:
    lip_outline = rounded_loop([
        (y - .0040, .0253), (y - .0031, .0290),
        (y + .0031, .0290), (y + .0040, .0253),
    ], [.00045, .00065, .00065, .00045], 5)
    lip = profile('AKM_Resonance_' + label + 'ContouredMountLip', lip_outline,
        lambda yy, z: .0008 - (.0119 - .0005 * max(0., (z - .0253) / .0037)),
        lambda yy, z: .0008 + (.0119 - .0005 * max(0., (z - .0253) / .0037)))
    bevel(lip, .00024)
    parts.append(lip)

# Finish the channel/pocket lips after all cuts. Re-project the changed metal
# while keeping the inherited polymer atlas UVs in the actual grasp section.
for obj in parts:
    # Resolve coincident remnants from the micro-bevel and Boolean operations
    # before authoring final corner normals and the single export UV channel.
    finish_topology(obj)
    normals(obj)
    uv(obj, metal_only=obj == grip)
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
bpy.ops.object.select_all(action='DESELECT')
for obj in parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active = grip
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'AKM_ResonanceGrip_Polished_Editable.blend'))
bpy.ops.object.join()
grip = bpy.context.object
grip.name = 'SM_AKM_angled'
tri = grip.modifiers.new('Export triangles', 'TRIANGULATE')
tri.keep_custom_normals = True
bpy.ops.object.modifier_apply(modifier=tri.name)
bpy.ops.export_scene.fbx(filepath=str(OUT / 'SM_AKM_angled.fbx'), use_selection=True,
    object_types={'MESH'}, axis_forward='-Y', axis_up='Z', bake_anim=False,
    mesh_smooth_type='FACE', use_tspace=False, path_mode='STRIP')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'AKM_ResonanceGrip_Polished_Export.blend'))
(OUT / 'authoring.json').write_text(json.dumps({
    'source': str(SOURCE), 'front_nose_reduction_m': .008,
    'front_only_width_reduction': .08, 'upper_profile': 'rounded swept shoulders',
    'details': ['recessed rail channels', 'nearly flush hex-socket heads', 'rounded tapered mounting lips'],
    'animations_changed': False, 'mount_transform_changed': False,
    'runtime_tested': False, 'rendered': False,
}, indent=2), encoding='utf-8')
print('AKM_RESONANCE_POLISH_EXPORTED', str(OUT / 'SM_AKM_angled.fbx'), flush=True)
