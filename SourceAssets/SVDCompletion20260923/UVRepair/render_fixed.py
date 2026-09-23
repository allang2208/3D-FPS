import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
O=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923');S=O.parent
file=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else S/'SVDDragunov20260922/Authored/SK_SVD_Viewmodel.blend'
bpy.ops.wm.open_mainfile(filepath=str(file));s=bpy.context.scene;r=next(o for o in s.objects if o.type=='ARMATURE')
if not r.animation_data or not r.animation_data.action:
 with bpy.data.libraries.load(str(S/'AKMSoviet20260911/AKM_Soviet_Editable.blend')) as (a,b):b.actions=['AKM_Native_idle']
 r.animation_data_create();a=bpy.data.actions['AKM_Native_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if len(args)>1:
 a=bpy.data.actions['A_SVD_'+args[1]];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
s.frame_set(int(args[2]) if len(args)>2 else s.frame_start);bpy.context.view_layer.update()
for o in list(s.objects):
 if o.type in ['CAMERA','LIGHT']:bpy.data.objects.remove(o,do_unlink=True)
for o in s.objects:
 if o.type!='MESH':continue
 m=bpy.data.materials.new('Review_'+o.name);m.diffuse_color=(.20,.24,.28,1) if 'Arms' in o.name else (.42,.38,.31,1)
 m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=m.diffuse_color;bs.inputs['Roughness'].default_value=.6
 if o.name.startswith('SM_SVD'):
  ts='pso' if 'Scope' in o.name else 'svd';tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(S/f'SVDDragunov20260922/Textures/T_SVD_{ts}_basecolor.jpg'));m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
 o.data.materials.clear();o.data.materials.append(m)
s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True;s.render.resolution_x=1000;s.render.resolution_y=700;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('ReviewWorld');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.3,.3,.3,1)
rt=r.matrix_world@r.pose.bones['WPN_root'].matrix
cam=bpy.data.objects.new('ReviewCamera',bpy.data.cameras.new('ReviewCamera'));s.collection.objects.link(cam);s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=1.15
sun=bpy.data.objects.new('ReviewSun',bpy.data.lights.new('ReviewSun','SUN'));s.collection.objects.link(sun);sun.data.energy=3;sun.rotation_euler=(.5,-.7,-.5)
for name,pos,target in [('side',(-1.,.08,.18),(0,-.20,.015)),('quarter',(-.6,.8,.42),(0,-.22,.02))]:
 cam.location=rt@Vector(pos);aim=rt@Vector(target);cam.rotation_euler=(aim-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/'UVRepair'/(file.stem+('_'+args[1]+'_'+args[2] if len(args)>2 else '')+'_'+name+'.png'));bpy.ops.render.render(write_still=True)
print('REVIEW_RENDER_DONE')
