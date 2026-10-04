"""Author only M09 Resonance V07. Preserve V03 skin and accepted V05 locomotion."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector, Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003')
OUT=ROOT/'ResonanceV07'
for folder in ('Authoring','Exports','Audio','FX','Records'):(OUT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'RigV03/Authoring/M09_Rigged_v03.blend'))
rig=bpy.data.objects['M09_Rig_V03'];scene=bpy.context.scene;scene.render.fps=60
for p in rig.pose.bones:
 for c in list(p.constraints):p.constraints.remove(c)
 p.rotation_mode='QUATERNION'
rig.animation_data_clear();rig.animation_data_create()
action=bpy.data.actions.new('A_M09_Resonance_V07');rig.animation_data.action=action;action.use_fake_user=True
names=[b.name for b in rig.data.bones if b.use_deform]
def sm(x):
 x=max(0.,min(1.,x));return x*x*(3-2*x)
def env(t,a,b,c,d):return sm((t-a)/max(.001,b-a))*(1-sm((t-c)/max(.001,d-c)))
def rot(name,axis,angle):
 p=rig.pose.bones[name];local=rig.data.bones[name].matrix_local.to_3x3().inverted()@Vector(axis)
 p.rotation_quaternion=Quaternion(local.normalized(),math.radians(angle))@p.rotation_quaternion
pulses=(1.10,1.80,2.50,3.20,3.90,4.60)
scene.frame_start=1;scene.frame_end=337
for frame in range(337):
 t=frame/60
 for p in rig.pose.bones:p.location=(0,0,0);p.rotation_quaternion=(1,0,0,0);p.scale=(1,1,1)
 brace=env(t,.01,.14,4.74,5.6)
 recoil=sum(env(t,p-.065,p,p+.035,p+.23) for p in pulses)
 # Small torso tension and recoil. No root movement, scaling or support release.
 rot('suspension',(1,0,0),-1.1*brace+.55*recoil)
 rot('spine_01',(1,0,0),3.8*brace-2.8*recoil)
 rot('spine_02',(1,0,0),-2.1*brace+1.5*recoil)
 rot('crown_neck',(1,0,0),-2.4*brace+.8*recoil)
 rot('eye_crown',(1,0,0),1.2*brace-.6*recoil)
 for side,sign,delay in [('L',1,0.),('R',-1,0.)]:
  # Crossed small arms brace the organ; big hand pose stays available to runtime IK.
  rot('small_upperarm_'+side,(0,1,0),sign*5.5*brace)
  rot('small_forearm_'+side,(1,0,0),-4.0*brace+1.5*recoil)
  rot('small_hand_'+side,(0,0,1),sign*3*brace)
  for digit in range(1,6):
   for joint in range(1,4):rot(f'smallfinger_{side}_{digit:02d}_{joint:02d}',(1,0,0),7*brace)
  for layer in range(1,4):
   layer_pulses=(pulses[layer-1],pulses[layer+2])
   # User request: all three pairs snap open together at the attack start.
   opening=env(t,0.,.12,4.82+(layer-1)*.08,5.42+(layer-1)*.09)
   compression=sum(env(t,p-.15,p-.055,p-.025,p+.015) for p in layer_pulses)
   release=sum(env(t,p-.02,p+.04,p+.085,p+.25) for p in layer_pulses)
   spread=(38+2*layer)*opening-9*compression+8*release
   for k,weight in enumerate((.44,.27,.18,.11),1):
    name=f'membrane_{side}{layer}_{k:02d}'
    rot(name,(0,1,0),-sign*spread*weight)
    rot(name,(1,0,0),(-1.0 if layer==1 else .8)*opening*weight)
    ring=0.
    for pulse in layer_pulses:
     age=t-pulse-(k-1)*.016
     if age>=0:ring+=math.sin(2*math.pi*7.5*age)*math.exp(-age*9)*sm(age/.025)
    # Flex travels from anchored base to tip; amplitude bounded to three degrees.
    rot(name,(1,0,0),ring*(.25,.9,1.8,2.8)[k-1])
    rot(name,(0,1,0),-sign*ring*(.15,.5,.9,1.3)[k-1])
 for name in names:
  p=rig.pose.bones[name]
  for channel in ('location','rotation_quaternion','scale'):p.keyframe_insert(channel,frame=frame+1,group=name)
# Keep baked keys linear so short release beats cannot overshoot between samples.
for slot in action.slots:
 for layer in action.layers:
  for strip in layer.strips:
   bag=strip.channelbag(slot)
   if bag:
    for curve in bag.fcurves:
     for key in curve.keyframe_points:key.interpolation='LINEAR'
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
fbx=OUT/'Exports/A_M09_Resonance_V07.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},apply_unit_scale=True,
 apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',bake_anim=True,
 bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,
 add_leaf_bones=False,use_armature_deform_only=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M09_Resonance_V07.blend'),compress=True)
manifest={'version':'V07','source_rig':'RigV03','clip':str(fbx),'duration':5.6,'fps':60,'frames':337,
 'pulses_seconds':pulses,'direction_lock_seconds':.8,'loop':False,'root_motion':False,
 'authoring':'All three membrane pairs open in .12s; two rounds of three pulses; hand support remains runtime IK',
 'tested':False,'accepted_baseline':'User confirmed V05 spawn and ceiling movement on 2026-10-03'}
(OUT/'Records/motion_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print('M09_RESONANCE_MOTION_SAVED',flush=True)
# A continuous spherical veil replaces the three narrow, closed white rings.
bpy.ops.wm.read_factory_settings(use_empty=True)
verts=[];faces=[];uvs=[]
rows=24;segments=96
for row in range(rows+1):
 theta=math.radians(50)*row/rows
 for col in range(segments+1):
  phi=2*math.pi*col/segments
  # Slight physical corrugation; opacity feathering owns the visible boundary.
  r=1.-.025*math.sin(theta*4)**2*(1+math.sin(phi*3+theta*5))
  verts.append((r*math.sin(theta)*math.cos(phi),r*math.sin(theta)*math.sin(phi),r*math.cos(theta)))
  uvs.append((col/segments,row/rows))
for row in range(rows):
 for col in range(segments):
  a=row*(segments+1)+col
  faces.append((a,a+segments+2,a+segments+1) if row==0 else (a,a+1,a+segments+2,a+segments+1))
mesh=bpy.data.meshes.new('M09_PressureVeil');mesh.from_pydata(verts,[],faces);mesh.update()
uv=mesh.uv_layers.new(name='PressureUV')
for poly in mesh.polygons:
 poly.use_smooth=True
 for li in poly.loop_indices:uv.data[li].uv=uvs[mesh.loops[li].vertex_index]
obj=bpy.data.objects.new('SM_M09_ResonanceWave_V07',mesh);bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT/'FX/SM_M09_ResonanceWave_V07.fbx'),use_selection=True,
 object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_anim=False,mesh_smooth_type='FACE')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M09_ResonanceWave_V07.blend'))
print('M09_RESONANCE_V07_FX_SAVED',flush=True)
