"""Split retained bow by connected shells; author a small real arrow support."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent;OUT=P/'Export';OUT.mkdir(exist_ok=True)
WOOD=P.parent/'DarkBow20260925/WoodLongbow20260925'
bpy.ops.wm.open_mainfile(filepath=str(WOOD/'WoodLongbow_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
src=bpy.data.objects['SM_DarkBow_WoodLongbow']
for o in list(bpy.data.objects):
    if o!=src:bpy.data.objects.remove(o,do_unlink=True)
src.data=src.data.copy();scale=100 if max(src.dimensions)<5 else 1
for v in src.data.vertices:v.co=src.matrix_world@v.co*scale
src.matrix_world.identity();vv=[v.co.copy() for v in src.data.vertices]
adj=[[] for _ in vv]
for e in src.data.edges:a,b=e.vertices;adj[a].append(b);adj[b].append(a)
unseen=set(range(len(vv)));groups=[]
while unseen:
    start=unseen.pop();stack=[start];g=[start]
    while stack:
        for i in adj[stack.pop()]:
            if i in unseen:unseen.remove(i);stack.append(i);g.append(i)
    groups.append(g)
# The centre wrap is already separate geometry inside the combined static mesh.
# Retain limb/tip bindings on the bow body, and preserve UVs/normals verbatim.
grip_ids=set(i for g in groups if min(vv[i].z for i in g)>-12 and max(vv[i].z for i in g)<12 and len(g)>100 for i in g)
def extract(name,keep):
    data=src.data.copy();bm=bmesh.new();bm.from_mesh(data);bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in keep],context='VERTS')
    # The retained donor has inward triangle winding after its baked transform.
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active=o;o.select_set(True)
    if data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
    o.select_set(False);return o
body=extract('SM_Bow_BodyModular',set(range(len(vv)))-grip_ids)
grip=extract('SM_Bow_GripWrap',grip_ids)
tree=BVHTree.FromPolygons(vv,[list(p.vertices) for p in src.data.polygons])
bpy.data.objects.remove(src,do_unlink=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01

def material(name,color,rough):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    p=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if p is None:
        p=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');out=m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(p.outputs['BSDF'],out.inputs['Surface'])
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough
    return m
woodmat=material('ArrowRestWood',(.13,.055,.018),.61)
leather=material('ArrowRestLeather',(.10,.045,.022),.84)
rest_parts=[]
def finish(o,mat):
    o.data.materials.clear();o.data.materials.append(mat)
    bpy.context.view_layer.objects.active=o;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for p in o.data.polygons:p.use_smooth=True
    rest_parts.append(o);return o
def ue(p):return Vector((p[0],-p[1],p[2]))
def capsule(a,b,r,mat):
    a,b=ue(a),ue(b);d=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=r,depth=d.length,location=(a+b)*.5)
    o=bpy.context.object;o.rotation_mode='QUATERNION';o.rotation_quaternion=Vector((0,0,1)).rotation_difference(d.normalized());finish(o,mat)
    for c in [a,b]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,radius=r,location=c);finish(bpy.context.object,mat)

# A feathered seat on the current wrapped surface, fitted by rays. The shelf
# is below the existing arrow centre (-3.5,-3.9,2.6) and keeps the shaft path.
verts=[];faces=[];nx=13;nz=21
for back in [False,True]:
    for iz in range(nz):
        t=iz/(nz-1);z=.55+1.9*t;w=.15+.62*math.sin(math.pi*t)**.5
        for ix in range(nx):
            s=ix/(nx-1);x=-1.35+(2*s-1)*w
            hit,n,index,d=tree.ray_cast(Vector((x,8,z)),Vector((0,-1,0)),16)
            if hit is None:raise RuntimeError('Arrow rest attachment misses retained bow')
            hit.y+=(-.05 if back else .03+.25*math.sin(math.pi*t)*math.sin(math.pi*s))
            verts.append(hit)
layer=nx*nz
for off in [0,layer]:
    for z in range(nz-1):
        for x in range(nx-1):a=off+z*nx+x;faces.append((a,a+1,a+nx+1,a+nx))
border=list(range(nx))+[i*nx+nx-1 for i in range(1,nz)]+list(range(layer-2,layer-nx-1,-1))+[i*nx for i in range(nz-2,0,-1)]
for a,b in zip(border,border[1:]+border[:1]):faces.append((a,b,b+layer,a+layer))
me=bpy.data.meshes.new('RestSaddle');me.from_pydata(verts,[],faces);o=bpy.data.objects.new('RestSaddle',me);bpy.context.collection.objects.link(o);finish(o,woodmat)
capsule((-1.35,-3.15,1.55),(-2.0,-3.8,1.75),.27,woodmat)
capsule((-2.0,-3.8,1.75),(-3.4,-3.9,2.03),.22,woodmat)
bpy.ops.object.select_all(action='DESELECT')
for o in rest_parts:o.select_set(True)
bpy.context.view_layer.objects.active=rest_parts[0];bpy.ops.object.join();rest=bpy.context.object
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bm=bmesh.new();bm.from_mesh(rest.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(rest.data);bm.free()
rest.data.remesh_voxel_size=.035;bpy.ops.object.voxel_remesh()
m=rest.modifiers.new('Carved join','SMOOTH');m.factor=.55;m.iterations=4;bpy.ops.object.modifier_apply(modifier=m.name)
m=rest.modifiers.new('Small support detail','DECIMATE');m.ratio=.35;bpy.ops.object.modifier_apply(modifier=m.name)
rest.name='SM_Bow_ArrowRestWood'
for p in rest.data.polygons:p.use_smooth=True
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
for loop in rest.data.uv_layers.active.data:loop.uv=(.15+loop.uv.x*.045,.40+loop.uv.y*.065)

lined=bpy.data.objects.new('SM_Bow_ArrowRestLined',rest.data.copy());bpy.context.collection.objects.link(lined)
bpy.ops.mesh.primitive_cube_add(size=1,location=ue((-3.0,-3.9,2.225)))
pad=bpy.context.object;pad.name='Leather_contact_pad';pad.scale=(1.2,.45,.10);finish(pad,leather)
m=pad.modifiers.new('Soft leather edges','BEVEL');m.width=.04;m.segments=3;bpy.ops.object.modifier_apply(modifier=m.name)
bpy.ops.object.select_all(action='DESELECT');lined.select_set(True);pad.select_set(True);bpy.context.view_layer.objects.active=lined;bpy.ops.object.join()
assets=[body,grip,rest,lined]
info={'source':str(WOOD/'WoodLongbow_Editable.blend'),'split_method':'connected central wrap shells, exact source surfaces and UVs',
      'rest_arrow_axis_cm':[-3.5,-3.9,2.6],'assets':{},'gameplay_tested':False}
for o in assets:
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    m=o.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(o.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,use_tspace=True)
    info['assets'][o.name]={'triangles':len(o.data.polygons),'material_slots':[m.name for m in o.data.materials]}
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_ModularParts.blend'))
(P/'authoring.json').write_text(json.dumps(info,indent=2),encoding='utf8');print('BOW_MODULES_AUTHORED',flush=True)
