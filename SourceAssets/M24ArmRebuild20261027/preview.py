import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_ArmRebuild_Editable.blend'),use_scripts=False)
r=bpy.data.objects['M24_V9_Rig'];skin=bpy.data.objects['M24_V9_BareArms'];s=bpy.context.scene
rest={b.name:b.matrix_local for b in r.data.bones}
C=Matrix(json.loads((O.parent/'M24Hold20261027/hip-calibration.json').read_text())['hip_transform'])@Matrix.Diagonal((100,-100,100,1))
def angle(a,b):return math.degrees(a.angle(b))
def clamp(x):return min(1,max(0,x))
def tent(x,a,b,c):return clamp((x-a)/(b-a)) if x<=b else clamp((c-x)/(c-b))
def morphs():
 row={b.name:b.matrix for b in r.pose.bones};keys=skin.data.shape_keys.key_blocks
 for k in keys:k.value=0
 for side in ('l','r'):
  u,l,h=[x+'_'+side for x in ('upperarm','lowerarm','hand')];tw='lowerarm_twist_01_'+side
  U=row[l].translation-row[u].translation;F=row[h].translation-row[l].translation
  R0=rest[l].translation-rest[u].translation;F0=rest[h].translation-rest[l].translation
  elbow=angle(U,F);re=angle(R0,F0)
  f0=(rest['middle_01_'+side].translation-rest[h].translation).normalized()
  r0=rest['index_metacarpal_'+side].translation-rest['pinky_metacarpal_'+side].translation;r0=(r0-f0*r0.dot(f0)).normalized();z0=f0.cross(r0)
  q=rest[tw].to_quaternion().inverted();f0=q@f0;r0=q@r0;z0=q@z0
  direction=row[tw].to_quaternion().inverted()@(row['middle_01_'+side].translation-row[h].translation).normalized()
  flex=math.degrees(math.atan2(-direction.dot(z0),direction.dot(f0)));dev=math.degrees(math.atan2(direction.dot(r0),direction.dot(f0)))
  values={'JC_ElbowFlex75':tent(elbow,re,75,110),'JC_ElbowFlex110':tent(elbow,75,110,135),'JC_ElbowFlex135':clamp((elbow-110)/25),'JC_ElbowFlex20':clamp((re-elbow)/(re-20)),
   'JC_WristFlexA':clamp(flex/40),'JC_WristFlexB':clamp(-flex/40),'JC_WristRadial':clamp(dev/20),'JC_WristUlnar':clamp(-dev/35)}
  for k,v in values.items():
   n=k+'_'+side.upper()
   if n in keys:keys[n].value=v
 bpy.context.view_layer.update()
def pose(role,f):
 a=bpy.data.actions['A_M24_'+role];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update();morphs()
for ob in s.objects:
 if ob.type=='MESH':ob.color=(.63,.69,.76,1) if ob==skin else (.16,.19,.22,1)
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_cavity=True
s.world=bpy.data.worlds.new('Joint review');s.world.color=(.05,.06,.08)
s.render.resolution_x=960;s.render.resolution_y=540;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.use_compositing=False;s.render.use_sequencer=False
bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=24;cam.data.lens=24/(2*math.tan(math.radians(75/2)));cam.data.clip_start=.01
cs=Matrix(((0,.01,0,0),(.01,0,0,0),(0,0,.01,0),(0,0,0,1)))
for name,role,f,view in [('idle','aim',0,'game'),('bolt','fire',28,'bolt'),('bolt_game','fire',28,'game'),('left_elbow','aim',0,'left'),('sprint_enter','sprint_enter',6,'game'),('reload_elbow','reload',33,'left')]:
 pose(role,f);r.matrix_world=Matrix.Identity(4)
 if view=='game':
  r.matrix_world=cs@C;cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0);cam.data.type='PERSP'
 else:
  target=r.pose.bones['WPN_BoltHandle' if view=='bolt' else 'lowerarm_l'].matrix.translation
  cam.location=target+Vector((.28,-.12,.20) if view=='bolt' else (-.32,-.20,.15));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.4
 s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
