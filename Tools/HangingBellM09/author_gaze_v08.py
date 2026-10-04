"""M09 Gaze V08 authoring. Original animation and UV FX meshes, no preview/test."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector, Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003')
OUT=ROOT/'GazeV08'
for folder in ('Authoring','Exports','Audio','FX','Records'):(OUT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'RigV03/Authoring/M09_Rigged_v03.blend'))
rig=bpy.data.objects['M09_Rig_V03'];scene=bpy.context.scene;scene.render.fps=60
for p in rig.pose.bones:
 for c in list(p.constraints):p.constraints.remove(c)
 p.rotation_mode='QUATERNION'
rig.animation_data_clear();rig.animation_data_create()
action=bpy.data.actions.new('A_M09_Gaze_V08');rig.animation_data.action=action;action.use_fake_user=True
names=[b.name for b in rig.data.bones if b.use_deform]
def sm(x):
 x=max(0.,min(1.,x));return x*x*(3-2*x)
def env(t,a,b,c,d):return sm((t-a)/max(.001,b-a))*(1-sm((t-c)/max(.001,d-c)))
def rot(name,axis,angle):
 p=rig.pose.bones[name];local=rig.data.bones[name].matrix_local.to_3x3().inverted()@Vector(axis)
 p.rotation_quaternion=Quaternion(local.normalized(),math.radians(angle))@p.rotation_quaternion
scene.frame_start=1;scene.frame_end=181
for frame in range(181):
 t=frame/60
 for p in rig.pose.bones:p.location=(0,0,0);p.rotation_quaternion=(1,0,0,0);p.scale=(1,1,1)
 brace=env(t,0,.65,1.85,2.85)
 recoil=env(t,1.24,1.34,1.72,2.22)
 rot('suspension',(1,0,0),-.8*brace+.3*recoil)
 rot('spine_01',(1,0,0),2.6*brace-1.4*recoil)
 rot('spine_02',(1,0,0),-1.8*brace+.9*recoil)
 rot('crown_neck',(1,0,0),-4.5*brace+3.0*recoil)
 rot('eye_crown',(1,0,0),-2.5*brace+1.8*recoil)
 for side,sign,delay in [('L',1,0.),('R',-1,.065)]:
  opened=env(t,.02+delay,.66+delay,1.94+delay,2.94)
  # Uncross the small arms about the model-space lateral axis. All grip bones
  # remain unkeyed relative to rest; the existing hand support solver follows.
  rot('small_upperarm_'+side,(0,1,0),-sign*30*opened)
  rot('small_forearm_'+side,(0,1,0),-sign*24*opened)
  rot('small_forearm_'+side,(1,0,0),-6*opened)
  rot('small_hand_'+side,(0,0,1),sign*6*opened)
  for digit in range(1,6):
   for joint in range(1,4):rot(f'smallfinger_{side}_{digit:02d}_{joint:02d}',(1,0,0),-9*opened)
  for layer in range(1,4):
   spread=(11+layer*2)*env(t,.08+layer*.025,.70,1.9,2.9)
   for k,weight in enumerate((.44,.27,.18,.11),1):
    name=f'membrane_{side}{layer}_{k:02d}'
    rot(name,(0,1,0),-sign*spread*weight)
    rot(name,(1,0,0),(.5+.45*k)*recoil*math.sin((t-1.25)*14-layer*.3))
 # The five eye bones are neutral here: the runtime overlay eases each eye
 # toward the actual target with staggered onset and a shared lock at .90s.
 for name in names:
  for channel in ('location','rotation_quaternion','scale'):
   rig.pose.bones[name].keyframe_insert(channel,frame=frame+1,group=name)
for slot in action.slots:
 for layer in action.layers:
  for strip in layer.strips:
   bag=strip.channelbag(slot)
   if bag:
    for curve in bag.fcurves:
     for key in curve.keyframe_points:key.interpolation='LINEAR'
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'Exports/A_M09_Gaze_V08.fbx'),use_selection=True,
 object_types={'ARMATURE'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',
 bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,
 add_leaf_bones=False,use_armature_deform_only=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M09_Gaze_V08.blend'),compress=True)
print('M09_GAZE_ANIMATION_SAVED',flush=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
def export_mesh(name,verts,faces,uvs):
 bpy.ops.object.select_all(action='DESELECT')
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
 layer=mesh.uv_layers.new(name='GazeUV')
 for poly in mesh.polygons:
  for li in poly.loop_indices:layer.data[li].uv=uvs[mesh.loops[li].vertex_index]
 ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
 bpy.context.view_layer.objects.active=ob;ob.select_set(True)
 bpy.ops.export_scene.fbx(filepath=str(OUT/'FX'/(name+'.fbx')),use_selection=True,object_types={'MESH'},
  axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False,mesh_smooth_type='FACE')
 return ob
# Three intersecting soft ribbons: authored 100 cm long, 1 cm half-width.
# UV.x is across the ribbon; UV.y runs from source to target along local +Z.
verts=[];faces=[];uvs=[]
for plane in range(3):
 theta=math.pi*plane/3
 start=len(verts)
 for row in range(17):
  for side in (-1,1):
   verts.append((.01*side*math.cos(theta),.01*side*math.sin(theta),row/16-.5))
   uvs.append(((side+1)/2,row/16))
 for row in range(16):
  a=start+row*2;faces.append((a,a+1,a+3,a+2))
export_mesh('SM_M09_GazeRibbon_V08',verts,faces,uvs)
# Convex iris veil: 1 cm radius, follows each actual eye bone at runtime.
verts=[(0,0,.003)];uvs=[(.5,.5)];faces=[]
for ring in range(1,5):
 radius=ring/4
 for segment in range(32):
  a=2*math.pi*segment/32;x=radius*math.cos(a);y=radius*math.sin(a)
  verts.append((.01*x,.01*y,.003*(1-radius*radius)));uvs.append((.5+.5*x,.5+.5*y))
for i in range(32):faces.append((0,1+i,1+(i+1)%32))
for ring in range(3):
 for i in range(32):
  a=1+ring*32+i;b=1+ring*32+(i+1)%32;faces.append((a,a+32,b+32,b))
export_mesh('SM_M09_IrisVeil_V08',verts,faces,uvs)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M09_GazeFX_V08.blend'))
(OUT/'Records/motion_manifest.json').write_text(json.dumps({'version':'V08','duration':3.,'fps':60,'frames':181,
 'lock':.9,'fire':[1.25,1.85],'damage_pulses':[1.25,1.45,1.65],
 'provenance':'Original local organ animation and FX mesh authoring; V03 rig reused',
 'root_motion':False,'tested':False,'eye_aim':'Five actual eye bones; runtime staged aim and recovery',
 'geometry_units':'Ribbon +/-50cm Z, radius 1cm; iris radius 1cm after UE import'},indent=2),encoding='utf8')
print('M09_GAZE_FX_SAVED',flush=True)
