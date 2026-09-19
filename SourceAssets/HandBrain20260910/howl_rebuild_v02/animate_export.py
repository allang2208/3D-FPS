import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector,Quaternion
R=Path(__file__).resolve().parent;out=R/'delivery';out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'SingleFace_Rig.blend'))
scene=bpy.context.scene;scene.render.fps=30;rig=bpy.data.objects['SK_HandBrain']
mouth=[p for p in rig.pose.bones if p.name.startswith('mouth_')]
def assign(a):
 rig.animation_data.action=a
 if a.slots:rig.animation_data.action_slot=a.slots[0]
def reset():
 for p in rig.pose.bones:p.matrix_basis.identity();p.rotation_mode='QUATERNION'
 rig.pose.bones['arm_mount'].scale=(.055,)*3;rig.pose.bones['fan_mount'].scale=(.06,)*3
def key(p,f):
 for ch in ['location','rotation_quaternion','scale']:p.keyframe_insert(ch,frame=f)
def rotate(name,axis,degrees):
 p=rig.pose.bones[name];q=p.bone.matrix_local.to_quaternion()
 p.rotation_quaternion=q.inverted()@Quaternion(axis,math.radians(degrees))@q
def interp(t,keys):
 for (a,x),(b,y) in zip(keys,keys[1:]):
  if t<=b:
   q=max(0,min(1,(t-a)/(b-a)));q=q*q*(3-2*q);return x+(y-x)*q
 return keys[-1][1]
# Add only neutral channels for the new bones to the three existing actions.
for name,end in [('Idle',61),('Move',31),('Attack_Slam',61)]:
 a=bpy.data.actions[name];assign(a)
 for p in mouth:
  p.matrix_basis.identity();p.rotation_mode='QUATERNION';key(p,1);key(p,end)
a=bpy.data.actions.new('Attack_Howl');a.use_fake_user=True;assign(a)
for f in range(1,92):
 t=(f-1)/30;reset()
 amount=interp(t,[(0,0),(.08,0),(.25,.18),(.48,.65),(.82,1),(1.8,1),(2.18,.52),(2.62,0),(3,0)])
 tremor=amount*(.009*math.sin(2*math.pi*5*t)) if .82<t<1.8 else 0
 for part,vec in {'jaw':(-.05,0,-.31),'upper':(.006,0,.11),'cheek_L':(0,.105,0),'cheek_R':(0,-.105,0)}.items():
  for parent in ['base','neck','cranium']:
   p=rig.pose.bones['mouth_'+part+'_'+parent]
   amt=amount+tremor if part=='jaw' else amount
   p.location=p.bone.matrix_local.to_quaternion().inverted()@(Vector(vec)*amt)
 rotate('cranium',(0,1,0),-4.5*amount)
 rotate('neck',(0,1,0),1.2*amount)
 for j in range(8):
  angle=j*math.tau/8
  rotate(f'crown_{j:02}',(-math.sin(angle),math.cos(angle),0),amount*(7+2*math.sin(angle)))
 for p in rig.pose.bones:key(p,f)
assign(bpy.data.actions['Idle']);scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:
 if o.type in {'ARMATURE','MESH'}:o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(out/'SK_HandBrain_SingleFace.fbx'),use_selection=True,path_mode='COPY',embed_textures=True,add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z')
bpy.ops.export_scene.gltf(filepath=str(out/'HandBrain_SingleFace.glb'),use_selection=True,export_format='GLB',export_animations=True,export_animation_mode='ACTIONS',export_skins=True,export_all_influences=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'HandBrain_SingleFace.blend'))
contract=json.loads((R.parent/'hunyuan_v01/delivery/animation_contract.json').read_text())
contract['Attack_Howl']={'duration_s':3,'fps':30,'frames':[1,91],'loop':False,'root_motion':False,'full_open_s':[.82,1.8],'closed_s':2.62,'source':'attacking-2.png, 28 frames','gameplay_damage_starts_s':0,'gameplay_damage_interval_s':.5,'ue_gameplay_integrated':False}
(out/'animation_contract.json').write_text(json.dumps(contract,indent=2))
print('SINGLE_FACE_EXPORT_COMPLETE')
