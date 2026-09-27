"""Blender background production: continuous pouring metal and a mould-fitted surface.

Mesh-local centimetre contract matches SM_BlastFurnace; FBX converts metres once.
No preview or scene render. UV.x measures travel time (stream) / X (mould surface).
"""
import json
import math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/FurnaceCasting20260926'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1.0
verts, faces, texcoords, slots = [], [], [], []

def vertex(p, uv):
    verts.append((p[0] * .01, -p[1] * .01, p[2] * .01))
    texcoords.append(uv)
    return len(verts) - 1

def face(indices, slot):
    # UE -> Blender reflection reverses winding.
    faces.append(tuple(reversed(indices)))
    slots.append(slot)

# The outlet is horizontal; gravity then carries the stream into the central mould.
# The old endpoint at x=32.9 was behind the mould, and its ballistic formula missed z=20.
flight = math.sqrt(2 * (63.5 - 26.2) / 600)
vx = (45 - 24.7) / flight
channel_time = (24.7 - 17.5) / vx
total_time = channel_time + flight
rings, sides = 64, 12
for i in range(rings + 1):
    t = i / rings * total_time
    fall = max(0., t - channel_time)
    center = Vector((17.5 + vx * t, 0, 63.5 - 300 * fall * fall))
    tangent = Vector((vx, 0, -600 * fall)).normalized()
    axis_a = Vector((0, 1, 0))
    axis_b = tangent.cross(axis_a).normalized()
    radius = 1.45 * math.sqrt(vx / math.sqrt(vx * vx + (600 * fall) ** 2))
    radius = max(.78, radius)
    for j in range(sides + 1):
        angle = 2 * math.pi * j / sides
        p = center + radius * (math.cos(angle) * axis_a + math.sin(angle) * axis_b)
        vertex(p, (t / total_time, j / sides))
for i in range(rings):
    for j in range(sides):
        a = i * (sides + 1) + j
        face((a, a + 1, a + sides + 2, a + sides + 1), 0)

# A rounded rectangle inside the actual cavity (top is z=28.5, floor z=21.8).
# Surface begins at the floor, rises to z=26.2, and cools into a 14.8 cm ingot.
base = len(verts)
vertex((45, 0, 26.2), (.5, .5))
segments, radial = 64, 5
for r in range(1, radial + 1):
    for j in range(segments):
        a = 2 * math.pi * j / segments
        # Superellipse, softened rectangular corners.
        x = 7.4 * math.copysign(abs(math.cos(a)) ** .5, math.cos(a)) * r / radial
        y = 3.8 * math.copysign(abs(math.sin(a)) ** .5, math.sin(a)) * r / radial
        vertex((45 + x, y, 26.2), (.5 + x / 14.8, .5 + y / 7.6))
for j in range(segments):
    face((base, base + 1 + j, base + 1 + (j + 1) % segments), 1)
for r in range(radial - 1):
    for j in range(segments):
        a = base + 1 + r * segments + j
        b = base + 1 + r * segments + (j + 1) % segments
        face((a, a + segments, b + segments, b), 1)

mesh = bpy.data.meshes.new('FurnaceCastingSurface')
mesh.from_pydata(verts, [], faces)
mesh.update()
obj = bpy.data.objects.new('SM_FurnaceCastingSurface', mesh)
bpy.context.collection.objects.link(obj)
for name in ('CastingStream', 'CastingPool'):
    mesh.materials.append(bpy.data.materials.new(name))
uv = mesh.uv_layers.new(name='FlowUV')
for poly, slot in zip(mesh.polygons, slots):
    poly.material_index = slot
    poly.use_smooth = True
    for loop in poly.loop_indices:
        uv.data[loop].uv = texcoords[mesh.loops[loop].vertex_index]
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
tri = obj.modifiers.new('ExportTriangles', 'TRIANGULATE')
bpy.ops.object.modifier_apply(modifier=tri.name)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'FurnaceCasting.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT / 'SM_FurnaceCastingSurface.fbx'),
    use_selection=True, object_types={'MESH'}, apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_ALL', axis_forward='-Y', axis_up='Z',
    use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=True,
    add_leaf_bones=False, bake_anim=False)
(OUT / 'geometry.json').write_text(json.dumps({
    'mesh': obj.name, 'triangles': len(mesh.polygons), 'vertices': len(mesh.vertices),
    'space': 'SM_BlastFurnace local cm; identity attachment to Body',
    'mouth': [17.5, 0, 63.5], 'exit': [24.7, 0, 63.5], 'landing': [45, 0, 26.2],
    'travel_seconds': total_time, 'flight_seconds': flight, 'vx_cm_s': vx,
    'mould_surface_cm': [14.8, 7.6], 'mould_floor_z': 21.8,
    'materials': ['CastingStream', 'CastingPool'],
    'provenance': 'Original analytic geometry; no external assets',
}, indent=2), encoding='utf8')
print('FURNACE_CASTING_MESH_EXPORTED', OUT, flush=True)
