import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent
out={}
def setup():
 sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.render.resolution_x=720;sc.render.resolution_y=540;sc.render.resolution_percentage=100
 sh=sc.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='WORLD';sc.world.color=(.13,.13,.13)
 sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
 for o in list(sc.objects):
  if o.type not in ('MESH','ARMATURE'):bpy.data.objects.remove(o,do_unlink=True)
 bpy.ops.object.camera_add();sc.camera=bpy.context.object
 return sc
def render(sc,name,center,offset,scale):
 c=sc.camera;c.location=center+Vector(offset);c.rotation_euler=(center-c.location).to_track_quat('-Z','Y').to_euler();c.data.type='ORTHO';c.data.ortho_scale=scale
 sc.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
for family in ['base','vertical']:
 file=S/'M16Gameplay20260919/M16_Manny_Editable.blend' if family=='base' else S/'M16UniversalAttachments20260920/M16_vertical_Animations_Editable.blend'
 bpy.ops.wm.open_mainfile(filepath=str(file),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];sc=setup()
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=not(o.name=='SK_Manny_Arms_Export' or o.name.startswith('M16A2_'))
 for kind,frames in [('reload',[54,80,100]),('reload_empty',[96,125])]:
  name='M16_'+(family+'_' if family!='base' else '')+kind;a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
  for f in frames:
   sc.frame_set(f);bpy.context.view_layer.update();h=r.matrix_world@r.pose.bones['hand_l'].matrix
   center=h@Vector((0,.045,0));render(sc,f'{family}_{kind}_{f}',center,(.20,.16,.12),.24)
   vals={}
   for b in r.pose.bones:
    if b.name.startswith(('index','middle','ring','pinky','thumb')):
     vals[b.name]={'local_location':list(b.location),'scale':list(b.scale),'rotation':list(b.rotation_quaternion)}
   out[family+kind+str(f)]=vals
 if family=='base':
  r.animation_data.action=bpy.data.actions['M16_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];sc.frame_set(0);bpy.context.view_layer.update()
  W=r.matrix_world@r.pose.bones['WPN_root'].matrix
  out['root_world']=[list(row) for row in W]
  for o in sc.objects:
   if o.type=='MESH' and o.name.startswith('SK_Manny'):o.hide_render=True
  render(sc,'receiver_before',W@Vector((0,-.045,.085)),W.to_3x3()@Vector((.4,.15,.13)),.35)
  dg=bpy.context.evaluated_depsgraph_get();out['parts']={}
  for n in ['M16A2_Receiver','M16A2_PistolGrip']:
   o=bpy.data.objects[n];ev=o.evaluated_get(dg);me=ev.to_mesh();out['parts'][n]={'vertices':[list(W.inverted()@o.matrix_world@v.co) for v in me.vertices],'faces':[list(p.vertices) for p in me.polygons]};ev.to_mesh_clear()
(O/'blender_inspection.json').write_text(json.dumps(out))
print('M16_BLENDER_INSPECTION_SAVED',flush=True)
