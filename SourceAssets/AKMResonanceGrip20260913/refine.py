"""Repair the AKM Resonance II game prop's cut upper frame and adapter silhouette.

Only the AKM static attachment is exported. Existing lower grasp surfaces and
animation assets stay in their original weapon-root coordinates. No rendering
or test harness is run by this authoring script.
"""
import json
import math
from pathlib import Path

import bmesh
import bpy

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
SOURCE = OUT / 'Before/SM_AKM_angled.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
grip = next(o for o in bpy.data.objects if o.type == 'MESH')
if grip.name not in scene.objects:
    scene.collection.objects.link(grip)
grip.name = 'AKM_Resonance_ExistingGraspFrame'

# Remove only the old rail, its blocks, and its single square front standoff.
adapter_slots = {i for i, m in enumerate(grip.data.materials) if m and m.name == 'AKM_AdapterSteel'}
bm = bmesh.new()
bm.from_mesh(grip.data)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in adapter_slots], context='FACES')
# The inherited bevel output contains coincident sliver vertices. Weld only at
# sub-micron tolerance; the grasp silhouette is not reshaped.
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=1e-8)
bm.to_mesh(grip.data)
bm.free()
grip.data.update()

# Use the existing AKM receiver-metal texture set, with its own full-tile UVs.
steel = bpy.data.materials.new('AKM_Resonance_Steel')
steel.use_nodes = True
nodes = steel.node_tree.nodes
links = steel.node_tree.links
nodes.clear()
bsdf = nodes.new('ShaderNodeBsdfPrincipled')
output = nodes.new('ShaderNodeOutputMaterial')
links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
for kind, socket in [('Base_color', 'Base Color'), ('Metallic', 'Metallic'), ('Roughness', 'Roughness'), ('Normal_OpenGL', 'Normal')]:
    path = ROOT / 'SourceAssets/AKMArmSupport20260911/Metal' / ('T_AKM_Mount_' + kind + '.png')
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(str(path), check_existing=True)
    if kind != 'Base_color':
        tex.image.colorspace_settings.name = 'Non-Color'
    if kind == 'Normal_OpenGL':
        normal = nodes.new('ShaderNodeNormalMap')
        links.new(tex.outputs['Color'], normal.inputs['Color'])
        links.new(normal.outputs['Normal'], bsdf.inputs[socket])
    else:
        links.new(tex.outputs['Color'], bsdf.inputs[socket])

old_steel_slots = {i for i, m in enumerate(grip.data.materials) if m and ('Body' in m.name or 'AdapterSteel' in m.name or 'Recess' in m.name)}
for i in old_steel_slots:
    grip.data.materials[i] = steel

def project_uv(obj, metal_slots=None):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    scene.tool_settings.mesh_select_mode = (False, False, True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    for poly in obj.data.polygons:
        poly.select = metal_slots is None or poly.material_index in metal_slots
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.018)
    bpy.ops.object.mode_set(mode='OBJECT')
    # Newly created UV layer names are localized in Blender. Use the source name
    # so joining the new bridge does not create a second, empty primary UV set.
    obj.data.uv_layers.active.name = 'UVMap'

# The old atlas UVs remain on the polymer inlays. New metal uses the AKM crop.
project_uv(grip, old_steel_slots)
parts = [grip]

def finish(obj, bevel=.00065):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    obj.data.materials.clear()
    obj.data.materials.append(steel)
    bpy.context.view_layer.objects.active = obj
    bevel_mod = obj.modifiers.new('Small continuous edge bevel', 'BEVEL')
    bevel_mod.width = bevel
    bevel_mod.segments = 3
    bevel_mod.harden_normals = True
    bpy.ops.object.modifier_apply(modifier=bevel_mod.name)
    for face in obj.data.polygons:
        face.use_smooth = True
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35), keep_sharp_edges=True)
    weighted = obj.modifiers.new('Weighted surface normals', 'WEIGHTED_NORMAL')
    weighted.keep_sharp = True
    bpy.ops.object.modifier_apply(modifier=weighted.name)
    project_uv(obj)
    parts.append(obj)
    return obj

# A single upper U connects both existing cut ends. The central opening remains
# open for the index/middle/ring grasp; its lower frame is copied without scaling.
# The rear post leans back to meet the rear cut shoulder instead of ending in air.
outline = [
    (-.3645, -.0108), (-.3645, .0190), (-.3590, .0260),
    (-.2390, .0260), (-.2335, .0190), (-.2375, -.0108),
    (-.2510, -.0108), (-.2480, .0205),
    (-.3500, .0205), (-.3515, -.0108),
]
verts = []
for side in [-1, 1]:
    for y, z in outline:
        t = max(0., min(1., (z + .0108) / .0368))
        center_x = .00027 + t * .00053
        half_width = .0104 + t * .0006
        verts.append((center_x + side * half_width, y, z))
n = len(outline)
faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, n * 2))]
faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
mesh = bpy.data.meshes.new('Closed rear bridge and tapered upper frame')
mesh.from_pydata(verts, [], faces)
mesh.update()
upper = bpy.data.objects.new('AKM_Resonance_ContinuousUpperFrame', mesh)
scene.collection.objects.link(upper)
bm = bmesh.new()
bm.from_mesh(mesh)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(mesh)
bm.free()
finish(upper)

for label, y in [('Front', -.330), ('Rear', -.270)]:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(.0008, y, .02725))
    obj = bpy.context.object
    obj.name = 'AKM_Resonance_' + label + 'MountLip'
    obj.scale = (.026, .007, .0035)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    finish(obj, .00045)

# Restrained side fasteners break up the new supports without oversized blocks.
for y in [-.3575, -.2425]:
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=.0021, depth=.0008,
            location=(.00054 + side * .0112, y, .008), rotation=(0, math.pi / 2, 0))
        obj = bpy.context.object
        obj.name = 'AKM_Resonance_SideFastener'
        finish(obj, .00018)

scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
bpy.ops.object.select_all(action='DESELECT')
for part in parts:
    part.select_set(True)
bpy.context.view_layer.objects.active = grip
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'AKM_ResonanceGrip_Editable.blend'))
bpy.ops.object.join()
grip = bpy.context.object
grip.name = 'SM_AKM_angled'
# Triangulation keeps the concave upper U intact through FBX import.
tri = grip.modifiers.new('Export triangles', 'TRIANGULATE')
tri.keep_custom_normals = True
bpy.ops.object.modifier_apply(modifier=tri.name)
bpy.ops.export_scene.fbx(filepath=str(OUT / 'SM_AKM_angled.fbx'), use_selection=True,
    object_types={'MESH'}, axis_forward='-Y', axis_up='Z', bake_anim=False,
    mesh_smooth_type='FACE', use_tspace=False, path_mode='STRIP')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'AKM_ResonanceGrip_Export.blend'))
(OUT / 'authoring.json').write_text(json.dumps({
    'source': str(SOURCE), 'asset': '/Game/Weapons/AKMIntegration/SovietFab/GripErgonomic/SM_AKM_angled',
    'method': 'Retain lower contact geometry; replace one-sided block adapter with continuous tapered front/rear upper frame',
    'existing_grasp_geometry_scaled': False, 'animations_changed': False,
    'metal': '/Game/Weapons/AKMIntegration/SovietFab/ArmSupport/M_AKM_Soviet_MountSteel',
    'rendered': False, 'runtime_tested': False,
}, indent=2), encoding='utf-8')
print('AKM_RESONANCE_EXPORTED', str(OUT / 'SM_AKM_angled.fbx'), flush=True)
