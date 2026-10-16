"""Author the reference-led exterior game mesh; no engine edits or rendering.

Coordinates are Blender metres, +X forward, +Z up. The origin is the
attachment's rear visual seating plane, on the circular opening's axis.
The visible front opening terminates in a shallow dark cosmetic recess.
"""
import bpy
import bmesh
import json
import math
import shutil
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parent
EXPORTS = ROOT / 'Exports'
REFERENCE = ROOT / 'Reference'
EXPORTS.mkdir(exist_ok=True)
REFERENCE.mkdir(exist_ok=True)
SOURCE_IMAGE = Path(r'C:/Users/allan/AppData/Local/Temp/codex-clipboard-e8879289-f109-471e-a48c-c070740593cc.png')


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene.view_settings.view_transform = 'AgX'

PARAMS = {
    'body_start': .024,
    'body_end': .278,
    'half_width': .029,
    'half_height': .041,
    'vertical_center': -.0225,
    'top_corner_radius': .012,
    'bottom_corner_radius': .008,
    'front_recess_radius': .0107,
    'front_recess_depth': .006,
    'body_seams': [.041, .252, .268],
    'seam_depth': .00013,
    'seam_half_width': .00028,
}

MATERIAL_RECIPES = [
    ('Suppressor_GraphiteShell', (.034, .037, .043, 1), .35, 1.0),
    ('Suppressor_EndPlate', (.029, .032, .037, 1), .32, 1.0),
    ('Suppressor_SeamAndRecess', (.006, .007, .009, 1), .64, .15),
    ('Suppressor_RearSeat', (.034, .035, .037, 1), .42, 1.0),
    ('Suppressor_RimMetal', (.070, .077, .088, 1), .29, 1.0),
]
MATERIALS = []
for name, color, roughness, metallic in MATERIAL_RECIPES:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = color
    material.roughness = roughness
    material.metallic = metallic
    nodes=material.node_tree.nodes;nodes.clear()
    shader=nodes.new('ShaderNodeBsdfPrincipled');output=nodes.new('ShaderNodeOutputMaterial')
    material.node_tree.links.new(shader.outputs['BSDF'],output.inputs['Surface'])
    shader.inputs['Base Color'].default_value = color
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    # The shape and bevels supply the normal: no placeholder normal textures.
    MATERIALS.append(material)


def collection(name):
    result = bpy.data.collections.new(name)
    scene.collection.children.link(result)
    return result


def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]


def profile_distance(y, z, inset=0.0):
    z -= PARAMS['vertical_center']
    radius = (PARAMS['top_corner_radius'] if z >= 0 else PARAMS['bottom_corner_radius']) - inset
    radius = max(radius, .0005)
    qy = abs(y) - (PARAMS['half_width'] - inset - radius)
    qz = abs(z) - (PARAMS['half_height'] - inset - radius)
    return math.hypot(max(qy, 0), max(qz, 0)) + min(max(qy, qz), 0) - radius


def perimeter(count, inset=0.0):
    """Sample a continuous rounded rectangular outline around the visual axis."""
    result = []
    for i in range(count):
        angle = 2 * math.pi * i / count
        cy, sz = math.cos(angle), math.sin(angle)
        lo, hi = 0.0, .1
        for _ in range(35):
            radius = (lo + hi) / 2
            if profile_distance(radius * cy, radius * sz, inset) > 0:
                hi = radius
            else:
                lo = radius
        radius = (lo + hi) / 2
        result.append((radius * cy, radius * sz))
    return result


class Loft:
    def __init__(self, count):
        self.count = count
        self.vertices, self.faces, self.materials = [], [], []

    def ring(self, x, shape):
        start = len(self.vertices)
        self.vertices.extend((x, y, z) for y, z in shape)
        return list(range(start, start + len(shape)))

    def circle(self, x, radius, y=0.0, z=0.0):
        return self.ring(x, [(y + radius * math.cos(i * math.tau / self.count),
                             z + radius * math.sin(i * math.tau / self.count))
                            for i in range(self.count)])

    def bridge(self, a, b, material=0):
        for i in range(self.count):
            j = (i + 1) % self.count
            self.faces.append((a[i], a[j], b[j], b[i]))
            self.materials.append(material)

    def cap(self, ring, material=0):
        self.faces.append(tuple(reversed(ring)))
        self.materials.append(material)

    def object(self, name, target):
        mesh = bpy.data.meshes.new(name + '_Mesh')
        mesh.from_pydata(self.vertices, [], self.faces)
        for material in MATERIALS:
            mesh.materials.append(material)
        for polygon, material in zip(mesh.polygons, self.materials):
            polygon.material_index = material
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        for polygon in mesh.polygons:
            polygon.use_smooth = True
        mesh.set_sharp_from_angle(angle=math.radians(42))
        obj = bpy.data.objects.new(name, mesh)
        target.objects.link(obj)
        select([obj])
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.018)
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh.uv_layers.active.name = 'UV0'
        normals = obj.modifiers.new('Planar_Surface_Normals', 'WEIGHTED_NORMAL')
        normals.keep_sharp = True
        normals.weight = 50
        return obj


def make_shell(count, target):
    loft = Loft(count)
    # Closely spaced front and rear rings form the edge highlights in geometry.
    rows = [(PARAMS['body_start'], .0010, 0),
            (PARAMS['body_start'] + .0003, .00045, 0),
            (PARAMS['body_start'] + .0010, 0.0, 0)]
    for center in PARAMS['body_seams']:
        half = PARAMS['seam_half_width']
        depth = PARAMS['seam_depth']
        rows.extend([(center - half, 0, 0),
                     (center - half * .4, depth, 0),
                     (center + half * .4, depth, 2),
                     (center + half, 0, 0)])
    front = PARAMS['body_end']
    rows.extend([(front - .0011, 0, 1),
                 (front - .00055, .00016, 1),
                 (front - .00015, .00050, 1),
                 (front, .0011, 1)])
    rings = []
    for x, inset, material in rows:
        ring = loft.ring(x, perimeter(count, inset))
        if rings:
            loft.bridge(rings[-1], ring, material)
        rings.append(ring)
    loft.cap(rings[0], 3)
    # Front plate, highlight rim, then a shallow visual pocket with a dark cap.
    opening = loft.circle(front, PARAMS['front_recess_radius'] + .0006)
    loft.bridge(rings[-1], opening, 1)
    rim = loft.circle(front - .00065, PARAMS['front_recess_radius'])
    loft.bridge(opening, rim, 4)
    pocket = loft.circle(front - PARAMS['front_recess_depth'], PARAMS['front_recess_radius'])
    loft.bridge(rim, pocket, 2)
    loft.cap(pocket, 2)
    obj = loft.object('Suppressor_BoxShell', target)
    obj['part_role'] = 'shared_exterior_body'
    return obj


def make_rear_seat(count, target):
    loft = Loft(count)
    previous = None
    # A closed visual seat; adapters remain independent from the shared body.
    for x, radius, material in [(-.0020, .0113, 3), (-.0012, .0120, 3),
                               (.0030, .0120, 3), (.0037, .0131, 3),
                               (.0080, .0131, 3), (.0083, .0129, 2),
                               (.0088, .0129, 2), (.0091, .0131, 3),
                               (.018, .0148, 3), (.026, .0148, 3)]:
        ring = loft.circle(x, radius)
        if previous is None:
            loft.cap(ring, 3)
        else:
            loft.bridge(previous, ring, material)
        previous = ring
    loft.cap(previous, 3)
    obj = loft.object('Suppressor_RearVisualSeat', target)
    obj['part_role'] = 'replaceable_game_mount'
    return obj


def make_front_fastener(count, target, y):
    loft = Loft(count)
    z = -.050
    x = PARAMS['body_end'] + .00002
    rear = loft.circle(x, .0017, y, z)
    edge = loft.circle(x + .00016, .0015, y, z)
    inner = loft.circle(x + .00016, .00055, y, z)
    recess = loft.circle(x + .00003, .00055, y, z)
    loft.cap(rear, 1)
    loft.bridge(rear, edge, 1)
    loft.bridge(edge, inner, 1)
    loft.bridge(inner, recess, 2)
    loft.cap(recess, 2)
    return loft.object('Suppressor_FrontPin_L' if y < 0 else 'Suppressor_FrontPin_R', target)


def author_parts(count, target):
    return [make_shell(count, target), make_rear_seat(count, target),
            make_front_fastener(max(12, count // 3), target, -.015),
            make_front_fastener(max(12, count // 3), target, .015)]


def export_mesh(parts, level):
    # Keep editable source pieces separate. Collapse evaluated copies for export.
    select(parts)
    bpy.ops.object.duplicate()
    copies = list(bpy.context.selected_objects)
    for obj in copies:
        select([obj])
        bpy.ops.object.convert(target='MESH')
    select(copies)
    bpy.ops.object.join()
    combined = bpy.context.object
    combined.name = 'SM_ShotgunSuppressor01_' + level
    triangle_modifier = combined.modifiers.new('Export_Triangles', 'TRIANGULATE')
    triangle_modifier.quad_method = 'FIXED'
    bpy.ops.object.modifier_apply(modifier=triangle_modifier.name)
    combined.data.calc_loop_triangles()
    stats = {'vertices': len(combined.data.vertices),
             'triangles': len(combined.data.loop_triangles)}
    fbx = EXPORTS / (combined.name + '.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True,
                            object_types={'MESH'}, axis_forward='-Y', axis_up='Z',
                            bake_anim=False, add_leaf_bones=False,
                            mesh_smooth_type='FACE', use_tspace=True)
    glb = EXPORTS / (combined.name + '.glb')
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB',
                             use_selection=True, export_materials='EXPORT',
                             export_extras=True, export_animations=False,
                             export_tangents=True)
    stats.update({'fbx': str(fbx), 'glb': str(glb)})
    bpy.data.objects.remove(combined, do_unlink=True)
    return stats



def side_details(target):
    result=[]
    # Shallow external styling ribs and identification panel; no internal assembly.
    for side in (-1,1):
        for index,z in enumerate((-.015,-.024,-.033)):
            bpy.ops.mesh.primitive_cube_add(size=1,location=(.145,side*.0288,z))
            obj=bpy.context.object;obj.name=f'Suppressor_SideRib_{side}_{index}'
            obj.dimensions=(.172,.0014,.0020)
            bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
            obj.data.materials.append(MATERIALS[1])
            bevel=obj.modifiers.new('Soft machined rib edges','BEVEL');bevel.width=.00065;bevel.segments=3
            obj.modifiers.new('Planar rib normals','WEIGHTED_NORMAL')
            result.append(obj)
    return result

model_collection=collection('01_Editable_Exterior')
parts=author_parts(128,model_collection)+side_details(model_collection)
for obj in parts:
    obj['asset_family']='Shared_Shotgun_Muzzle'
    obj['variant']='shotgun_suppressor'
lods={'LOD0':export_mesh(parts,'LOD0')}
for level,count in [('LOD1',64),('LOD2',32)]:
    c=collection('Source_'+level)
    simple=author_parts(count,c)+side_details(c)
    lods[level]=export_mesh(simple,level)
    for obj in simple:bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.collections.remove(c)
helpers=collection('02_Assembly_Markers')
for name,x in [('Mount_Origin',0),('Visual_Front',.278)]:
    marker=bpy.data.objects.new(name,None);marker.location=(x,0,0)
    marker.empty_display_type='ARROWS';marker.empty_display_size=.02
    helpers.objects.link(marker);marker.hide_render=True
helpers.hide_viewport=True
select(parts)
source_file=ROOT/'ShotgunSuppressor01_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(source_file))
report={'status':'model_and_exports_saved','editable_source':str(source_file),
    'parameters_in_blender_metres':PARAMS,'lods':lods,
    'materials':[{'name':n,'base_color_linear':c,'roughness':r,'metallic':m} for n,c,r,m in MATERIAL_RECIPES],
    'tip_cm':27.8,'source_reference':'Original cosmetic shotgun suppressor exterior, shared SUPER90 visual seat',
    'normal_texture':None,'engine_imported':False,'runtime_tested':False}
(ROOT/'authoring_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SUPPRESSOR_MODEL_SAVED',json.dumps(lods),flush=True)
