"""Requested asset/hand previews, rendered from the editable export source."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(O/'PKM_Gameplay_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['PKM_Manny_Rig'];a=bpy.data.actions['PKM_Game_idle']
r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix']);W=r.pose.bones['WPN_root'].matrix@fit
s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type=='OPTIX'
if any(d.use for d in prefs.devices):s.cycles.device='GPU'
s.render.resolution_x=1600;s.render.resolution_y=900;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('PKM07Studio');s.world.use_nodes=True
s.world.node_tree.nodes['Background'].inputs[0].default_value=(.06,.075,.095,1)
s.world.node_tree.nodes['Background'].inputs[1].default_value=.5
s.view_settings.view_transform='AgX';s.view_settings.exposure=-.15
def aim(o,p):o.rotation_euler=(p-o.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('PKM07Camera',bpy.data.cameras.new('PKM07Camera'));s.collection.objects.link(cam);s.camera=cam
for name,power,pos,size in [('Key',80,(.3,-.15,.75),.65),('Fill',35,(-.6,.1,.4),1.2),('Rim',60,(0,-.5,.6),.65)]:
 o=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));s.collection.objects.link(o);o.location=W@Vector(pos);o.data.energy=power;o.data.size=size;aim(o,W@Vector((0,0,0)))
def visibility(hands,bipod):
 for ob in s.objects:
  if ob.type!='MESH':continue
  visible=('mechanical_bone' in ob and not ob.name.startswith('New_')) or (hands and ob.name=='SK_Manny_Arms_Export') or (bipod and ob.get('attachment_id')=='pkm_bipod')
  if ob.get('source_part_id') in [65,72,127,128,129]:visible=bipod
  ob.hide_render=not visible
  if visible:ob.hide_set(False)
def shot(name,pos,target,ortho=None):
 cam.location=W@Vector(pos);aim(cam,W@Vector(target));cam.data.type='ORTHO' if ortho else 'PERSP';cam.data.lens=48
 if ortho:cam.data.ortho_scale=ortho
 s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
visibility(False,False);shot('PKM_07_NoBipod',(1.4,.80,.55),(0,-.025,-.012),1.38)
visibility(False,True);shot('PKM_07_WithBipod',(1.4,.80,.55),(0,-.025,-.012),1.38)
visibility(True,False);shot('PKM_07_IdleGrip',(.34,.48,.24),(0,.015,-.025))
shot('PKM_07_GripUnderside',(.45,.22,-.23),(0,-.095,.005))
visibility(False,False);shot('PKM_07_MetalClose',(.29,.36,.25),(0,.11,.055))
print('PKM07_REQUESTED_RENDERS_COMPLETE',flush=True)
