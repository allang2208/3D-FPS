"""Bake the supplied GLB into a standalone canonical display mesh and PBR source."""
import bpy
import hashlib
import json
import math
import struct
from pathlib import Path
import numpy as np
from mathutils import Vector, Matrix

P=Path('D:/FPS3D/FPSGAME');ROOT=P/'SourceAssets/SpecialDutyBackpack20261024';R=ROOT/'MeshyFitR1_20261024'
src=ROOT/'Input/Meshy_AI_Rugged_Expedition_Pac_1024095908_texture.glb'
calibration=json.loads((R/'calibration.json').read_text())
blob=src.read_bytes();length,_=struct.unpack_from('<II',blob,12);gltf=json.loads(blob[20:20+length]);binary=blob[28+length:]
material=gltf['materials'][0]
channels={'BaseColor':material['pbrMetallicRoughness']['baseColorTexture']['index'],
          'MetallicRoughness':material['pbrMetallicRoughness']['metallicRoughnessTexture']['index'],
          'Normal_GL':material['normalTexture']['index']}
textures={}
for key,index in channels.items():
    image=gltf['images'][gltf['textures'][index]['source']];view=gltf['bufferViews'][image['bufferView']]
    ext='.jpg' if image['mimeType']=='image/jpeg' else '.png';path=R/'Textures'/('T_SpecialDuty_'+key+ext)
    offset=view.get('byteOffset',0);path.write_bytes(binary[offset:offset+view['byteLength']]);textures[key]=str(path)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(src));bpy.context.view_layer.update()
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
if len(objects)!=1:raise RuntimeError('This authored source expects the supplied single-mesh GLB')
ob=objects[0];me=ob.data;me.calc_loop_triangles()
matrix=np.asarray(ob.matrix_world,dtype=float)
yaw=np.asarray(Matrix.Rotation(math.radians(calibration['source_yaw_degrees']),3,'Z'))
transform=yaw@matrix[:3,:3];translation=yaw@matrix[:3,3]
v=np.asarray([list(x.co) for x in me.vertices],float)@transform.T+translation
faces=np.asarray([list(t.vertices) for t in me.loop_triangles],np.int32)
loops=np.asarray([list(t.loops) for t in me.loop_triangles],np.int32)
normal_matrix=np.linalg.inv(transform)
normals=np.asarray([list(n.vector) for n in me.corner_normals],float)[loops]@normal_matrix
normals/=np.maximum(np.linalg.norm(normals,axis=-1,keepdims=True),1e-12)
uv=np.asarray([list(t.uv) for t in me.uv_layers.active.data],np.float32)[loops]
lo,hi=v.min(0),v.max(0);scale=calibration['height_cm']/(hi[2]-lo[2])
v=(v-(lo+hi)/2)*scale
ue_uv=uv.copy();ue_uv[:,:,1]=1-ue_uv[:,:,1]
np.savez_compressed(R/'Authored/static_source.npz',positions=v.astype(np.float32),triangles=faces,
                    normals=normals.astype(np.float32),uv=ue_uv)
# Use explicit baked vertex coordinates on an unparented identity object. This
# also handles glTF's quaternion-mode root without an unapplied Euler rotation.
materials=list(me.materials)
for obj in list(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
mesh=bpy.data.meshes.new('SpecialDutyCanonical');mesh.from_pydata((v/100).tolist(),[],faces.tolist());mesh.update()
for m in materials:mesh.materials.append(m)
layer=mesh.uv_layers.new(name='UVMap');layer.data.foreach_set('uv',uv.reshape(-1))
for poly in mesh.polygons:poly.use_smooth=True
mesh.normals_split_custom_set(normals.reshape(-1,3).tolist())
ob=bpy.data.objects.new('SpecialDutyBackpack_Source',mesh);bpy.context.scene.collection.objects.link(ob)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'SpecialDutyBackpack_source.blend'))
receipt={'source_sha256':hashlib.sha256(blob).hexdigest(),'vertices':len(v),'triangles':len(faces),
         'dimensions_cm':np.ptp(v,axis=0).tolist(),'uniform_scale':float(scale),'textures':textures,'source_double_sided':material.get('doubleSided',False),
         'decimation_applied':False,'geometry_convention':'cross_e1_e2','source_yaw_degrees':calibration['source_yaw_degrees'],
         'rotation_method':'explicit vertex/world-matrix bake, unparented identity display',
         'outward_front':'-Y','wearer_face':'+Y','up':'+Z'}
(R/'source_prepared.json').write_text(json.dumps(receipt,indent=2))
# Production icons are exported from the UE equipment studio after publication.
print('SPECIAL_DUTY_SOURCE_READY',json.dumps(receipt),flush=True)
