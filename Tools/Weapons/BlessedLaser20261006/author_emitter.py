"""Build the approved hard-surface emitter with the V2 fitted firearm mounts.

Metres in Blender. The canonical emitter is at (0,0,0), +X forward, +Z toward
the mount. Per-gun host interfaces are fitted by fit_mounts.py; optical sockets stay fixed.
No viewport, gameplay or acceptance render is launched.
"""
import bpy
import bmesh
import json
import math
import re
from pathlib import Path
from mathutils import Vector, Matrix

P = Path(__file__).resolve().parents[3]
O = P / 'SourceAssets/BlessedLaser20261006/Model'
O.mkdir(parents=True, exist_ok=True)
(O / 'Exports').mkdir(exist_ok=True)
(O / 'Fitted').mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.read_factory_settings(use_empty=True)
materials = {}
for name, color, metal, rough in [
    ('Blessed_Graphite', (.045,.051,.06,1), .8, .34),
    ('Blessed_Gold', (.68,.43,.14,1), .92, .25),
    ('Blessed_Black', (.009,.011,.014,1), .25, .5),
    ('Blessed_Optic', (.19,.064,.004,1), .72, .16),
    ('Blessed_Aperture', (1,.32,.004,1), .15, .22),
]:
    m = bpy.data.materials.new(name)
    m.diffuse_color = color
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = color
    bs.inputs['Metallic'].default_value = metal
    bs.inputs['Roughness'].default_value = rough
    if name == 'Blessed_Aperture':
        bs.inputs['Emission Color'].default_value = color
        bs.inputs['Emission Strength'].default_value = 2
    materials[name] = m


def select(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.hide_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def mesh_object(name, verts, faces, mat, bevel=0):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    ob = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(ob)
    data.materials.append(materials[mat])
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    if bevel:
        select(ob)
        modifier = ob.modifiers.new('Machined edge', 'BEVEL')
        modifier.width = bevel
        modifier.segments = 3
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return ob


def prism(name, polygon_xz, y0, y1, mat, bevel=0):
    n = len(polygon_xz)
    verts = [(x,y,z) for y in [y0,y1] for x,z in polygon_xz]
    faces = [tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh_object(name, verts, faces, mat, bevel)


def box(name, center, size, mat, bevel=0):
    x,y,z = center
    a,b,c = (v/2 for v in size)
    return prism(name,[(x-a,z-c),(x+a,z-c),(x+a,z+c),(x-a,z+c)],y-b,y+b,mat,bevel)


def lathe(name, profile, mat, segments=64, faceted=False):
    verts = []
    for x,r in profile:
        for i in range(segments):
            angle = 2*math.pi*i/segments
            radius = r
            if faceted:
                radius *= math.cos(math.pi/8)/math.cos((angle+math.pi/8)%(math.pi/4)-math.pi/8)
            verts.append((x,radius*math.cos(angle),radius*math.sin(angle)))
    faces = []
    for j in range(len(profile)):
        k = (j+1)%len(profile)
        for i in range(segments):
            n = (i+1)%segments
            faces.append((j*segments+i,j*segments+n,k*segments+n,k*segments+i))
    ob = mesh_object(name,verts,faces,mat)
    for face in ob.data.polygons:
        face.use_smooth = not faceted
    return ob


def line(name, points, radius, mat, closed=False):
    curve = bpy.data.curves.new(name,'CURVE')
    curve.dimensions = '3D'
    curve.bevel_depth = radius
    curve.bevel_resolution = 1
    curve.resolution_u = 1
    curve.use_fill_caps = True
    spline = curve.splines.new('POLY')
    spline.points.add(len(points)-1)
    for point, coord in zip(spline.points,points):
        point.co = (*coord,1)
    spline.use_cyclic_u = closed
    ob = bpy.data.objects.new(name,curve)
    bpy.context.collection.objects.link(ob)
    curve.materials.append(materials[mat])
    select(ob)
    bpy.ops.object.convert(target='MESH')
    return bpy.context.object


# Octagonal armored capsule. Its solid nose backs the inset optical well.
sections = [(-.071,.0098,.0108),(-.066,.012,.014),(-.015,.012,.014),(-.007,.0098,.0108)]
verts = []
for x,w,h in sections:
    verts += [(x,y,z) for y,z in [(-w,-h*.60),(-w*.60,-h),(w*.60,-h),(w,-h*.60),(w,h*.60),(w*.60,h),(-w*.60,h),(-w,h*.60)]]
faces = [tuple(range(7,-1,-1)),tuple(range(24,32))]
for j in range(3):
    faces += [(j*8+i,j*8+(i+1)%8,(j+1)*8+(i+1)%8,(j+1)*8+i) for i in range(8)]
mesh_object('Sealed armored capsule',verts,faces,'Blessed_Graphite',.00035)

# Closed black baffle ring; dedicated optics never share the shell's material.
lathe('Octagonal gold bezel',[(-.009,.0135),(-.006,.0135),(-.0055,.0127),(-.0055,.0118),(-.009,.0118)],'Blessed_Gold',64,True)
lathe('Black recessed optical baffle',[(-.0065,.0117),(-.001,.0117),(0,.0105),(0,.0060),(-.005,.0060),(-.0065,.0069)],'Blessed_Black',64,True)
lathe('Inner lens retaining ring',[(-.0049,.0059),(-.0042,.0059),(-.0040,.0051),(-.0048,.0051)],'Blessed_Gold')
lathe('Amber optical cup',[(-.006,.0050),(-.0047,.0050),(-.0042,.0037),(-.0039,.0020),(-.0045,.0020),(-.006,.0037)],'Blessed_Optic')
# A closed short cylinder at the bottom of the recess forms the only emitter.
bpy.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=16,location=(-.0041,0,0))
lens = bpy.context.object
lens.name = 'Inset gold emitting lens'
lens.scale = (.00045,.0021,.0021)
lens.data.materials.append(materials['Blessed_Aperture'])
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
for face in lens.data.polygons:
    face.use_smooth = True

# Thin proud panels and shallow gold inlays follow the approved chamfered outline.
panel = [(-.066,-.0068),(-.060,-.0100),(-.020,-.0100),(-.011,-.0038),(-.013,.006),(-.020,.0094),(-.059,.0094),(-.066,.0052)]
for side in [-1,1]:
    y = side*.01205
    prism('Side armor panel',panel,y-side*.00028,y+side*.00036,'Blessed_Graphite',.00023)
    for points in [[(-.063,.0096),(-.055,.0096),(-.052,.0108),(-.021,.0108),(-.016,.0082)],
                   [(-.064,-.0069),(-.059,-.0102),(-.049,-.0102)],
                   [(-.029,-.0102),(-.020,-.0102),(-.013,-.0052)]]:
        line('Recessed gold edge inlay',[(x,side*.01245,z) for x,z in points],.00022,'Blessed_Gold')
    # Sun/halo ornament is real thin inlay geometry, not a glowing body mask.
    cx,cz = -.048,-.0008
    surface = side*.01246
    for radius in [.00325,.0040]:
        line('Halo concentric engraving',[(cx+math.cos(i*math.tau/64)*radius,surface,cz+math.sin(i*math.tau/64)*radius) for i in range(64)],.000045,'Blessed_Gold',True)
    for i in range(32):
        a = math.tau*i/32
        inner,outer = .0046,(.0072 if i%4==0 else .0061 if i%2==0 else .00555)
        line('Halo ray',[(cx+math.cos(a)*r,surface,cz+math.sin(a)*r) for r in [inner,outer]],.000038,'Blessed_Gold')
    line('Halo longitudinal line',[(cx+.0041,surface,cz),(-.019,surface,cz)],.000048,'Blessed_Gold')
    for x,z in [(-.059,.0065),(-.019,-.0055),(-.065,-.0038)]:
        screw=lathe('Recessed fastener',[(-.0005,.00125),(0,.0014),(.00025,.00115),(.00025,.00064),(-.0001,.00064),(-.0005,.0008)],'Blessed_Black',32)
        screw.rotation_euler = (0,0,side*math.pi/2)
        screw.location = (x,side*.01235,z)

# Rear gasket, rotary cap and tactile ridges.
lathe('Rear gold seam',[(-.0715,.0108),(-.0707,.0113),(-.0698,.0113),(-.0698,.0097),(-.0715,.0097)],'Blessed_Gold',64,True)
lathe('Rear rubber switch',[(-.0745,.0067),(-.0725,.0075),(-.0712,.0075),(-.0712,.0002),(-.0745,.0002)],'Blessed_Black')
for i in range(40):
    a=i*math.tau/40
    line('Switch knurl',[(-.0740,math.cos(a)*.0073,math.sin(a)*.0073),(-.0725,math.cos(a)*.00755,math.sin(a)*.00755)],.00012,'Blessed_Black')
box('Top keyed seating block',(-.045,0,.0156),(.024,.015,.0045),'Blessed_Graphite',.00065)
box('Top seat gold key',(-.039,0,.0144),(.013,.016,.001),'Blessed_Gold',.00018)

# Useful physical UV scale on the new surfaces; source shoe UVs remain untouched.
for ob in list(bpy.context.scene.objects):
    if ob.type != 'MESH':
        continue
    select(ob)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    uv = ob.data.uv_layers.new(name='SurfaceUV')
    for face in ob.data.polygons:
        axis = max(range(3),key=lambda i:abs(face.normal[i]))
        axes = [i for i in range(3) if i!=axis]
        for li in face.loop_indices:
            p = ob.data.vertices[ob.data.loops[li].vertex_index].co
            uv.data[li].uv = (p[axes[0]]/.015,p[axes[1]]/.015)

bpy.ops.wm.save_as_mainfile(filepath=str(O/'BlessedLaser_Master.blend'))
master_names = [ob.name for ob in bpy.context.scene.objects if ob.type=='MESH']


def join_meshes(objects,name):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:
        ob.hide_set(False)
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    ob=bpy.context.object
    ob.name=name
    bpy.context.scene.cursor.location=(0,0,0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    return ob


def export(ob,path):
    # Export explicit triangles so all new bevels and retained shoe tangents
    # have an unambiguous representation in both FBX and Unreal.
    select(ob)
    triangulate=ob.modifiers.new('Game triangles','TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    for child in ob.children:
        if child.type=='EMPTY':child.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)


canonical=join_meshes([bpy.data.objects[n] for n in master_names],'SM_BlessedLaser_Master')
export(canonical,O/'Exports/SM_BlessedLaser_Master.fbx')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'BlessedLaser_GameMaster.blend'))

# V2 uses measured current-host contact surfaces and explicit family interfaces.
# The retired material-count/body-bounds fitting recipe is kept only in
# trash/weapon-accessories-20261006/SourceAssets/BlessedLaser20261006/Model/MountRepair/Before/author_emitter.py.
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fit_mounts import run as fit_current_mounts
fit_current_mounts()
