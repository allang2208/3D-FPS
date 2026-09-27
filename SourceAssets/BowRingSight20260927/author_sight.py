"""V17 fine wooden ring sight, authored in Blender; coordinates in UE cm.

Original geometry. The fitted seat and wood PBR derive from the retained bow.
No rendering or runtime testing. Editable construction parts remain in Blend.
"""
import bpy
import bmesh
import json
import math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

P = Path(__file__).parent
OUT = P / 'Export'
OUT.mkdir(exist_ok=True)
BASE = P.parent / 'DarkBow20260925/WoodLongbow20260925'
PIN = Vector((-3.5, -10.1, 16.5))
RING_RADIUS = 1.60
SEAT_Z = (14.65, 18.35)

bpy.ops.wm.open_mainfile(filepath=str(BASE / 'WoodLongbow_Editable.blend'))
src = bpy.data.objects['SM_DarkBow_WoodLongbow']
scale = 100 if max(src.dimensions) < 5 else 1
verts = [src.matrix_world @ v.co * scale for v in src.data.vertices]
verts = [Vector((p.x, -p.y, p.z)) for p in verts]
adj = [[] for _ in verts]
for e in src.data.edges:
    a, b = e.vertices
    adj[a].append(b)
    adj[b].append(a)
unseen = set(range(len(verts)))
islands = []
while unseen:
    first = unseen.pop()
    stack, group = [first], [first]
    while stack:
        for i in adj[stack.pop()]:
            if i in unseen:
                unseen.remove(i)
                stack.append(i)
                group.append(i)
    islands.append(group)
body = set(max(islands, key=lambda g: max(verts[i].z for i in g)-min(verts[i].z for i in g)))
src.data.calc_loop_triangles()
tri = [t for t in src.data.loop_triangles if t.vertices[0] in body]
tri_indices = [list(t.vertices) for t in tri]
tree = BVHTree.FromPolygons(verts, tri_indices, all_triangles=True)
tuv = [[Vector((*src.data.uv_layers.active.data[l].uv, 0)) for l in t.loops] for t in tri]

def surface(x, z):
    p, _, idx, _ = tree.ray_cast(Vector((x, -12, z)), Vector((0, 1, 0)), 24)
    if p is None:
        raise RuntimeError('Mount surface unavailable at ' + str((x, z)))
    uv = barycentric_transform(p, *(verts[i] for i in tri_indices[idx]), *tuv[idx])
    return p, (uv.x, uv.y)

def seat_thickness(x, z):
    t = (z-SEAT_Z[0])/(SEAT_Z[1]-SEAT_Z[0])
    if not 0 <= t <= 1:
        return 0.
    half = .12 + .68 * math.sin(math.pi*t)**.55
    s = (x+.65)/half
    if abs(s) > 1:
        return 0.
    return .025 + .24 * math.sin(math.pi*t)**.75 * math.cos(s*math.pi/2)**.9

samples = []
for iz in range(49):
    t = iz/48
    z = SEAT_Z[0] + (SEAT_Z[1]-SEAT_Z[0])*t
    half = .12 + .68*math.sin(math.pi*t)**.55
    row = []
    for ix in range(17):
        x = -.65 + (ix/16*2-1)*half
        p, uv = surface(x, z)
        row.append((p, uv, seat_thickness(x, z)))
    samples.append(row)
root, _ = surface(-.65, PIN.z)

# Two tiny linen collars retain the contoured foot without a bulky bracket.
collars = []
for z in (15.05, 17.95):
    path = []
    for i in range(145):
        t = i/144
        angle = math.tau*1.85*t
        zz = z + (t-.5)*.18
        radial = Vector((math.cos(angle), math.sin(angle), 0))
        center = Vector((-.7, 0, zz))
        hit, _, _, _ = tree.ray_cast(center+radial*12, -radial, 24)
        if hit is None:
            raise RuntimeError('Collar surface unavailable')
        if hit.y < 0:
            hit.y -= seat_thickness(hit.x, hit.z) * min(1., -radial.y*1.5)
        path.append(hit + radial*.036)
    collars.append(path)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = .01
materials = []
for name, color, rough in [('FineBowWood', (.19, .058, .023, 1), .52),
                            ('FineWaxedLinen', (.10, .062, .033, 1), .85),
                            ('EndgrainInlay', (.34, .205, .095, 1), .57)]:
    m = bpy.data.materials.new(name)
    m.diffuse_color = color
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = rough
    materials.append(m)
wood = materials[0]
n, links = wood.node_tree.nodes, wood.node_tree.links
bsdf = n.get('Principled BSDF')
for filename, target in [('Image_0.png', 'Base Color'), ('Image_1.png', 'Roughness'), ('Image_2.png', 'Normal')]:
    tex = n.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(str(BASE/'Textures'/filename))
    if target == 'Base Color':
        links.new(tex.outputs['Color'], bsdf.inputs[target])
    else:
        tex.image.colorspace_settings.name = 'Non-Color'
        if target == 'Normal':
            normal = n.new('ShaderNodeNormalMap')
            normal.inputs['Strength'].default_value = .35
            links.new(tex.outputs['Color'], normal.inputs['Color'])
            links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
        else:
            sep = n.new('ShaderNodeSeparateColor')
            links.new(tex.outputs['Color'], sep.inputs['Color'])
            mx = n.new('ShaderNodeMath')
            mx.operation = 'MAXIMUM'
            mx.inputs[1].default_value = .50
            links.new(sep.outputs['Green'], mx.inputs[0])
            links.new(mx.outputs[0], bsdf.inputs['Roughness'])

parts = []
def mesh(name, vertices, faces, face_uvs, mat=0):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(materials[mat])
    uv = data.uv_layers.new(name='UVMap')
    for poly, coords in zip(data.polygons, face_uvs):
        poly.use_smooth = True
        for l, coord in zip(poly.loop_indices, coords):
            uv.data[l].uv = coord
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    parts.append(obj)
    return obj

def catmull(points, steps=12):
    q = [Vector(p) for p in points]
    out = []
    for i in range(len(q)-1):
        a, b, c, d = q[max(0,i-1)], q[i], q[i+1], q[min(len(q)-1,i+2)]
        for j in range(steps):
            t = j/steps
            out.append((2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)*.5)
    return out+[q[-1]]

def sweep(name, points, radius, mat=0, sides=16, closed=False, vbase=.48):
    points = [Vector(p) for p in points]
    vv, faces, uvfaces = [], [], []
    count = len(points)
    distances = [0.]
    for i in range(1, count):
        distances.append(distances[-1]+(points[i]-points[i-1]).length)
    total = distances[-1] + ((points[0]-points[-1]).length if closed else 0)
    for i, p in enumerate(points):
        prev = points[(i-1)%count] if closed else points[max(0,i-1)]
        nxt = points[(i+1)%count] if closed else points[min(count-1,i+1)]
        tangent = (nxt-prev).normalized()
        across = Vector((1,0,0))
        across = (across-tangent*across.dot(tangent)).normalized()
        if across.length < .5:
            across = tangent.cross(Vector((0,0,1))).normalized()
        side = tangent.cross(across).normalized()
        rx, ry = radius(i/(count if closed else count-1))
        for j in range(sides):
            angle = math.tau*j/sides
            vv.append(p+across*(rx*math.cos(angle))+side*(ry*math.sin(angle)))
    for i in range(count if closed else count-1):
        ni = (i+1)%count
        v0 = vbase+distances[i]/140
        v1 = vbase+(total if ni == 0 else distances[ni])/140
        for j in range(sides):
            nj = (j+1)%sides
            faces.append((i*sides+j, i*sides+nj, ni*sides+nj, ni*sides+j))
            u0, u1 = .149+.046*j/sides, .149+.046*(j+1)/sides
            uvfaces.append(((u0,v0),(u1,v0),(u1,v1),(u0,v1)))
    if not closed:
        for ring, reverse in [(0, True), (count-1, False)]:
            indices = list(range(sides))
            if reverse:
                indices.reverse()
            faces.append(tuple(ring*sides+j for j in indices))
            uvfaces.append(tuple((.172+.010*math.cos(math.tau*j/sides),vbase+.010*math.sin(math.tau*j/sides)) for j in indices))
    return mesh(name, vv, faces, uvfaces, mat)

vv, uvs, faces = [], [], []
nz, nx = len(samples), len(samples[0])
layer = nz*nx
for top in (False, True):
    for row in samples:
        for p, uv, thickness in row:
            vv.append((p.x, p.y-thickness if top else p.y+.055, p.z))
            uvs.append(uv)
for offset in (0, layer):
    for i in range(nz-1):
        for j in range(nx-1):
            a = offset+i*nx+j
            faces.append((a,a+1,a+nx+1,a+nx))
border = list(range(nx))+[i*nx+nx-1 for i in range(1,nz)]+list(range(layer-2,layer-nx-1,-1))+[i*nx for i in range(nz-2,0,-1)]
for a,b in zip(border,border[1:]+border[:1]):
    faces.append((a,b,b+layer,a+layer))
seat = mesh('01_Surface_fitted_feathered_wood_foot',vv,faces,[[uvs[i] for i in face] for face in faces])
rod_path = catmull([(-.65, root.y+.04, 16.5),(-.90,root.y-.65,16.5),
                    (-1.45,-4.2,16.5),(-2.20,-5.85,16.5),(-3.08,-7.35,16.5),
                    (-3.50,-8.50,16.5)])
def rod_radius(t):
    r = .175 + .235*max(0.,1-t/.32)**2
    return r, r
rod = sweep('02_Slender_swept_wooden_rod',rod_path,rod_radius)
ring = sweep('03_Closed_circular_wood_aperture',
             [(PIN.x,PIN.y+RING_RADIUS*math.cos(math.tau*i/96),PIN.z+RING_RADIUS*math.sin(math.tau*i/96)) for i in range(96)],
             lambda t:(.15,.12),closed=True,vbase=.53)
post = sweep('04_Centre_vertical_sight_post',
             [(PIN.x,PIN.y,PIN.z-RING_RADIUS-.07+(RING_RADIUS+.07)*i/24) for i in range(25)],
             lambda t:(.085-.025*t,.080-.040*t),vbase=.62)

# Keep pre-boolean authoring parts, independently editable in the source Blend.
construction = bpy.data.collections.new('EDITABLE_CONSTRUCTION_UE_cm')
bpy.context.scene.collection.children.link(construction)
for o in list(parts):
    copy = o.copy()
    copy.data = o.data.copy()
    construction.objects.link(copy)
    copy.name = 'SOURCE_'+o.name
    copy.hide_render = True
    copy.hide_set(True)
construction.hide_render = True

# Exact unions retain the genuinely circular ring and the exact post endpoint;
# local junction bevels replace the old global voxel smoothing.
bpy.ops.object.select_all(action='DESELECT')
seat.select_set(True)
bpy.context.view_layer.objects.active = seat
for part in (rod,ring,post):
    mod = seat.modifiers.new('Continuous wood junction', 'BOOLEAN')
    mod.operation = 'UNION'
    mod.solver = 'EXACT'
    mod.object = part
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(part, do_unlink=True)
bm = bmesh.new()
bm.from_mesh(seat.data)
bmesh.ops.dissolve_degenerate(bm,dist=.00005,edges=list(bm.edges))
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(seat.data)
bm.free()
bevel = seat.modifiers.new('Soft mortise and aperture junctions','BEVEL')
bevel.width = .035
bevel.segments = 3
bevel.limit_method = 'ANGLE'
bevel.angle_limit = math.radians(38)
bevel.use_clamp_overlap = True
bpy.ops.object.modifier_apply(modifier=bevel.name)
for p in seat.data.polygons:
    p.use_smooth = True
parts = [seat]
for index,path in enumerate(collars):
    sweep('05_Fine_linen_collar_'+str(index),path,lambda t:(.033,.033),mat=1,sides=8)
# Small flush endgrain plugs, seated in the foot rather than floating screws.
for z in (15.48,17.52):
    point,_ = surface(-.65,z)
    point.y -= seat_thickness(point.x,point.z)-.012
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.073,location=point)
    o = bpy.context.object
    o.name = '06_Flush_wooden_dowel'
    o.scale = (1,.28,1)
    o.data.materials.append(materials[2])
    for face in o.data.polygons:
        face.use_smooth = True
    parts.append(o)

bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = seat
bpy.ops.object.join()
obj = bpy.context.object
obj.name = 'SM_Bow_FineRingSight'
bpy.context.scene.cursor.location = (0,0,0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
for v in obj.data.vertices:
    v.co.y = -v.co.y
bm = bmesh.new()
bm.from_mesh(obj.data)
bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
bm.to_mesh(obj.data)
bm.free()
triangulate = obj.modifiers.new('Export triangles','TRIANGULATE')
bpy.ops.object.modifier_apply(modifier=triangulate.name)
# Match source collection to export handedness for convenient Blender editing.
for o in construction.objects:
    for v in o.data.vertices:
        v.co.y = -v.co.y
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bm.to_mesh(o.data)
    bm.free()
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_FineRingSight.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,
    object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,
    bake_anim=False,use_tspace=True,path_mode='AUTO',embed_textures=False)
(P/'authoring.json').write_text(json.dumps({
    'sight_pin_cm':list(PIN),'ring_outer_diameter_cm':3.44,'ring_inner_diameter_cm':2.96,
    'rod_shaft_diameter_cm':.35,'seat_z_cm':list(SEAT_Z),'ads_distance_cm':67.,
    'post_tip_width_cm':.08,'triangles':len(obj.data.polygons),
    'materials':[m.name for m in obj.data.materials],
    'source_bow':'WoodLongbow20260925/WoodLongbow_Editable.blend',
    'wood_pbr_source':'WoodLongbow20260925/Textures/Image_0,1,2.png',
    'construction':'original exact union, circular ring, vertical post, ray-fitted seat',
    'runtime_tested':False,'rendered':False},indent=2),encoding='utf8')
print('BOW_FINE_RING_SIGHT_AUTHORED',len(obj.data.polygons))
