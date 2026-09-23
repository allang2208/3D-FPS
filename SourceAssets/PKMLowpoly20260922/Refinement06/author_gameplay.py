"""Export the PKM candidate for the shared FPS action system; no renders/tests."""
import bpy,json,math,pathlib
from mathutils import Matrix,Vector
O=pathlib.Path(__file__).parent;R=O.parent;E=O/'Exports';E.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(O/'PKM_Manny_Reload_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['PKM_Manny_Rig'];s.render.fps=60
import sys
sys.path.insert(0,str(O))
from surface_and_skin import refine
refine(r)
def action(a):
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
def select(objects):
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=r
def export(name,mesh=False):
 objects=[r]+[o for o in s.objects if o.type=='MESH' and (o.name=='SK_Manny_Arms_Export' or 'mechanical_bone' in o)] if mesh else [r]
 select(objects)
 bpy.ops.export_scene.fbx(filepath=str(E/(name+'.fbx')),use_selection=True,object_types={'ARMATURE','MESH'} if mesh else {'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=not mesh,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,bake_anim_step=1,use_mesh_modifiers=True,mesh_smooth_type='FACE',path_mode='AUTO')
# Material sections give the runtime explicit ownership of the old/new props.
# No animated scale hiding: the section swap happens only at the action boundary.
sections={}
for o in s.objects:
 if o.type!='MESH' or 'mechanical_bone' not in o:continue
 bone=o['mechanical_bone'];new=bone.startswith('New_');b=bone.removeprefix('New_')
 group=('New' if new else 'Old')+('Box' if b in ['PKM_Box','PKM_BoxLid'] else 'Belt') if b in ['PKM_Box','PKM_BoxLid'] or b.startswith('PKM_Belt') else ''
 if group:
  for slot in o.material_slots:
   original=slot.material;name=original.name+'__'+group
   mat=bpy.data.materials.get(name)
   if not mat:mat=original.copy();mat.name=name
   slot.material=mat;sections[name]={'base':original.name,'group':group}
action(bpy.data.actions['PKM_Idle']);s.frame_set(0);bpy.context.view_layer.update()
base={b.name:b.matrix.copy() for b in r.pose.bones}
rest={b.name:b.bone.matrix_local.copy() for b in r.pose.bones}
parents={b.name:b.parent.name if b.parent else None for b in r.pose.bones}
W=base['WPN_root'];fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
# The common item/icon frame uses the magazine marker as its pivot.
mag=W@fit@Matrix.Translation((0,.04,-.065));mag.translation=W@(fit@Vector((0,.04,-.065)))
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def seq(t,keys):
 if t<=keys[0][0]:return keys[0][1]
 for (a,v),(b,w) in zip(keys,keys[1:]):
  if t<=b:return v+(w-v)*smooth((t-a)/(b-a))
 return keys[-1][1]
def trans(v):return Matrix.Translation(v)
def rot(axis,d):return Matrix.Rotation(math.radians(d),4,axis)
def pose(kind,t):
 d={n:m.copy() for n,m in base.items()};motion=Matrix.Identity(4)
 if kind in ['fire','aim_fire']:
  pulse=seq(t,[(0,0),(.025,1),(.10,0)]);motion=trans((0,.007*pulse,-.001*pulse))@rot('X',-.45*pulse)
  # Mechanical recoil and trigger remain relative to the fitted gun root.
  for n in ['PKM_InnerCarrier','PKM_Charge']:
   d[n]=W@trans((0,.012*pulse,0))@W.inverted()@d[n]
  pivot=d['PKM_Trigger'].translation
  d['PKM_Trigger']=trans(pivot)@rot('X',-5*pulse)@trans(-pivot)@d['PKM_Trigger']
  for i in range(14):
   n=f'PKM_Belt_{i:02}';d[n]=W@trans((.002*math.sin(t/.10*math.pi*2),0,.001*pulse))@W.inverted()@d[n]
 elif kind=='equip':
  p=1-smooth(t/.72);motion=trans((.04*p,.05*p,-.20*p))@rot('X',-25*p)@rot('Y',10*p)
 elif kind=='inspect':
  p=seq(t,[(0,0),(.75,1),(1.8,1),(2.8,-.6),(3.5,-.6),(4.2,0)])
  motion=trans((.045*p,.025*abs(p),.035*abs(p)))@rot('Y',28*p)@rot('Z',-10*p)
 elif kind.startswith('sprint_'):
  p=smooth(t/.32) if kind=='sprint_enter' else 1-smooth(t/.32) if kind=='sprint_exit' else 1
  bob=math.sin(t*math.pi*2)*.005 if kind=='sprint_loop' else 0
  motion=trans((.045*p,.055*p,-.04*p+bob))@rot('X',-20*p)@rot('Y',-12*p)
 elif kind=='quick_melee':
  p=seq(t,[(0,0),(.10,-.3),(1/6,1),(8/30,.8),(.9,0)])
  motion=trans((-.065*p,-.085*p,.035*p))@rot('Z',32*p)@rot('Y',-18*p)
 # Apply one complete assembly transform: both hands retain their contact frames.
 xf=W@motion@W.inverted()
 for n in d:d[n]=xf@d[n]
 if 'WPN_SOCKET_Magazine' in d:d['WPN_SOCKET_Magazine']=xf@mag
 return d
def bake(kind,duration):
 a=bpy.data.actions.new('PKM_Game_'+kind);a.use_fake_user=True;r.animation_data.action=a;last={}
 for frame in range(round(duration*60)+1):
  d=pose(kind,frame/60)
  for n,m in d.items():
   p=parents[n];lr=rest[p].inverted()@rest[n] if p else rest[n];lp=d[p].inverted()@m if p else m
   loc,q,scale=(lr.inverted()@lp).decompose()
   if n in last and last[n].dot(q)<0:q.negate()
   last[n]=q.copy();b=r.pose.bones[n];b.location=loc;b.rotation_quaternion=q;b.scale=scale
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=frame,group=n)
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for key in curve.keyframe_points:key.interpolation='LINEAR'
 s.frame_start=0;s.frame_end=round(duration*60);s.frame_set(0);export('A_PKM_'+kind)
 return a
clips={'idle':1,'aim':1,'fire':.10,'aim_fire':.10,'equip':.72,'inspect':4.2,'sprint_enter':.32,'sprint_loop':1,'sprint_exit':.32,'quick_melee':.9}
for kind,duration in clips.items():bake(kind,duration);print('PKM_GAME_CLIP',kind,flush=True)
for kind,source,duration in [('reload','PKM_Reload_Normal',6.5),('reload_empty','PKM_Reload_Empty',7.5)]:
 action(bpy.data.actions[source]);s.frame_start=0;s.frame_end=round(duration*60);s.frame_set(0);export('A_PKM_'+kind);clips[kind]=duration
action(bpy.data.actions['PKM_Game_idle']);s.frame_start=0;s.frame_end=60;s.frame_set(0)
export('SK_PKM_Manny',True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PKM_Gameplay_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'clips':clips,'sections':sections,'fps':60,'mesh':'SK_PKM_Manny','tested':False,'hand_source':'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend','additional_motion':'Fitted idle assembly transforms; reload retains selected video adaptation'},indent=2),encoding='utf-8')
print('PKM_GAMEPLAY_EXPORT_COMPLETE',flush=True)
