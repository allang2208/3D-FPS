"""Blender: preserve the generated mother mesh, bake detail and author timber pieces. No preview renders."""
import bpy, bmesh, json, math
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector

ROOT=Path(__file__).parent
OUT=ROOT/'Delivery';OUT.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'textured_master_00001_.glb'))
parts=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
bpy.ops.object.join();master=bpy.context.object;master.name='Poplar_GeneratedMother'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
points=np.array([v.co[:] for v in master.data.vertices])
_,axes=np.linalg.eigh(np.cov(points.T));long_axis=Vector(axes[:,-1])
if long_axis.z<0:long_axis=-long_axis
rotation=long_axis.rotation_difference(Vector((0,0,1))).to_matrix().to_4x4()
master.data.transform(rotation)
points=np.array([v.co[:] for v in master.data.vertices]);lo=points.min(0);hi=points.max(0)
for v in master.data.vertices:
    v.co.x=(v.co.x-(lo[0]+hi[0])*.5)*.31/(hi[0]-lo[0])
    v.co.y=(v.co.y-(lo[1]+hi[1])*.5)*.31/(hi[1]-lo[1])
    v.co.z=(v.co.z-lo[2])*.84/(hi[2]-lo[2])
master.data.update()
images={}
def texture_upstream(socket,seen=None):
    seen=set() if seen is None else seen
    for link in socket.links:
        n=link.from_node
        if n in seen:continue
        seen.add(n)
        if n.type=='TEX_IMAGE' and n.image:return n.image
        for inp in n.inputs:
            result=texture_upstream(inp,seen)
            if result:return result

material=next(m for m in master.data.materials if m and m.use_nodes)
principled=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
for kind,socket in [('BaseColor','Base Color'),('ORM','Roughness')]:
    img=texture_upstream(principled.inputs[socket])
    if img:
        img.filepath_raw=str(OUT/('T_Poplar_'+kind+'.png'));img.file_format='PNG';img.save()
        images[kind]=Path(img.filepath_raw).name

low=master.copy();low.data=master.data.copy();bpy.context.collection.objects.link(low);low.name='Poplar_Low_Work'
bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low
dec=low.modifiers.new('Game topology','DECIMATE');dec.ratio=min(1,6500/max(1,len(low.data.polygons)))
bpy.ops.object.modifier_apply(modifier=dec.name)
for p in low.data.polygons:p.use_smooth=True

# Tangent normal baking is asset production, not an acceptance render.
normal=bpy.data.images.new('T_Poplar_Normal',width=2048,height=2048,alpha=False)
normal.colorspace_settings.name='Non-Color'
for m in low.data.materials:
    n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=normal;m.node_tree.nodes.active=n
bpy.context.scene.render.engine='CYCLES';bpy.context.scene.cycles.device='CPU';bpy.context.scene.cycles.samples=8
bpy.context.scene.render.bake.use_selected_to_active=True
bpy.context.scene.render.bake.max_ray_distance=.035
bpy.context.scene.render.bake.cage_extrusion=.015
bpy.context.scene.render.bake.margin=12
bpy.ops.object.select_all(action='DESELECT');master.select_set(True);low.select_set(True);bpy.context.view_layer.objects.active=low
bpy.ops.object.bake(type='NORMAL')
normal.filepath_raw=str(OUT/'T_Poplar_Normal.png');normal.file_format='PNG';normal.save();images['Normal']='T_Poplar_Normal.png'

bark=material.copy();bark.name='TimberBark'
bsdf=next(n for n in bark.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
n=bark.node_tree.nodes.new('ShaderNodeTexImage');n.image=normal
nm=bark.node_tree.nodes.new('ShaderNodeNormalMap');bark.node_tree.links.new(n.outputs['Color'],nm.inputs['Color']);bark.node_tree.links.new(nm.outputs['Normal'],bsdf.inputs['Normal'])
bsdf.inputs['Metallic'].default_value=0

cap=bpy.data.materials.new('TimberEndGrain');cap.use_nodes=True
bsdf=next(n for n in cap.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bsdf.inputs['Roughness'].default_value=.82
tex=cap.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/'cut_surface_reference.png'))
uv=cap.node_tree.nodes.new('ShaderNodeTexCoord');mapping=cap.node_tree.nodes.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY_ADD'
mapping.inputs[1].default_value=(.28,.56,1);mapping.inputs[2].default_value=(.65,.17,0)
cap.node_tree.links.new(uv.outputs['UV'],mapping.inputs[0]);cap.node_tree.links.new(mapping.outputs['Vector'],tex.inputs['Vector']);cap.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])

def cut_piece(name,bottom,top,diameter,stump=False,twist=0):
    obj=low.copy();obj.data=low.data.copy();bpy.context.collection.objects.link(obj);obj.name=name
    obj.data.materials.clear();obj.data.materials.append(bark);obj.data.materials.append(cap)
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=(0,0,bottom),plane_no=(0,0,1),clear_inner=True)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=(0,0,top),plane_no=(0,0,1),clear_outer=True)
    filled=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)['faces']
    uv_layer=bm.loops.layers.uv.verify()
    for face in filled:
        face.material_index=1;face.smooth=False
        for loop in face.loops:loop[uv_layer].uv=(.5+loop.vert.co.x/.31,.5+loop.vert.co.y/.31)
    for v in bm.verts:
        z=(v.co.z-bottom)/(top-bottom)
        factor=diameter/.31
        if stump:factor*=1+.42*math.exp(-z*5)*(1+.18*math.sin(math.atan2(v.co.y,v.co.x)*5))
        angle=twist*z
        x,y=v.co.x,v.co.y
        v.co.x=(x*math.cos(angle)-y*math.sin(angle))*factor
        v.co.y=(x*math.sin(angle)+y*math.cos(angle))*factor
        v.co.z=(v.co.z-bottom)*(.42/(top-bottom) if stump else 1)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    if not stump:
        obj.data.transform(Matrix.Rotation(math.pi/2,4,'Y'))
        xs=[v.co.x for v in obj.data.vertices];mid=(min(xs)+max(xs))*.5
        for v in obj.data.vertices:v.co.x-=mid
    obj.data.update();return obj

delivery=[cut_piece('SM_PoplarLog_A',.02,.82,.31),cut_piece('SM_PoplarLog_B',.04,.77,.29,twist=.07),
          cut_piece('SM_PoplarLog_C',.025,.815,.34,twist=-.05),cut_piece('SM_PoplarStump',.02,.44,.36,stump=True)]
verts=[(0,0,0)]+[(.18*math.cos(i*2*math.pi/64),.18*math.sin(i*2*math.pi/64),0) for i in range(64)]
faces=[(0,i+1,(i+1)%64+1) for i in range(64)]
mesh=bpy.data.meshes.new('PoplarCutCap');mesh.from_pydata(verts,[],faces);mesh.materials.append(cap)
uv=mesh.uv_layers.new(name='UVMap')
for p in mesh.polygons:
    for idx in p.loop_indices:
        v=mesh.vertices[mesh.loops[idx].vertex_index].co;uv.data[idx].uv=(.5+v.x/.36,.5+v.y/.36)
obj=bpy.data.objects.new('SM_PoplarCutCap',mesh);bpy.context.collection.objects.link(obj);delivery.append(obj)
report={'textures':images,'reference_texture':'cut_surface_reference.png','meshes':{},'normal_format':'OpenGL; flip green when importing in UE',
        'source':'local TRELLIS.2 multiview mother mesh with local cuts, caps and root flare; no purchased assets'}
for obj in delivery:
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},add_leaf_bones=False,
        apply_unit_scale=True,axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
    report['meshes'][obj.name]={'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons),'dimensions_m':list(obj.dimensions),
        'materials':[m.name for m in obj.data.materials]}
master.hide_set(True);low.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HarvestTimber_Editable.blend'))
(OUT/'authoring.json').write_text(json.dumps(report,indent=2))
print('HARVEST_TIMBER_AUTHORED',json.dumps(report),flush=True)
