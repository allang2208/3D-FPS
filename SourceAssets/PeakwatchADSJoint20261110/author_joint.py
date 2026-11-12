"""Locally join the retained scope housing, curved support and bow saddle."""
from pathlib import Path
import bpy,bmesh,math,json,hashlib
from mathutils import Vector
P=Path(__file__).resolve().parent
SOURCE=P/'Before/Highland_Peakwatch3to6_Production.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version=0
body=bpy.data.objects['SM_Highland_Peakwatch3to6']
ring=bpy.data.objects['SM_Highland_PeakwatchZoomRing']
me=body.data
adj=[[] for _ in me.vertices]
for e in me.edges:
    a,b=e.vertices;adj[a].append(b);adj[b].append(a)
def component(first):
    found={first};todo=[first]
    while todo:
        i=todo.pop()
        for j in adj[i]:
            if j not in found:found.add(j);todo.append(j)
    return found
# These are semantic connected components of the backed-up V11 production mesh,
# not indices reused across a new export or a later mesh revision.
housing_ids=component(0);saddle_ids=component(22128)
rods=component(22990)|component(23246)
if (len(housing_ids),len(saddle_ids),len(rods))!=(2048,862,512):
    raise RuntimeError('Unexpected production source topology')
def extract(name,keep):
    mesh=me.copy();obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in keep],context='VERTS')
    bm.to_mesh(mesh);bm.free();return obj
housing=extract('Retained optical housing',housing_ids)
saddle=extract('Retained fitted saddle',saddle_ids)
outer_y=max(v.co.y for v in saddle.data.vertices)
# Seat the existing wood face and screw heads against the actual saddle plane.
for first,dy in ((23502,-.28),(23598,-.31),(23854,-.31),(23878,-.31),(24134,-.31)):
    for i in component(first):me.vertices[i].co.y+=dy
bm=bmesh.new();bm.from_mesh(me);bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index in housing_ids|saddle_ids|rods],context='VERTS')
bm.to_mesh(me);bm.free()

pin=Vector((-.4,10.223,24.3328)) # Blender Y is mirrored once on the UE export.
start=Vector((1,outer_y-.14,pin.z-1.45))
end=pin+Vector((.55,-1.535,-1.535))
inward=Vector((0,1,1)).normalized()
control=(start,start+Vector((-.35,2.6,0)),end-inward*.65,end)
def curve(t):
    a,b,c,d=control;s=1-t
    return s*s*s*a+3*s*s*t*b+3*s*t*t*c+t*t*t*d
def tangent(t):
    a,b,c,d=control;s=1-t
    return (3*s*s*(b-a)+6*s*t*(c-b)+3*t*t*(d-c)).normalized()
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
verts=[];faces=[];uvs=[];sections=64;sides=32
for j in range(sections+1):
    t=j/sections;pos=curve(t);axis=tangent(t)
    u=Vector((1,0,0));u=(u-axis*u.dot(axis)).normalized();v=axis.cross(u).normalized()
    radius=.16+.06*(1-smooth(t/.16))+.02*smooth((t-.80)/.20)
    for i in range(sides):
        a=i*math.tau/sides;verts.append(pos+radius*(math.cos(a)*u+math.sin(a)*v))
for j in range(sections):
    for i in range(sides):
        n=(i+1)%sides
        faces.append((j*sides+i,j*sides+n,(j+1)*sides+n,(j+1)*sides+i))
        uvs.append(((i/sides,j/sections),((i+1)/sides,j/sections),((i+1)/sides,(j+1)/sections),(i/sides,(j+1)/sections)))
faces.extend([tuple(reversed(range(sides))),tuple(sections*sides+i for i in range(sides))])
uvs.extend([tuple((.5+.5*math.cos(i*math.tau/sides),.5+.5*math.sin(i*math.tau/sides)) for i in reversed(range(sides))),
            tuple((.5+.5*math.cos(i*math.tau/sides),.5+.5*math.sin(i*math.tau/sides)) for i in range(sides))])
mesh=bpy.data.meshes.new('Continuous support sweep');mesh.from_pydata(verts,[],faces);mesh.update()
tube=bpy.data.objects.new('Continuous support sweep',mesh);bpy.context.scene.collection.objects.link(tube)
mesh.materials.append(bpy.data.materials['M_Peakwatch_Steel'])
uv=mesh.uv_layers.new(name='UVMap')
for poly,coords in zip(mesh.polygons,uvs):
    poly.use_smooth=len(poly.vertices)==4
    for li,coord in zip(poly.loop_indices,coords):uv.data[li].uv=coord

def active(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
active(housing)
for operand in (tube,saddle):
    modifier=housing.modifiers.new('Continuous solid joint','BOOLEAN')
    modifier.operation='UNION';modifier.solver='EXACT';modifier.object=operand;modifier.material_mode='TRANSFER'
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(operand,do_unlink=True)
# Only the joint/housing submesh is processed; lens, engravings, knurling and
# all their original face-corner UVs stay outside this operation.
bevel=housing.modifiers.new('Support junction edge radius','BEVEL')
bevel.width=.025;bevel.segments=3;bevel.limit_method='ANGLE';bevel.angle_limit=.60
bpy.ops.object.modifier_apply(modifier=bevel.name)
bm=bmesh.new();bm.from_mesh(housing.data)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(housing.data);bm.free()
active(body);housing.select_set(True);bpy.ops.object.join()
tri=body.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
body.data.update()
(P/'Export').mkdir(exist_ok=True)
active(body)
bpy.ops.export_scene.fbx(filepath=str(P/'Export/SM_Highland_Peakwatch3to6.fbx'),use_selection=True,object_types={'MESH'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_Peakwatch3to6_JointV12.blend'))
record=dict(source=str(SOURCE),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    mesh=body.name,triangles=len(body.data.polygons),materials=[m.name for m in body.data.materials],
    scope_center_ue_cm=[-.4,-10.223,24.3328],lens_radius_cm=1.95125,ring_reused='Scope3to6V11/SM_Highland_PeakwatchZoomRing',
    start_blender_cm=list(start),end_blender_cm=list(end),saddle_outer_y_cm=outer_y,
    operation='continuous closed sweep with exact union to retained housing and fitted saddle',
    wood_seating_delta_y_cm=-.28,screw_seating_delta_y_cm=-.31,gameplay_tested=False)
(P/'authoring.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('PEAKWATCH_JOINT_AUTHORED '+json.dumps(record),flush=True)
