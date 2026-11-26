"""Hair-shape preview using actual authored strands and the preserved Meshy face."""
import bpy,json,math,os,sys
from pathlib import Path
from mathutils import Vector
N=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115');R=N/'HairNativeCombR9';O=R/'NativePreview';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'Authored/Native_Donor.blend'))
before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(N/'MeshyHeadR1/Source/NunHead_R1_glb.glb'))
source=next(o for o in bpy.data.objects if o not in before and o.type=='MESH');mat=source.data.materials[0]
d=json.loads((N/'FaceOriginalRestoreR6/Authored/head.json').read_text());me=bpy.data.meshes.new('OriginalMeshyFace');me.from_pydata(d['positions'],[],[t[::-1] for t in d['triangles']]);me.update();me.materials.append(mat);me.uv_layers.new(name='UVMap')
for f,uv in zip(me.polygons,d['uv']):
 f.use_smooth=True
 for li,xy in zip(f.loop_indices,uv[::-1]):me.uv_layers.active.data[li].uv=(xy[0],1-xy[1])
me.normals_split_custom_set([n for ns in d['normals'] for n in ns[::-1]])
for ob in list(bpy.data.objects):
 if ob not in before:bpy.data.objects.remove(ob,do_unlink=True)
head=bpy.data.objects.new('OriginalMeshyFace',me);bpy.context.collection.objects.link(head)
hair=bpy.data.materials.new('ReferenceBlackHair');hair.use_nodes=True;nt=hair.node_tree;nt.nodes.clear();bs=nt.nodes.new('ShaderNodeBsdfHairPrincipled');bs.parametrization='MELANIN';bs.inputs['Melanin'].default_value=.94;bs.inputs['Melanin Redness'].default_value=0.;bs.inputs['Roughness'].default_value=.37;bs.inputs['Random Roughness'].default_value=.25;bs.inputs['Random Color'].default_value=.05;out=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(bs.outputs[0],out.inputs['Surface'])
for ob in bpy.data.objects:
 if ob.type=='CURVES':ob.data.materials.append(hair)
 ob.scale=(-.01,.01,.01)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for device in prefs.devices:device.use=device.type=='OPTIX'
scene.cycles.device='GPU';scene.render.resolution_x=960;scene.render.resolution_y=960;scene.render.resolution_percentage=100
if os.environ.get('NUN_HAIR_DRAFT')=='1' or '--draft' in sys.argv:
 scene.cycles.samples=24;scene.render.resolution_x=720;scene.render.resolution_y=720
scene.world=bpy.data.worlds.new('NeutralStudio');scene.world.use_nodes=True;bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.38,.38,.38,1);bg.inputs['Strength'].default_value=.35
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
def area(name,loc,energy,size):
 light=bpy.data.lights.new(name,'AREA');light.energy=energy;light.shape='DISK';light.size=size;ob=bpy.data.objects.new(name,light);bpy.context.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,1.59))-ob.location).to_track_quat('-Z','Y').to_euler()
area('LargeKey',(-.35,.45,1.98),12,.5);area('SoftFill',(.40,.25,1.62),6,.5);area('HairRim',(.15,-.45,1.88),10,.35)
cam=bpy.data.cameras.new('ReferenceCamera');camera=bpy.data.objects.new('ReferenceCamera',cam);bpy.context.collection.objects.link(camera);scene.camera=camera;cam.type='ORTHO';cam.ortho_scale=.31
for name,loc in [('front',(0,.80,1.61)),('profile',(.85,0,1.62))]:
 camera.location=loc;camera.rotation_euler=(Vector((0,0,1.585))-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
print('REFERENCE_HAIR_PREVIEW_RENDERED',flush=True)
