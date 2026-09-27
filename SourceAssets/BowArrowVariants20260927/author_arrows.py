"""Three native bow ammunition meshes; retain the accepted shaft/nock/fletching.
Blender 5.1 background authoring. Renders here are production ammo icons, not QA.
"""
import bpy, bmesh, math, json, shutil, sys
from pathlib import Path
from mathutils import Vector

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
SOURCE = P.parent / 'DarkBow20260925/ArmsV2/WoodArrow_Editable.blend'
EXPORT = P / 'Export'
ICONS = ROOT / 'Content/ColdSteelData/Icons/ArrowVariants20260927'
EXPORT.mkdir(exist_ok=True)
ICONS.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1

# Linear albedo values also consumed by the Unreal material authoring script.
SPECS = {
    'ArrowSteelForged': ([.42, .44, .46], .9, .32),
    'ArrowSteelEdge': ([.55, .57, .59], .95, .23),
    'ArrowBindingSteel': ([.09, .075, .046], 0., .73),
    'ArrowBindingPoison': ([.035, .09, .026], 0., .77),
    'ArrowBindingSerrated': ([.16, .028, .018], 0., .75),
    'ArrowVenomCoat': ([.028, .11, .009], 0., .27),
}
materials = {}
for name, (color, metal, rough) in SPECS.items():
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Metallic'].default_value = metal
    shader.inputs['Roughness'].default_value = rough
    materials[name] = mat

with bpy.data.libraries.load(str(SOURCE), link=False) as (available, selected):
    selected.objects = ['SM_Bow_WoodArrow']
wood = selected.objects[0]
scene.collection.objects.link(wood)
wood.hide_render = True
# Author-source shaft color predates the live ash finish; use its current stain
# for the icon scene. UE meshes reuse the actual existing scan-based material.
for mat in wood.data.materials:
    if mat and mat.name.startswith('ArrowWood'):
        shader = mat.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (.9, .68, .38, 1)

def mesh(name, vertices, faces, material):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    data.materials.append(materials[material])
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    return obj

def bevel(obj, width=.00018):
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new('Fine ground edges', 'BEVEL')
    mod.width = width
    mod.segments = 2
    mod.limit_method = 'ANGLE'
    mod.angle_limit = math.radians(28)
    mod.use_clamp_overlap = True
    bpy.ops.object.modifier_apply(modifier=mod.name)

def cylinder(name, x, radius, length, material, y=0., z=0., sides=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides, radius=radius, depth=length,
        location=(x, y, z), rotation=(0, math.pi / 2, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(materials[material])
    for poly in obj.data.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bevel(obj, .00012)
    return obj

def diamond_head(name, rings, material):
    vertices = []
    for x, width, ridge in rings:
        vertices.extend([(x, -width, 0), (x, 0, ridge), (x, width, 0), (x, 0, -ridge)])
    faces = [(3, 2, 1, 0)]
    for r in range(len(rings) - 1):
        for i in range(4):
            faces.append((r * 4 + i, r * 4 + (i + 1) % 4,
                (r + 1) * 4 + (i + 1) % 4, (r + 1) * 4 + i))
    start = (len(rings) - 1) * 4
    faces.append(tuple(start + i for i in range(4)))
    obj = mesh(name, vertices, faces, material)
    bevel(obj, .00009)
    return obj

def body_without_head():
    obj = wood.copy()
    obj.data = wood.data.copy()
    scene.collection.objects.link(obj)
    obj.hide_render = False
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    indices = [i for i, m in enumerate(obj.data.materials) if m and 'Steel' in m.name]
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in indices], context='FACES')
    unused = [v for v in bm.verts if not v.link_faces]
    if unused:
        bmesh.ops.delete(bm, geom=unused, context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()
    return obj

def binding(material):
    # Individual waxed thread turns around the retained shaft, below the socket.
    result = []
    for i in range(14):
        bpy.ops.mesh.primitive_torus_add(major_segments=24, minor_segments=6,
            location=(.297 + i * .00068, 0, 0), rotation=(0, math.pi / 2, 0),
            major_radius=.00313, minor_radius=.00035)
        obj = bpy.context.object
        obj.name = 'WaxedBinding'
        obj.data.materials.append(materials[material])
        for f in obj.data.polygons:
            f.use_smooth = True
        result.append(obj)
    return result

arrows = {}
for variant, bind in [('ArmorPiercing', 'Steel'), ('Poison', 'Poison'), ('Serrated', 'Serrated')]:
    body = body_without_head()
    objects = [body, cylinder('TaperSocket', .317, .00365, .025, 'ArrowSteelForged')]
    objects += binding('ArrowBinding' + bind)
    objects.append(cylinder('SocketLip', .305, .0039, .0014, 'ArrowSteelEdge'))
    if variant == 'ArmorPiercing':
        # Compact bodkin: four pronounced ridges, a continuous tapered tip.
        objects.append(diamond_head('FourRidgeBodkin', [(.326,.0038,.0038),
            (.342,.0043,.0043),(.375,.001,.001),(.38,.00005,.00005)], 'ArrowSteelEdge'))
    elif variant == 'Poison':
        head = diamond_head('VenomLeaf', [(.326,.0033,.0023),(.334,.010,.0028),
            (.346,.0125,.003),(.360,.0087,.0024),(.38,.00005,.00005)], 'ArrowSteelForged')
        # Shallow rounded channels in the two faces; recessed green coating is
        # separate material and follows the cut instead of coloring all the metal.
        for y in (-.004, .004):
            for z in (-.0028, .0028):
                bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=(.347,y,z))
                cutter = bpy.context.object
                cutter.scale = (.012, .00115, .0015)
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                bpy.context.view_layer.objects.active = head
                mod = head.modifiers.new('RecessedVenomChannel', 'BOOLEAN')
                mod.operation = 'DIFFERENCE'
                mod.solver = 'EXACT'
                mod.object = cutter
                bpy.ops.object.modifier_apply(modifier=mod.name)
                bpy.data.objects.remove(cutter, do_unlink=True)
                bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10,
                    location=(.347,y,math.copysign(.00148,z)))
                coat = bpy.context.object
                coat.name = 'RecessedVenomCoating'
                coat.scale = (.0105,.00065,.00026)
                coat.data.materials.append(materials['ArrowVenomCoat'])
                for face in coat.data.polygons:
                    face.use_smooth = True
                objects.append(coat)
        objects.append(head)
    else:
        # A continuous broadhead with backwards-facing saw teeth, solid sidewalls.
        half = [(.326,.0033),(.329,.008),(.329,.017),(.337,.012),
                (.338,.018),(.346,.012),(.347,.0165),(.354,.010),
                (.355,.013),(.362,.0078),(.364,.009),(.38,.00005)]
        outline = half + [(x,-y) for x,y in reversed(half)]
        vertices = [(x,y,z) for z in (-.0014,.0014) for x,y in outline]
        n = len(outline)
        faces = [tuple(reversed(range(n))), tuple(n+i for i in range(n))]
        faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        head = mesh('ReverseSerrationBroadhead', vertices, faces, 'ArrowSteelEdge')
        bevel(head, .00035)
        objects.append(head)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    arrow = bpy.context.object
    arrow.name = 'SM_Arrow_' + variant
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # Export all new meshes in the accepted arrow's meter-based FBX convention.
    bpy.ops.export_scene.fbx(filepath=str(EXPORT / (arrow.name + '.fbx')),
        use_selection=True, object_types={'MESH'}, axis_forward='-Y', axis_up='Z',
        bake_anim=False, mesh_smooth_type='FACE')
    arrow.hide_render = True
    arrows[variant] = arrow

(P/'materials.json').write_text(json.dumps(SPECS, indent=2), encoding='utf-8')
manifest = dict(source=str(SOURCE), length_cm=76, shaft_radius_cm=.3,
    nock_cm=[-38,0,0], tip_cm=[38,0,0], forward='+X', units='meters',
    variants={v:dict(mesh=o.name,vertices=len(o.data.vertices),polygons=len(o.data.polygons))
        for v,o in arrows.items()}, runtime_tested=False)
(P/'authoring.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_ArrowVariants.blend'))

# Macro product icons: show the actual arrowhead and forward shaft at the same
# scale. Their discriminating heads fit inside the R wheel's centered 0.82 UV.
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.view_settings.exposure = -0.7
scene.world = bpy.data.worlds.new('Neutral Product World')
scene.world.use_nodes = True
scene.world.node_tree.nodes.get('Background').inputs[0].default_value = (.32,.32,.32,1)
scene.world.node_tree.nodes.get('Background').inputs[1].default_value = .6

def point(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

target = Vector((.324,0,0))
cam_data = bpy.data.cameras.new('Ammo Product Camera')
cam = bpy.data.objects.new('Ammo Product Camera', cam_data)
scene.collection.objects.link(cam)
cam.location = target + Vector((0,-.15,.36))
point(cam,target)
cam.rotation_euler.rotate_axis('Z',math.radians(-35))
cam.data.type = 'ORTHO'
cam.data.ortho_scale = .145
scene.camera = cam
for name,location,power,size in [('Key',(.31,-.13,.3),9,.22),
    ('Rim',(.39,.12,.19),7,.12),('Fill',(.25,.06,.25),4,.20)]:
    data = bpy.data.lights.new(name,'AREA')
    data.energy = power
    data.shape = 'DISK'
    data.size = size
    light = bpy.data.objects.new(name,data)
    scene.collection.objects.link(light)
    light.location = location
    point(light,target)
icons = [('arrow_wood',wood),('arrow_broadhead',arrows['ArmorPiercing']),
         ('arrow_poison',arrows['Poison']),('arrow_serrated',arrows['Serrated'])]
for id_,original in icons:
    # Actual head + forward shaft, capped below crop. No extraneous background
    # furniture or baked text, so the same icon works on pouch and wheel.
    icon = original.copy()
    icon.data = original.data.copy()
    scene.collection.objects.link(icon)
    bm = bmesh.new()
    bm.from_mesh(icon.data)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
        plane_co=(.27,0,0), plane_no=(1,0,0), clear_inner=True, dist=0.000001)
    boundary = [e for e in bm.edges if e.is_boundary]
    if boundary:
        bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
    bm.to_mesh(icon.data)
    bm.free()
    icon.hide_render = False
    scene.render.filepath = str(ICONS / (id_ + '.png'))
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(icon, do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_ArrowIcons.blend'))
print('BOW_ARROWS_AUTHORED_AND_ICONS_SAVED', flush=True)
