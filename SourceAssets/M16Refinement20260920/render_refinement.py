import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;S=O.parent;mode=sys.argv[-1]
def scene():
 s=bpy.context.scene
 if not s.world:s.world=bpy.data.worlds.new('ReviewWorld')
 for o in list(s.objects):
  if o.type not in ['MESH','ARMATURE']:bpy.data.objects.remove(o,do_unlink=True)
 s.render.engine='BLENDER_WORKBENCH';sh=s.display.shading;sh.light='STUDIO';sh.color_type='OBJECT';sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD';s.world.color=(.15,.15,.15)
 s.render.resolution_x=800;s.render.resolution_y=650;s.render.resolution_percentage=100;s.render.film_transparent=False;s.render.image_settings.file_format='PNG';s.render.use_compositing=False;s.render.use_sequencer=False
 bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.data.type='ORTHO';return s
def shot(s,name,target,offset,scale):
 c=s.camera;c.location=target+Vector(offset);c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();c.data.ortho_scale=scale;s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
if mode=='hands':
 for state in ['before','after']:
  for clip,frame in [('reload',61),('reload',76),('reload_empty',54)]:
   file=S/'M16Gameplay20260919/M16_Manny_Editable.blend' if state=='before' else O/'Animations/base'/('A_M16_'+clip+'.blend')
   bpy.ops.wm.open_mainfile(filepath=str(file),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['M16_'+clip] if state=='before' else bpy.data.actions['M16_Refined_base_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s=scene();s.frame_set(frame);bpy.context.view_layer.update()
   for o in s.objects:
    if o.type=='MESH':o.hide_render=o.name not in ['SK_Manny_Arms_Export','M16A2_Magazine'];o.hide_set(False);o.color=(.28,.45,.6,1) if o.name.startswith('SK_Manny') else (.60,.4,.15,1)
   pts={n:r.matrix_world@r.pose.bones[n].matrix.translation for n in ['hand_l','index_01_l','pinky_01_l','middle_02_l']};normal=(pts['index_01_l']-pts['hand_l']).cross(pts['pinky_01_l']-pts['hand_l']).normalized();center=(pts['hand_l']+pts['middle_02_l'])/2
   for sign,view in [(1,'palm'),(-1,'back')]:shot(s,f'{state}_{clip}_{frame}_{view}',center,normal*.3*sign+Vector((.03,.015,.02)),.21)
else:
 I=json.loads((O/'blender_inspection.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(O/'M16_Interfaces_Editable.blend'),use_scripts=False);s=scene()
 for o in s.objects:
  if o.type=='MESH':o.hide_render=True
 me=bpy.data.meshes.new('ReceiverReference');p=I['parts']['M16A2_Receiver'];me.from_pydata(p['vertices'],[],p['faces']);rec=bpy.data.objects.new('ReceiverReference',me);s.collection.objects.link(rec);rec.color=(.18,.2,.22,1)
 optics=bpy.data.objects['SM_M16_holographic'];optics.hide_render=False;optics.hide_set(False);optics.color=(.29,.32,.35,1);mount=Matrix.Rotation(-math.pi/2,4,'Z');mount.translation=Vector((-.000038,-.105,.1815));optics.matrix_world=mount
 grip=bpy.data.objects.get('SM_M16_balanced_reargrip') or bpy.data.objects['SM_M16_balanced_reargrip.001'];grip.hide_set(False);grip.hide_render=False;grip.color=(.3,.32,.34,1)
 shot(s,'fitted_mount_side',Vector((0,-.105,.173)),(.34,.07,.08),.27)
 shot(s,'fitted_mount_rear',Vector((0,-.105,.167)),(.13,.32,.075),.25)
 shot(s,'balanced_grip_interface',Vector((0,.008,.006)),(.28,.09,.04),.15)
 # Assign diagnostic glass colour only for reading which surfaces were separated.
 s.display.shading.color_type='MATERIAL'
 for mat in optics.data.materials:mat.diffuse_color=(.05,.5,.8,1) if 'Glass' in mat.name else (.2,.22,.24,1)
 shot(s,'holo_window_surfaces',mount@Vector((-.015,0,.051)),(.02,.28,.016),.10)
print('M16_REFINEMENT_RENDERED',mode,flush=True)
