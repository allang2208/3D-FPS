"""Prepare the retained timber mother and end-grain material; use repair_solid_logs.py for game meshes."""
import bpy
import numpy as np
from pathlib import Path
from mathutils import Vector

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

cap=bpy.data.materials.new('TimberEndGrain');cap.use_nodes=True
bsdf=next(n for n in cap.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bsdf.inputs['Roughness'].default_value=.82
tex=cap.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/'cut_surface_reference.png'))
uv=cap.node_tree.nodes.new('ShaderNodeTexCoord');mapping=cap.node_tree.nodes.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY_ADD'
mapping.inputs[1].default_value=(.28,.56,1);mapping.inputs[2].default_value=(.65,.17,0)
cap.node_tree.links.new(uv.outputs['UV'],mapping.inputs[0]);cap.node_tree.links.new(mapping.outputs['Vector'],tex.inputs['Vector']);cap.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])

cap.use_fake_user=True
master.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'HarvestTimber_Editable.blend'))
print('TIMBER_MOTHER_PREPARED',flush=True)
