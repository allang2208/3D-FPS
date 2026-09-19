import bpy,math,json,sys,numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion
R=Path(__file__).resolve().parent;out=R/'delivery'
bpy.ops.wm.open_mainfile(filepath=str(R.parent/'howl_rebuild_v02/delivery/HandBrain_SingleFace.blend'))
s=bpy.context.scene;s.render.fps=30;rig=bpy.data.objects['SK_HandBrain'];body=bpy.data.objects['HandBrain_Body']
old_names=list(rig.pose.bones.keys());old_samples={}
def assign(a):
 rig.animation_data.action=a
 if a.slots:rig.animation_data.action_slot=a.slots[0]
for name,end in [('Idle',61),('Move',31),('Attack_Slam',61),('Attack_Howl',91)]:
 assign(bpy.data.actions[name])
 for f in [1,(end+1)//2,end]:
  s.frame_set(f);old_samples[(name,f)]={p.name:np.array(p.matrix) for p in rig.pose.bones}
rig.animation_data.action=None
for p in rig.pose.bones:p.matrix_basis.identity()
bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
root=rig.data.edit_bones['root'];children=list(root.children)
pivot=rig.data.edit_bones.new('death_pivot');pivot.head=(0,0,0);pivot.tail=(0,0,.25);pivot.parent=root
for child in children:child.parent=pivot
bpy.ops.object.mode_set(mode='OBJECT')
# Root-weighted surface follows the same pivot; the root itself remains stationary.
for o in s.objects:
 if o.type!='MESH':continue
 old=o.vertex_groups.get('root')
 if old:
  new=o.vertex_groups.new(name='death_pivot')
  for v in o.data.vertices:
   for g in list(v.groups):
    if g.group==old.index:new.add([v.index],g.weight,'REPLACE');old.remove([v.index]);break
def key(p,f):
 for c in ['location','rotation_quaternion','scale']:p.keyframe_insert(c,frame=f)
p=rig.pose.bones['death_pivot'];p.rotation_mode='QUATERNION'
for name,end in [('Idle',61),('Move',31),('Attack_Slam',61),('Attack_Howl',91)]:
 assign(bpy.data.actions[name]);p.matrix_basis.identity();key(p,1);key(p,end)
error=0
for (name,f),bones in old_samples.items():
 assign(bpy.data.actions[name]);s.frame_set(f)
 for name,matrix in bones.items():error=max(error,float(np.max(np.abs(np.array(rig.pose.bones[name].matrix)-matrix))))
assert error<1e-5,error
def interp(t,keys):
 for (a,x),(b,y) in zip(keys,keys[1:]):
  if t<=b:
   q=max(0,min(1,(t-a)/(b-a)));q=q*q*(3-2*q);return x+(y-x)*q
 return keys[-1][1]
def rotate(name,axis,degrees):
 p=rig.pose.bones[name];q=p.bone.matrix_local.to_quaternion();p.rotation_quaternion=q.inverted()@Quaternion(axis,math.radians(degrees))@q
def minimum():
 bpy.context.view_layer.update();e=body.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();z=min((e.matrix_world@v.co).z for v in m.vertices);e.to_mesh_clear();return z
a=bpy.data.actions.new('Death');a.use_fake_user=True;assign(a);ground=[]
# Settle on both the head and the narrow base rather than balancing on a single protrusion.
base_ids=[v.index for v in body.data.vertices if v.co.z<.4]
head_ids=[v.index for v in body.data.vertices if v.co.z>1.35]
for p in rig.pose.bones:p.matrix_basis.identity();p.rotation_mode='QUATERNION'
lo,hi=70.,95.
for _ in range(15):
 mid=(lo+hi)/2;rotate('death_pivot',(1,0,0),mid);bpy.context.view_layer.update()
 e=body.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh()
 gap=min(m.vertices[i].co.z for i in base_ids)-min(m.vertices[i].co.z for i in head_ids);e.to_mesh_clear()
 if gap>0:hi=mid
 else:lo=mid
settled_roll=(lo+hi)/2
for f in range(1,86):
 t=(f-1)/30
 for p in rig.pose.bones:p.matrix_basis.identity();p.rotation_mode='QUATERNION'
 rig.pose.bones['arm_mount'].scale=(.055,)*3;rig.pose.bones['fan_mount'].scale=(.06,)*3
 roll=interp(t,[(0,0),(.16,-2),(.36,6),(.65,23),(.92,56),(1.12,settled_roll+2),(1.23,settled_roll+4),(1.4,settled_roll-2),(1.68,settled_roll+.8),(2.05,settled_roll),(2.77,settled_roll)])
 rotate('death_pivot',(1,0,0),roll)
 bend=interp(t,[(0,0),(.16,-4),(.35,3),(.8,7),(1.12,4),(1.24,-3),(1.55,1),(2.05,0),(2.77,0)])
 rotate('neck',(0,1,0),bend);rotate('cranium',(0,1,0),-bend*.65)
 for j in range(8):
  angle=j*math.tau/8
  # Starts at the existing Idle first pose, then relaxes asymmetrically.
  degrees=.8*math.sin(angle)*(1-min(1,t/.35))+interp(t,[(0,0),(.35,2),(.9,4),(1.12,-2),(1.4,1),(2.05,-1),(2.77,-1)])*(.7+.3*math.sin(angle))
  rotate(f'crown_{j:02}',(-math.sin(angle),math.cos(angle),0),degrees)
 p=rig.pose.bones['death_pivot'];q=p.bone.matrix_local.to_quaternion()
 shift=interp(t,[(0,0),(.4,0),(1.12,-.08),(1.5,-.12),(2.77,-.12)])
 p.location=q.inverted()@Vector((0,shift,0))
 z=minimum();lift=-z # deterministic floor support for the original body's actual deformed geometry
 p.location+=q.inverted()@Vector((0,0,lift));ground.append(minimum())
 for p in rig.pose.bones:key(p,f)
assert min(ground)>-1e-5 and max(ground)<1e-5
s.frame_start=1;s.frame_end=85;assign(bpy.data.actions['Death']);s.frame_set(85)
bpy.ops.object.select_all(action='DESELECT')
for o in s.objects:
 if o.type in {'MESH','ARMATURE'}:o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(out/'SK_HandBrain_FiveActions.fbx'),use_selection=True,path_mode='COPY',embed_textures=True,add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z')
bpy.ops.export_scene.gltf(filepath=str(out/'HandBrain_FiveActions.glb'),use_selection=True,export_format='GLB',export_animations=True,export_animation_mode='ACTIONS',export_skins=True,export_all_influences=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'HandBrain_FiveActions.blend'))
contract=json.loads((R.parent/'howl_rebuild_v02/delivery/animation_contract.json').read_text())
contract['Death']={'duration_s':2.8,'fps':30,'frames':[1,85],'loop':False,'hold_last_frame':True,'impact_s':1.12,'settled_s':2.05,'root_motion':False,'design':'Original authored side collapse; no dedicated source death clip exists','ue_integrated':False}
(out/'animation_contract.json').write_text(json.dumps(contract,indent=2))
(out/'build_validation.json').write_text(json.dumps({'old_four_actions_bone_error':error,'body_floor_min_m':min(ground),'body_floor_max_m':max(ground),'settled_roll_degrees':settled_roll,'bones':len(rig.data.bones)},indent=2))
print('DEATH_BUILD_COMPLETE')
