"""Keep the anatomy; transfer smooth skin and fit separate cloth simulation islands."""
from pathlib import Path
import bpy, json, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006');OUT=ROOT/'RigRepairV3'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'LocomotionV2/BoundCongregate_LocomotionV2.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis.identity()
body=bpy.data.objects['BC_Flesh'];skin=np.load(OUT/'skin_weights.npz');names=skin['names'].tolist()
body.vertex_groups.clear()
for name in names:body.vertex_groups.new(name=name)
for vi,(ids,weights) in enumerate(zip(skin['indices'],skin['weights'])):
    for j,w in zip(ids,weights):body.vertex_groups[names[int(j)]].add([vi],float(w),'REPLACE')
points=[v.co.copy() for v in body.data.vertices];faces=[p.vertices[:] for p in body.data.polygons]
bvh=BVHTree.FromPolygons(points,faces)
W=np.zeros((len(points),len(names)))
W[np.arange(len(points))[:,None],skin['indices']]=skin['weights']
recipe=json.loads((ROOT/'Authoring/rig_recipe.json').read_text())
def point(p):return Vector((p[0]*recipe['scale'],p[1]*recipe['scale'],(p[2]-recipe['ground_z'])*recipe['scale']))
def nearest_weights(p):
    hit,normal,face,_=bvh.find_nearest(p);ids=faces[face][:3]
    bc=barycentric_transform(hit,*[points[i] for i in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
    bc=np.maximum(np.array(bc),0);bc/=max(1e-8,bc.sum())
    weights=bc@W[list(ids)];idx=np.argsort(weights)[-8:];value=weights[idx];value/=value.sum()
    return idx,value
def outside(p,clearance):
    # Repeat against the complete body so an outward move cannot end inside a
    # neighbouring pustule/limb. This also fixes original rest-pose intersections.
    p=p.copy()
    for _ in range(16):
        hit,normal,_,_=bvh.find_nearest(p);gap=(p-hit).dot(normal)
        if gap>=clearance-1e-5:break
        p+=normal*(clearance-gap+.001)
    return p
def skin_cloth(ob,pin_values):
    ob.vertex_groups.clear()
    for n in names:ob.vertex_groups.new(name=n)
    for vi,v in enumerate(ob.data.vertices):
        idx,value=nearest_weights(v.co)
        for j,w in zip(idx,value):ob.vertex_groups[names[int(j)]].add([vi],float(w),'REPLACE')
    ob.modifiers.clear();mod=ob.modifiers.new('SurfaceMatchedSkin','ARMATURE');mod.object=rig;ob.parent=rig
    for attr in list(ob.data.color_attributes):ob.data.color_attributes.remove(attr)
    attr=ob.data.color_attributes.new(name='ClothTravel',type='FLOAT_COLOR',domain='POINT')
    for c,pin in zip(attr.data,pin_values):c.color=(pin,0,0,1)
    ob.data.update()
for ob in list(bpy.context.scene.objects):
    if ob.name.endswith('_SimulationProxy'):bpy.data.objects.remove(ob,do_unlink=True)
fabric=bpy.data.materials['BC_RagFabric']
garments=[]
for name in ('BC_LeftTornRobe','BC_RightLining'):
    ob=bpy.data.objects[name]
    # Retain only the original exterior layer of the previously solidified cape.
    bm=__import__('bmesh').new();bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table();half=len(bm.verts)//2
    __import__('bmesh').ops.delete(bm,geom=list(bm.verts)[half:],context='VERTS')
    __import__('bmesh').ops.subdivide_edges(bm,edges=list(bm.edges),cuts=1,use_grid_fill=True)
    bm.to_mesh(ob.data);bm.free()
    pins=[]
    for v in ob.data.vertices:
        v.co=outside(v.co,.035)
        # Travel grows gradually down the cape, remaining below its flesh gap.
        pins.append(.045*max(0,min(1,(1.40-v.co.z)/.65)))
    skin_cloth(ob,pins);garments.append(ob)

for index,material_name in ((1,'BC_SleeveLeft'),(8,'BC_SleeveRight')):
    old=bpy.data.objects.get('BC_DonorSleeve'+str(index))
    if old:bpy.data.objects.remove(old,do_unlink=True)
    leg=recipe['legs'][index];_,knee,ankle,_=[point(p) for p in leg['points']]
    axis=(ankle-knee).normalized();x=axis.cross(Vector((0,0,1))).normalized();y=x.cross(axis).normalized()
    leg_ids=[names.index('leg_'+leg['name']+'_'+suffix) for suffix in ('upper','lower','foot')]
    # Extract the sleeve shell from the actual limb surface. The old cylinder
    # was centred on an approximate bone and could completely miss an irregular
    # donor leg. Surface topology supplies the circumference and joint shape.
    length=(ankle-knee).length
    selected=[]
    for face in faces:
        center=sum((points[i] for i in face),Vector())/len(face)
        along=(center-knee).dot(axis)/length
        radial=(center-knee)-axis*((center-knee).dot(axis))
        if .18<along<.66 and radial.length<.32 and np.mean(W[list(face)][:,leg_ids].sum(1))>.25:
            selected.append(face)
    used=sorted(set(i for face in selected for i in face))
    if len(used)<40:raise RuntimeError('Insufficient sleeve surface '+leg['name'])
    remap={old:new for new,old in enumerate(used)}
    verts=[];pins=[]
    for i in used:
        q=outside(points[i]+body.data.vertices[i].normal*.032,.026)
        v=(points[i]-knee).dot(axis)/length
        verts.append(q);pins.append(.024*max(0,min(1,(v-.59)/.07)))
    polys=[tuple(remap[i] for i in face) for face in selected]
    uvs=[]
    for face in selected:
        coordinates=[]
        for i in face:
            delta=points[i]-knee
            coordinates.append((math.atan2(delta.dot(y),delta.dot(x))/math.tau+.5,delta.dot(axis)/.35))
        if max(c[0] for c in coordinates)-min(c[0] for c in coordinates)>.5:
            coordinates=[(c[0]+(1 if c[0]<.5 else 0),c[1]) for c in coordinates]
        uvs.append(coordinates)
    data=bpy.data.meshes.new('FittedSleeve_'+leg['name']);data.from_pydata(verts,[],polys);data.update()
    ob=bpy.data.objects.new('BC_DonorSleeve'+str(index),data);bpy.context.collection.objects.link(ob)
    mat=fabric.copy();mat.name=material_name;data.materials.append(mat)
    uv=data.uv_layers.new(name='UVMap')
    for poly,coordinates in zip(data.polygons,uvs):
        poly.use_smooth=True
        for loop,co in zip(poly.loop_indices,coordinates):uv.data[loop].uv=co
    skin_cloth(ob,pins);garments.append(ob)

for ob in garments:
    # Four independent render/simulation pairs prevent sleeve transfer from
    # selecting a nearby cape triangle that merely shares the same material.
    proxy=ob.copy();proxy.data=ob.data.copy();proxy.name=ob.name+'_SimulationProxy'
    bpy.context.collection.objects.link(proxy)
    mat=ob.data.materials[0].copy();mat.name=ob.data.materials[0].name+'_Proxy';proxy.data.materials[0]=mat;proxy.hide_render=True
    bpy.context.view_layer.objects.active=ob
    solid=ob.modifiers.new('RealFabricThickness','SOLIDIFY');solid.thickness=.004;solid.offset=1
    bpy.ops.object.modifier_apply(modifier=solid.name)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BoundCongregate_RigV3.blend'))
bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.context.scene.objects:
    if ob.type in ('MESH','ARMATURE'):ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_BoundCongregate_RigV3.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
    add_leaf_bones=False,use_armature_deform_only=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
print('RIG_CLOTH_V3_EXPORTED',flush=True)
