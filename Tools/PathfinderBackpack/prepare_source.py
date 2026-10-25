"""Preserve the supplied Meshy source and produce the actual inventory icon."""
import bpy,json,struct,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector, Matrix
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/PathfinderBackpack20261023/OrientationFitR2_20261024';src=R.parent/'Input/Meshy_AI_Expedition_Tactical_B_1023085801_texture.glb'
for d in ['Textures','Authored','Icon']:(R/d).mkdir(exist_ok=True)
blob=src.read_bytes();n,_=struct.unpack_from('<II',blob,12);g=json.loads(blob[20:20+n]);binary=blob[28+n:];mat=g['materials'][0]
mapping={'BaseColor':mat['pbrMetallicRoughness']['baseColorTexture']['index'],'MetallicRoughness':mat['pbrMetallicRoughness']['metallicRoughnessTexture']['index'],'Normal_GL':mat['normalTexture']['index']}
textures={}
for key,ti in mapping.items():
    img=g['images'][g['textures'][ti]['source']];view=g['bufferViews'][img['bufferView']];offset=view.get('byteOffset',0)
    dest=R/'Textures'/('T_Pathfinder_'+key+('.jpg' if img['mimeType']=='image/jpeg' else '.png'))
    dest.write_bytes(binary[offset:offset+view['byteLength']]);textures[key]=str(dest)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(src))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];bpy.ops.object.select_all(action='DESELECT')
for ob in objects:ob.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
if len(objects)>1:bpy.ops.object.join()
# glTF objects use quaternion rotation mode. Editing rotation_euler did nothing.
# Rotate the world matrix so the padded wearer face is +Y, outer pouches -Y.
ob=bpy.context.object;ob.matrix_world=Matrix.Rotation(3.141592653589793,4,'Z') @ ob.matrix_world;ob.name='PathfinderBackpack_Source';bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
me=ob.data;v=np.asarray([list(v.co) for v in me.vertices]);lo,hi=v.min(0),v.max(0)
# Keep the full model at 68 cm overall height; wearable depth is calibrated from its rear panel.
scale=.68/(hi[2]-lo[2]);centre=(lo+hi)/2
for vertex in me.vertices:vertex.co=(vertex.co-Vector(centre))*scale
# Match the approved overall width while keeping height and pouch depth.
width=max(v.co.x for v in me.vertices)-min(v.co.x for v in me.vertices)
ob.scale.x=.52/width
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
me.update();me.calc_loop_triangles();uv=me.uv_layers.active
positions=np.asarray([list(v.co) for v in me.vertices],np.float32)*100
faces=np.asarray([list(f.vertices) for f in me.loop_triangles],np.int32)
loops=np.asarray([list(f.loops) for f in me.loop_triangles],np.int32)
normals=np.asarray([list(n.vector) for n in me.corner_normals],np.float32)[loops]
tex=np.asarray([list(x.uv) for x in uv.data],np.float32)[loops];tex[:,:,1]=1-tex[:,:,1]
np.savez_compressed(R/'Authored/static_source.npz',positions=positions,triangles=faces,normals=normals,uv=tex)
receipt={'source_sha256':hashlib.sha256(blob).hexdigest(),'vertices':len(positions),'triangles':len(faces),'dimensions_cm':np.ptp(positions,axis=0).tolist(),
         'source_double_sided':mat.get('doubleSided',False),'decimation_applied':False,'textures':textures,'geometry_convention':'cross_e1_e2','wearer_face':'+Y','outer_face':'-Y','source_yaw_degrees':180,'rotation_method':'world_matrix (glTF quaternion mode)' }
(R/'source_prepared.json').write_text(json.dumps(receipt,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'PathfinderBackpack_source.blend'))
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=320;scene.render.resolution_y=320;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('IconWorld');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.45,.45,.45,1);bg.inputs[1].default_value=.5
for name,position,power,size in [('Key',(-1,-2,2),200,2),('Fill',(2,-1,.8),150,2),('Rim',(0,1,1.6),200,1.5)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
    node=bpy.data.objects.new(name,light);scene.collection.objects.link(node);node.location=position;node.rotation_euler=(-node.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.cameras.new('ItemIcon');node=bpy.data.objects.new('ItemIcon',cam);scene.collection.objects.link(node)
node.location=(.95,-2.4,.65);node.rotation_euler=(-node.location).to_track_quat('-Z','Y').to_euler();cam.type='ORTHO';cam.ortho_scale=.78;scene.camera=node
scene.render.filepath=str(R/'Icon/source_icon.png');bpy.ops.render.render(write_still=True)
print('PATHFINDER_SOURCE_READY',json.dumps(receipt),flush=True)
