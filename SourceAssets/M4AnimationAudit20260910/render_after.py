import bpy,math,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
for o in s.objects:o.hide_render=o.type!='MESH' or o.parent!=r
s.world.color=(.10,.10,.10)
for pos in [(-.7,-.3,.8),(.8,.5,.8)]:
 d=bpy.data.lights.new('Review','AREA');d.energy=95;d.size=1;o=bpy.data.objects.new('Review',d);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,.2,-.1))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('ReviewCam');cam=bpy.data.objects.new('ReviewCam',d);s.collection.objects.link(cam);s.camera=cam;d.clip_start=.005
s.render.engine='BLENDER_EEVEE';s.eevee.taa_render_samples=12;s.render.resolution_x=640;s.render.resolution_y=480;s.render.resolution_percentage=100
continuous='--continuous' in sys.argv
for clip,fs in [('reload',[64,76,95]),('reload_empty',[12,21,28,54,80,130]),('equip_charge',[12,18,24])]:
 for version in ['M4_MAT_']:
  a=bpy.data.actions[version+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
  if continuous:fs=range(0,round(a.frame_range[1])+1,2)
  for f in fs:
   s.frame_set(f);bpy.context.view_layer.update()
   side='r' if clip=='equip_charge' else 'l';focus=r.pose.bones['hand_'+side].head.copy();focus+=Vector((0,0,.025))
   for view in (['fps'] if continuous else ['fps','palm']):
    if view=='fps':
     d.type='PERSP';d.lens_unit='FOV';d.angle=math.radians(90);cam.location=(-.07,-.10,.07);cam.rotation_euler=(math.pi/2,0,0)
    else:
     d.type='ORTHO';d.ortho_scale=.33;cam.location=focus+Vector((-.35,-.3,.25) if side=='l' else (.35,-.3,.25));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler()
    folder=O/('Frames' if continuous else 'ReviewAfter')/(version+clip)/view;folder.mkdir(parents=True,exist_ok=True)
    s.render.filepath=str(folder/f'{f:03}.png');bpy.ops.render.render(write_still=True)
print('RENDER_DONE')
