import bpy,math,json
from pathlib import Path
from mathutils import Matrix,Vector
OUT=Path(__file__).resolve().parent
def setup():
 bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910/M4_HK416_Drum_Editable.blend')
 r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
 with bpy.data.libraries.load('D:/FPS3D/FPSGAME/SourceAssets/M4Drum20260909/M4_Drum_Optimized.blend',link=False) as (a,b):b.objects=['SM_M4_LargeDrum']
 drum=b.objects[0];s.collection.objects.link(drum);drum.parent=r;drum.matrix_parent_inverse=Matrix.Identity(4);drum.matrix_basis=Matrix.Identity(4)
 for mod in drum.modifiers:
  if mod.type=='ARMATURE':mod.object=r
 for o in s.objects:
  o.hide_render=o.type not in {'MESH'} or o.parent!=r
  if 'Magazine' in o.name:o.hide_render=True
 s.world.color=(.16,.16,.16)
 camdata=bpy.data.cameras.new('DrumGripReview');cam=bpy.data.objects.new('DrumGripReview',camdata);s.collection.objects.link(cam);s.camera=cam;cam.hide_render=False;camdata.clip_start=.005
 for pos in [(-.7,-.3,.8),(.8,.5,.8)]:
  ld=bpy.data.lights.new('GripLight','AREA');ld.energy=95;ld.size=1;ob=bpy.data.objects.new('GripLight',ld);s.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,.2,-.1))-ob.location).to_track_quat('-Z','Y').to_euler()
 s.render.engine='BLENDER_EEVEE';s.render.resolution_x=900;s.render.resolution_y=700;s.render.resolution_percentage=100
 return r,s,drum
def render(r,s,f,path):
 s.frame_set(f);bpy.context.view_layer.update();cam=s.camera
 focus=r.pose.bones['WPN_SOCKET_Magazine'].head
 cam.data.type='ORTHO';cam.data.ortho_scale=.48
 cam.location=focus+Vector((.5,-.3,.12));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler()
 s.render.filepath=str(path);bpy.ops.render.render(write_still=True)
if __name__=='__main__':
 r,s,d=setup()
 for name,frames in [('A_M4_HK416_drum_reload',[15,29,76,95]),('A_M4_HK416_drum_reload_empty',[21,54,80,130])]:
  a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
  for f in frames:render(r,s,f,OUT/f'before_{name}_{f}.png')
