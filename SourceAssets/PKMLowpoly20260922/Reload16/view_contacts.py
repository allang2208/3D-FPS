"""Focused source-pose images for the user's elbow/contact diagnosis, not PIE."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(O/'PKM_base_Reload_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['PKM_Manny_Rig'];fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.get_devices()
for device in pref.devices:device.use=device.type=='OPTIX'
s.cycles.device='GPU';s.render.resolution_x=960;s.render.resolution_y=720;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('PKM16ContactWorld');s.world.use_nodes=True
background=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND');background.inputs[0].default_value=(.09,.09,.09,1);background.inputs[1].default_value=.55
s.view_settings.view_transform='AgX';s.view_settings.exposure=0
cam=bpy.data.objects.new('ContactCamera',bpy.data.cameras.new('ContactCamera'));s.collection.objects.link(cam);s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.53
def aim(ob,p):ob.rotation_euler=(p-ob.location).to_track_quat('-Z','Y').to_euler()
lights=[]
for name,energy,pos,size in [('Key',70,(.3,.3,.5),.7),('Fill',45,(-.4,.3,.4),.8)]:
 ob=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));s.collection.objects.link(ob);ob.data.energy=energy;ob.data.size=size;lights.append((ob,Vector(pos)))
for label,action,frame,side in [('belt_before','PKM_Reload_Normal_HandReload10_Wrist12',99,'l'),('belt_after','PKM16_base_reload',198,'l'),('charge_after','PKM16_base_reload_empty',630,'r')]:
 a=bpy.data.actions[action];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(frame);bpy.context.view_layer.update();W=r.pose.bones['WPN_root'].matrix@fit
 for ob in s.objects:
  if ob.type!='MESH':continue
  show=('mechanical_bone' in ob and not ob.name.startswith('New_')) or ob.name=='SK_Manny_Arms_Export'
  if ob.get('source_part_id') in [65,72,127,128,129]:show=False
  if label=='charge_after' and ob.name.startswith('New_'):show=True
  if label=='charge_after' and ob.get('mechanical_bone') in ['PKM_Box','PKM_BoxLid','PKM_BeltRoot']:show=False
  ob.hide_render=not show
  if show:ob.hide_set(False)
 target=r.pose.bones['hand_'+side].head.lerp(r.pose.bones['lowerarm_'+side].head,.43) if side=='l' else r.pose.bones['hand_r'].head.lerp(r.pose.bones['PKM_Charge'].head,.5)
 cam.location=target+W.to_3x3()@Vector((.5 if side=='l' else -.48,.19,.16));aim(cam,target)
 for light,pos in lights:light.location=W@pos;aim(light,target)
 s.render.filepath=str(O/(label+'.png'));bpy.ops.render.render(write_still=True)
 print('PKM16_SOURCE_CONTACT',label,flush=True)
