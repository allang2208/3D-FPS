"""Author original visual-only DW715 game meshes; no physical engineering output.

The existing game mesh supplies the coordinate frame and visible contact outline.
Only FBX/Blender render assets are produced, with no collision or fabrication data.
"""
import bpy
import bmesh
import json
import math
from pathlib import Path
from mathutils import Vector, Matrix
import numpy as np

OUT = Path(__file__).parent
EXPORTS = OUT / 'Exports'
EXPORTS.mkdir(exist_ok=True)
INPUT = json.loads((OUT / 'source_frame.json').read_text(encoding='utf-8'))
DONOR = OUT.parent / 'DanWesson715GripBrake20260927/DW715_GripBrake_Editable.blend'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
with bpy.data.libraries.load(str(DONOR), link=False) as (src, dst):
    dst.materials = ['DW715_Steel', 'DW715_DarkSteel']
STEEL, DARK = dst.materials
PARTS = {}
REPORT = {'host_asset': INPUT['host_asset'], 'source_snapshot': INPUT['source_snapshot'],
          'coordinate_frame': INPUT['frame'], 'ue_mount_matrix': INPUT['ue_mount_matrix'],
          'material_donor': str(DONOR), 'parts': {}, 'game_tested': False,
          'scope': 'Compact compensator only; accepted target weight belongs to MuzzleWeightFitV2_20260927'}


def select(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.hide_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def create_mesh(name, vertices, faces, material=STEEL):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(ob)
    mesh.materials.append(material)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    return ob


def triangulate(ob):
    select(ob)
    mod = ob.modifiers.new('Author triangulation', 'TRIANGULATE')
    mod.keep_custom_normals = True
    bpy.ops.object.modifier_apply(modifier=mod.name)


def bevel(ob, amount, segments=4):
    select(ob)
    mod = ob.modifiers.new('Rounded exterior edges', 'BEVEL')
    mod.width = amount
    mod.segments = segments
    mod.limit_method = 'ANGLE'
    mod.angle_limit = math.radians(24)
    mod.use_clamp_overlap = True
    mod.harden_normals = True
    bpy.ops.object.modifier_apply(modifier=mod.name)


def subtract(ob, cutter, name):
    # Loft rings are triangulated before booleans so non-planar side quads
    # cannot collapse a whole shell during exact boolean evaluation.
    triangulate(cutter)
    select(ob)
    mod = ob.modifiers.new(name, 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    if not len(ob.data.polygons):
        raise RuntimeError('Boolean produced no authorable geometry: ' + name)


def lathe(name, profile, segments=80):
    verts = [(x, math.cos(i * 2 * math.pi / segments) * r,
              math.sin(i * 2 * math.pi / segments) * r)
             for x, r in profile for i in range(segments)]
    faces = []
    for row in range(len(profile)):
        nxt = (row + 1) % len(profile)
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((row*segments+i, row*segments+j, nxt*segments+j, nxt*segments+i))
    return create_mesh(name, verts, faces)


def rounded_box(name, location, dimensions, edge):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    ob = bpy.context.object
    ob.name = name
    ob.dimensions = dimensions
    ob.data.materials.append(STEEL)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel(ob, edge, 5)
    return ob


def physical_uv(ob):
    uv = ob.data.uv_layers.new(name='Physical10cm')
    for p in ob.data.polygons:
        axis = max(range(3), key=lambda a: abs(p.normal[a]))
        axes = (0, 2) if axis == 1 else (1, 2) if axis == 0 else (0, 1)
        for li in p.loop_indices:
            co = ob.data.vertices[ob.data.loops[li].vertex_index].co
            uv.data[li].uv = (co[axes[0]] / .1, co[axes[1]] / .1)


def finish(ob):
    ob.data.materials.append(DARK)
    ob.data.update()
    for p in ob.data.polygons:
        p.use_smooth = True
        # Darken only the shallow, visible recesses, leaving the main exterior
        # in the same steel family as the existing DW715 accessory material.
        if math.hypot(p.center.y, p.center.z) < .0049:
            p.material_index = 1
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for e in bm.edges:
        if e.is_manifold:
            e.smooth = e.calc_face_angle(0) < math.radians(34)
    bm.to_mesh(ob.data)
    bm.free()
    physical_uv(ob)
    select(ob)
    mod = ob.modifiers.new('Broad-surface normals', 'WEIGHTED_NORMAL')
    mod.keep_sharp = True
    mod.weight = 45
    bpy.ops.object.modifier_apply(modifier=mod.name)
    triangulate(ob)
    ob['game_part'] = True
    ob['mount_reference'] = 'WPN_SOCKET_Muzzle'
    ob['forward_axis'] = '+X'
    ob['usage'] = 'UE static render mesh only; no collision'


compact = lathe('dw715_compact_compensator', [
    (-.0005, .0058), (.0002, .00655), (.0025, .00655),
    (.0035, .0070), (.0050, .0083), (.0060, .00865),
    (.0169, .00865), (.0183, .00825), (.0192, .0075),
    (.0195, .0069), (.0195, .0048), (.0187, .00465), (-.0005, .00465)])
triangulate(compact)
window = rounded_box('Compact visible side opening', (.0113, 0, 0), (.0073, .029, .0055), .00105)
subtract(compact, window, 'Exterior opening')
bevel(compact, .00024, 4)
finish(compact)
PARTS[compact.name] = compact


# The accepted target weight is authored by DanWesson715MuzzleWeightFitV2_20260927/author.py.
# This legacy batch now owns only the compact compensator.

# Save editable standalone source files before making any distant LOD copies.
for key, ob in PARTS.items():
    collection = bpy.data.collections.new(key)
    scene.collection.children.link(collection)
    for c in list(ob.users_collection): c.objects.unlink(ob)
    collection.objects.link(ob)
    ob['part_id'] = key
    for other in PARTS.values():
        other.hide_set(other != ob)
        other.hide_render = other != ob
    select(ob)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / (key + '_Editable.blend')))

lod_collection = bpy.data.collections.new('ExportLODs')
scene.collection.children.link(lod_collection)
for key, ob in PARTS.items():
    for other in PARTS.values(): other.hide_set(False)
    group = bpy.data.objects.new('SM_' + key, None)
    lod_collection.objects.link(group)
    group['fbx_type'] = 'LodGroup'
    levels = []
    for level, ratio in [(0, 1), (1, .5), (2, .23)]:
        part = ob.copy()
        part.data = ob.data.copy()
        part.name = 'SM_' + key + '_LOD' + str(level)
        part.hide_render = False
        lod_collection.objects.link(part)
        part.parent = group
        if level:
            select(part)
            dec = part.modifiers.new('Distant surface reduction', 'DECIMATE')
            dec.ratio = ratio
            dec.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier=dec.name)
            weighted = part.modifiers.new('LOD surface normals', 'WEIGHTED_NORMAL')
            weighted.keep_sharp = True
            bpy.ops.object.modifier_apply(modifier=weighted.name)
        levels.append(part)
    select(group)
    for part in levels: part.select_set(True)
    fbx = EXPORTS / ('SM_' + key + '.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True,
        object_types={'MESH', 'EMPTY'}, axis_forward='-Y', axis_up='Z',
        bake_anim=False, mesh_smooth_type='FACE', use_tspace=False, use_custom_props=True)
    REPORT['parts'][key] = {'fbx': str(fbx), 'lod_triangles': [len(p.data.polygons) for p in levels],
        'materials': [m.name for m in ob.data.materials], 'mount': 'WPN_SOCKET_Muzzle',
        'tip_cm': [max(v.co.x for v in ob.data.vertices)*100, 0, 0],
        'mesh': '/Game/Weapons/DanWesson715/MuzzleModels20260927/Meshes/SM_' + key,
        'source': str(OUT / (key + '_Editable.blend'))}
    for part in levels: part.hide_set(True)
    group.hide_set(True)

# A non-rendering host reference is retained in the editable assembly scene.
raw = json.loads(Path(INPUT['source_snapshot']).read_text(encoding='utf-8'))
matrix = np.array(INPUT['ue_mount_matrix'])
positions = (np.array(raw['positions']) - matrix[:3, 3]) @ matrix[:3, :3]
positions *= np.array([.01, -.01, .01])
keep = [i for i, m in enumerate(raw['materials'])
        if raw['slots'][m] in ('M_DW715_Hero_Steel', 'M_DW715_Hero_Frame',
                               'M_DW715_Hero_Cylinder', 'M_DW715_Hero_Grip', 'M_DW715_Hero_Sights')]
used = sorted({v for i in keep for v in raw['triangles'][i]})
remap = {v: i for i, v in enumerate(used)}
host_ob = create_mesh('DW715_HOST_REFERENCE', positions[used].tolist(),
    [tuple(remap[v] for v in reversed(raw['triangles'][i])) for i in keep])
host_ob.display_type = 'WIRE'
host_ob.hide_render = True
host_ob.hide_select = True
host_ob['source_asset'] = INPUT['host_asset']
host_ob['reference_only'] = True
host_collection = bpy.data.collections.new('HostReference_NOT_EXPORTED')
scene.collection.children.link(host_collection)
for c in list(host_ob.users_collection): c.objects.unlink(host_ob)
host_collection.objects.link(host_ob)
for key, ob in PARTS.items():
    ob.hide_set(key != 'dw715_compact_compensator')
    ob.hide_render = key != 'dw715_compact_compensator'
lod_collection.hide_render = True
select(compact)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'DW715_MuzzlePair_Assembly_Editable.blend'))
(OUT / 'authoring.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')
print('DW715_MUZZLE_MODELS_AUTHORED ' + json.dumps({k: v['lod_triangles'] for k, v in REPORT['parts'].items()}), flush=True)
