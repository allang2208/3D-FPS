"""Import the user's reduced Meshy GLB, preserve geometry and make its item icon."""
import bpy,json,struct,hashlib,math
from pathlib import Path
from mathutils import Vector
import numpy as np

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ExpeditionBackpack20261022'
src=R/'Input/Meshy_AI_Expedition_Backpack_1022050243_texture.glb'
for folder in ('Textures','Authored','Icon'):(R/folder).mkdir(exist_ok=True)
blob=src.read_bytes();n,_=struct.unpack_from('<II',blob,12);gltf=json.loads(blob[20:20+n])
start=20+n;binary=blob[start+8:]
names=['T_Expedition_Normal_GL','T_Expedition_BaseColor','T_Expedition_MetallicRoughness']
for record,name in zip(gltf['images'],names):
    view=gltf['bufferViews'][record['bufferView']];offset=view.get('byteOffset',0)
    (R/'Textures'/(name+'.png')).write_bytes(binary[offset:offset+view['byteLength']])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(src))
objects=[ob for ob in bpy.context.scene.objects if ob.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for ob in objects:ob.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
if len(objects)>1:bpy.ops.object.join()
ob=bpy.context.object;ob.name='ExpeditionBackpack_Meshy'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
me=ob.data
v=np.array([list(v.co) for v in me.vertices]);lo,hi=v.min(0),v.max(0)
centre=(lo+hi)/2;scale=.62/(hi[2]-lo[2])
for vertex in me.vertices:vertex.co=(vertex.co-Vector(centre))*scale
me.update();me.calc_loop_triangles()
uv=me.uv_layers.active
data={'positions':[[c*100 for c in vertex.co] for vertex in me.vertices],
      'triangles':[],'uv':[],'normals':[],'triangle_materials':[],
      'geometry_convention':'cross_e1_e2','source':str(src),'revision':'ExpeditionMeshyR1_20261022',
      'materials':[{'slot':'ExpeditionFabric','asset':'/Game/Characters/ExpeditionBackpack20261022/M_ExpeditionBackpack.M_ExpeditionBackpack'}]}
for face in me.loop_triangles:
    loops=list(face.loops)
    data['triangles'].append([me.loops[li].vertex_index for li in loops])
    data['uv'].append([[uv.data[li].uv.x,1-uv.data[li].uv.y] for li in loops])
    data['normals'].append([list(me.corner_normals[li].vector) for li in loops])
    data['triangle_materials'].append(0)
(R/'Authored/static_source.json').write_text(json.dumps(data,separators=(',',':')))
bounds=np.asarray(data['positions'])
receipt={'input_sha256':hashlib.sha256(blob).hexdigest(),'source_vertices':len(me.vertices),
         'triangles':len(data['triangles']),'dimensions_cm':(bounds.max(0)-bounds.min(0)).tolist(),
         'blender_axes':'X width, Y depth, Z up; front to be identified from source icon',
         'unit_scale_from_blender':scale,'source_double_sided':gltf['materials'][0].get('doubleSided',False),
         'decimation_applied':False,'textures':[str(R/'Textures'/(n+'.png')) for n in names]}
(R/'source_prepared.json').write_text(json.dumps(receipt,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'ExpeditionBackpack_source.blend'))
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=768;scene.render.resolution_y=768;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('IconWorld');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.5,.5,.5,1);bg.inputs[1].default_value=.6
for name,position,power,size in [('Key',(-1,-2,2),220,2),('Fill',(2,-1,.8),180,2),('Rim',(0,1,1.6),240,1.5)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
    node=bpy.data.objects.new(name,light);scene.collection.objects.link(node);node.location=position
    node.rotation_euler=(-node.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.cameras.new('ItemIcon');node=bpy.data.objects.new('ItemIcon',cam);scene.collection.objects.link(node)
node.location=(1.05,-2.2,.85);node.rotation_euler=(-node.location).to_track_quat('-Z','Y').to_euler()
cam.type='ORTHO';cam.ortho_scale=.76;scene.camera=node
scene.render.filepath=str(R/'Icon/source_icon.png');bpy.ops.render.render(write_still=True)
print('EXPEDITION_SOURCE_PREPARED',json.dumps(receipt),flush=True)
