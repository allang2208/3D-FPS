"""Read the original M24 motion and the rejected adaptation at bolt contact."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).resolve().parent
report={}
for family,path,rig_name,frames in [
 ('native',O.parent/'M24CustomScope20261026/M24_CustomScope_Native_Editable.blend','M24_SourceRig',[1,10,17,20,25,30,35,40,46,50]),
 ('rejected',O.parent/'M24ArmRebuild20261027/M24_ArmRebuild_Editable.blend','M24_V9_Rig',[0,9,16,19,24,29,34,39,45,49])]:
 bpy.ops.wm.open_mainfile(filepath=str(path),use_scripts=False)
 s=bpy.context.scene;r=bpy.data.objects[rig_name]
 if family=='rejected':
  a=bpy.data.actions['A_M24_fire'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 else:a=r.animation_data.action
 rest={b.name:b.matrix_local.copy() for b in r.data.bones}
 report[family]={'rig':rig_name,'fps':s.render.fps,'action':a.name,'frame_range':list(a.frame_range),
  'objects':[{'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None,'matrix':[list(v) for v in o.matrix_world]} for o in s.objects],
  'rest':{n:[list(v) for v in m] for n,m in rest.items()},'poses':{}}
 for f in range(1 if family=='native' else 0,51 if family=='native' else 56):
  s.frame_set(f);bpy.context.view_layer.update()
  report[family]['poses'][str(f)]={b.name:[list(v) for v in b.matrix] for b in r.pose.bones}
 for ob in s.objects:
  if ob.type=='MESH':
   ob.color=(.64,.69,.73,1) if 'Arms' in ob.name else (.17,.20,.23,1)
 s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_cavity=True
 if not s.world:s.world=bpy.data.worlds.new('ReferenceWorld')
 s.world.color=(.055,.065,.075);s.render.resolution_x=720;s.render.resolution_y=480;s.render.resolution_percentage=100
 s.render.image_settings.file_format='PNG';s.render.use_compositing=False;s.render.use_sequencer=False
 bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.40
 folder=O/'ReferenceFrames'/family;folder.mkdir(parents=True,exist_ok=True)
 for f in frames:
  s.frame_set(f);bpy.context.view_layer.update()
  target=r.matrix_world@r.pose.bones['WPN_BoltHandle'].matrix.translation
  direction=Vector((.30,-.13,.20))
  if family=='native':direction=Matrix.Rotation(math.pi,3,'Z')@direction
  cam.location=target+direction;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
  s.render.filepath=str(folder/(str(f)+'.png'));bpy.ops.render.render(write_still=True)
(O/'native_reference.json').write_text(json.dumps(report),encoding='utf-8')
print('NATIVE_REFERENCE_SAVED',flush=True)
