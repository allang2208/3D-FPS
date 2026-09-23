"""Targeted user-requested cover/box inspection and two source renders."""
import bpy,json,pathlib,math
from mathutils import Vector,Matrix
O=pathlib.Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'Integration04/PKM_Gameplay_Editable.blend'))
r=bpy.data.objects['PKM_Manny_Rig'];s=bpy.context.scene
def setclip(name,frame):
 a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(frame);bpy.context.view_layer.update()
# Compare every closed control to its parent-relative bind pose, not Euler guesses.
report={}
for clip,frames in [('PKM_Game_idle',[0,30,60]),('PKM_Reload_Normal',[0,78,390]),('PKM_Reload_Empty',[0,78,450])]:
 for f in frames:
  setclip(clip,f);row={}
  for name in ['PKM_Cover','PKM_Box','PKM_BoxLid','New_PKM_Box','New_PKM_BoxLid']:
   b=r.pose.bones[name];row[name]={'translation_m':list(b.location),'rotation_degrees':math.degrees(b.rotation_quaternion.angle),'scale':list(b.scale)}
  report[clip+':'+str(f)]=row
(O/'source_pose_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for ob in s.objects:
 ob.hide_render=ob.type not in ['MESH'] or ob.name=='SK_Manny_Arms_Export' or ob.name.startswith('New_') or 'mechanical_bone' not in ob
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=24;s.cycles.use_denoising=True
s.render.resolution_x=1024;s.render.resolution_y=768;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('PKM_CheckWorld');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.11,.13,.17,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.5
def aim(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
target=Vector((.045,.22,-.075))
cam=bpy.data.objects.new('PKM_CheckCamera',bpy.data.cameras.new('PKM_CheckCamera'));s.collection.objects.link(cam);cam.location=(1.0,-.62,.63);aim(cam,target);cam.data.type='ORTHO';cam.data.ortho_scale=.95;s.camera=cam
for name,pos,power,size in [('Key',(.4,-.4,1.5),120,2),('Fill',(-1,.3,.5),80,1.5),('Rim',(.3,1.5,.8),130,1)]:
 light=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));s.collection.objects.link(light);light.location=pos;light.data.energy=power;light.data.shape='DISK';light.data.size=size;aim(light,target)
for clip,frame,name in [('PKM_Game_idle',0,'idle_closed'),('PKM_Reload_Normal',78,'reload_open')]:
 setclip(clip,frame);s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
print('PKM_TARGETED_POSE_CHECK_COMPLETE')
