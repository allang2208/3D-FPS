"""Produce the required gunsmith icons from the final baked model, without PIE."""
import bpy,json,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parents[1];D=O/'Icons';D.mkdir(exist_ok=True)
frames=json.loads((O/'Reference/author_frames.json').read_text())
ref=json.loads((O.parent/'AttachmentIconAudit20260914/frame_reference.json').read_text())
rear=Matrix(ref['rear_sight_matrix']);front=Matrix(ref['front_sight_matrix'])
z=rear.to_3x3().col[2].normalized();f=front.translation-rear.translation;f-=z*f.dot(z);f.normalize()
x=-f;y=z.cross(x).normalized();z=x.cross(y).normalized()
level=Matrix(((*x,0),(*y,0),(*z,0),(0,0,0,1)))
frame=level@Matrix(frames['M4']['canonical_to_source']);frame.translation=(0,0,0)
guns=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['M4','AKM','QBZ191']
for gun in guns:
 bpy.ops.wm.open_mainfile(filepath=str(O/gun/'Drum_Editable.blend'))
 ob=bpy.data.objects['SM_'+gun+'_LargeDrum_Upgrade']
 for other in list(bpy.data.objects):
  if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
 ob.hide_set(False);ob.hide_render=False;ob.data.transform(frame)
 pts=[v.co for v in ob.data.vertices];lo=Vector([min(v[i] for v in pts) for i in range(3)]);hi=Vector([max(v[i] for v in pts) for i in range(3)])
 center=(lo+hi)*.5;scale=2/max(hi.x-lo.x,hi.z-lo.z)
 ob.matrix_world=Matrix.Scale(scale,4)@Matrix.Translation(-center)
 s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=48;s.cycles.use_denoising=True
 s.render.threads_mode='FIXED';s.render.threads=8
 s.render.resolution_x=1024;s.render.resolution_y=1024;s.render.resolution_percentage=100
 s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
 s.render.use_compositing=False;s.render.use_sequencer=False;s.render.use_border=False
 s.view_settings.view_transform='AgX';s.view_settings.exposure=.35
 s.world=bpy.data.worlds.new('DrumIconStudio');s.world.use_nodes=True
 bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.36,.36,.36,1);bg.inputs[1].default_value=.55
 for loc,energy,size in [((-1.5,-3,3),700,4),((2,1.5,2.5),950,3),((-3,-1,-.5),180,2),((0,-4,.2),110,3)]:
  bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=energy;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
 bpy.ops.object.camera_add(location=(0,-5,0));cam=bpy.context.object;cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=2.36;s.camera=cam
 s.render.filepath=str(D/(gun+'_magazine_large_drum.png'))
 bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(D/(gun+'_DrumIcon_Editable.blend')))
 bpy.ops.render.render(write_still=True)
 (D/(gun+'_icon_receipt.json')).write_text(json.dumps({'gun':gun,'source':str(O/gun/'Drum_Editable.blend'),
  'output':s.render.filepath,'source_frame':'Common shell frame recovered from original meshes; front/up from M4 sight frame',
  'format':'1024x1024 RGBA transparent','front':'left','up':'+Z','renderer':'Blender Cycles CPU, AgX, 48 samples',
  'game_tested':False},indent=2),encoding='utf-8')
 print('DRUM_ICON_RENDERED',gun,flush=True)
