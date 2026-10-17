"""Restore right-hand cartridge contact using the existing UC loading grasp.

Keep the current AKM left chain, weapon/cartridge paths and event clock.
Transfer the complete UC loading hand by anatomical bind axes, then solve its support arm.
"""
import ast, json, math
from pathlib import Path
import bpy
from mathutils import Matrix, Vector, Quaternion

O=Path(__file__).parent;PREV=O.parent/'M870AKMArmSupport20261016';BASE=O.parent/'M870Tactical20261015'
X=O/'Exports';(X/'Animations').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(PREV/'M870_AKMArmSupport_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene;I=Matrix.Identity(4)
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}

def under(n,root):
 while n:
  if n==root:return True
  n=parents.get(n)
 return False

def ease(t):
 t=max(0.,min(1.,t));return t*t*(3-2*t)

def mix(a,b,w):
 pa,qa,sa=a.decompose();pb,qb,sb=b.decompose()
 return Matrix.LocRotScale(pa.lerp(pb,w),qa.slerp(qb,w),sa.lerp(sb,w))

UC=O.parent/'M870UrbanAnimations20261015'
import sys
sys.path.insert(0,str(UC))
from read_inputs import smd
source_rest=smd(UC/'Original/870/shotgun.smd')['rows'][0]
source_pose=smd(UC/'Original/870/anims/reloadinsert.smd')['rows'][6]
C=Matrix(json.loads((UC/'authoring.json').read_text())['source_to_target']);cq=C.to_quaternion()
prefix='ValveBiped.Bip01_R_'
def palm(poses,source=False):
 h=prefix+'Hand' if source else 'hand_r'
 middle=prefix+'Finger2' if source else 'middle_01_r'
 index=prefix+'Finger1' if source else 'index_01_r'
 pinky=prefix+'Finger4' if source else 'pinky_01_r'
 forward=(poses[middle].translation-poses[h].translation).normalized()
 across=(poses[index].translation-poses[pinky].translation).normalized()
 normal=across.cross(forward).normalized()
 return Matrix((forward.cross(normal).normalized(),forward,normal)).transposed().to_quaternion()
sb=palm(source_rest,True);sp=cq@palm(source_pose,True);tb=palm(rest)
handbones=[n for n in rest if under(n,'hand_r')]
template={'hand_r':Matrix.LocRotScale((C@source_pose[prefix+'Hand']).translation,sp@tb.inverted()@rest['hand_r'].to_quaternion(),Vector((1,1,1)))}
for n in handbones:
 if n=='hand_r':continue
 parent=parents[n];base=template[parent]@local_rest[n]
 if 'metacarpal' in n:template[n]=base;continue
 digit,joint,_=n.split('_');di=('thumb','index','middle','ring','pinky').index(digit);ji=int(joint)-1
 donor=prefix+'Finger'+str(di)+('' if ji==0 else str(ji))
 q=cq@source_pose[donor].to_quaternion()@source_rest[donor].to_quaternion().inverted()@sb@tb.inverted()@rest[n].to_quaternion()
 # Bind poses curl/spread fingers differently. Transport the actual donor
 # segment direction as well as roll, instead of preserving a target bind
 # curl that can leave the fingertips centimetres above the cartridge.
 if ji<2:
  next_source=prefix+'Finger'+str(di)+str(ji+1)
  next_target=f'{digit}_{ji+2:02d}_r'
  native_axis=rest[next_target].translation-rest[n].translation
  source_axis=source_pose[next_source].translation-source_pose[donor].translation
 else:
  previous_source=prefix+'Finger'+str(di)+'1'
  native_axis=rest[n].translation-rest[f'{digit}_02_r'].translation
  source_axis=source_pose[donor].to_quaternion()@source_rest[donor].to_quaternion().inverted()@(source_rest[donor].translation-source_rest[previous_source].translation)
 q=(q@rest[n].to_quaternion().inverted()@native_axis).rotation_difference(cq@source_axis)@q
 template[n]=Matrix.LocRotScale(base.translation,q,Vector((1,1,1)))
knuckles=('index','middle','ring','pinky')
source_knuckles=sum(((C@source_pose[prefix+'Finger'+str(i)]).translation for i in (1,2,3,4)),Vector())/4
native_knuckles=sum((template[n+'_01_r'].translation for n in knuckles),Vector())/4
for m in template.values():m.translation+=source_knuckles-native_knuckles
reference_action=json.loads((PREV/'authoring.json').read_text())['clips']['reload_continuous']['action']
r.animation_data.action=bpy.data.actions[reference_action];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(31)
grasp=r.pose.bones['WPN_Shell'].matrix.inverted()@template['hand_r']
fit=json.loads((O/'rigid_contact.json').read_text())
grasp=Matrix(fit['matrix'])@grasp
template_local={n:template[parents[n]].inverted()@template[n] for n in handbones if n!='hand_r'}

def move_right_arm(row,hand):
 old={n:m.copy() for n,m in row.items()}
 un='upperarm_r';ln='lowerarm_r';hn='hand_r';cl='clavicle_r'
 shoulder=old[un].translation.copy();elbow=old[ln].translation;wrist=old[hn].translation;goal=hand.translation
 l1=(elbow-shoulder).length;l2=(wrist-elbow).length
 axis=goal-shoulder;distance=axis.length
 if distance>.94*(l1+l2):
  shift=axis.normalized()*(distance-.94*(l1+l2));shoulder+=shift;row[cl].translation+=shift
  axis=goal-shoulder;distance=axis.length
 axis.normalize();pole=elbow-old[un].translation;pole-=axis*pole.dot(axis)
 if pole.length<1.e-7:pole=Vector((1,-.2,-1)).cross(axis)
 pole.normalize();along=(l1*l1-l2*l2+distance*distance)/(2*max(distance,1.e-7))
 e=shoulder+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
 uq=(elbow-old[un].translation).rotation_difference(e-shoulder)
 fq=(wrist-elbow).rotation_difference(goal-e)
 ud=Matrix.Translation(shoulder)@uq.to_matrix().to_4x4()@Matrix.Translation(-old[un].translation)
 fd=Matrix.Translation(e)@fq.to_matrix().to_4x4()@Matrix.Translation(-elbow)
 hd=hand@old[hn].inverted()
 for n in row:
  if under(n,hn):row[n]=hd@old[n]
  elif under(n,ln):row[n]=fd@old[n]
  elif under(n,un):row[n]=ud@old[n]

def phase(frame):
 t=frame/60
 index=0 if t<1. else min(6,1+int((t-1.)/(50/60)+1.e-6))
 start=18 if index==0 else 60+(index-1)*50
 contact=44+index*50;end=60+index*50
 p=12*(frame-start)/(contact-start) if frame<=contact else 12+14*(frame-contact)/(end-contact)
 return p,start,contact,end

tree=ast.parse((BASE/'author_m870.py').read_text());authored={}
selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('select','bake')]
exec(compile(ast.Module(body=selected,type_ignores=[]),str(BASE/'author_m870.py'),'exec'))
inputs=json.loads((PREV/'authoring.json').read_text())['clips'];recipes={}
for role in ('reload_continuous','reload_full'):
 entry=inputs[role];action=bpy.data.actions[entry['action']]
 r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
 count=round(entry['duration']*60)+1;original=[]
 for f in range(count):
  s.frame_set(f);original.append({b.name:b.matrix.copy() for b in r.pose.bones})
 def correction(f):
  row=original[f];return row['hand_r'].inverted()@row['WPN_Shell']@grasp
 first_correction=correction(18)
 rows=[]
 for f,source in enumerate(original):
  row={n:m.copy() for n,m in source.items()}
  if f<18:
   weight=ease(f/18);hand=source['hand_r']@mix(I,first_correction,weight);finger_weight=weight
  elif f<360:
   p,start,contact,end=phase(f)
   if p<=12:
    hand=source['WPN_Shell']@grasp;finger_weight=1.
   else:
    # Cartridge is entering the port and then hidden. Carry the hand's last
    # contact correction along its own return path, not the released prop.
    c=mix(correction(contact),correction(start),ease((p-12)/14))
    hand=source['hand_r']@c;finger_weight=1-ease((p-12)/6)*(1-ease((p-20)/6))
  else:
   weight=1-ease((f-360)/12)
   hand=source['hand_r']@mix(I,first_correction,weight);finger_weight=weight
  if f==count-1:rows.append(row);continue
  move_right_arm(row,hand)
  for n in handbones:
   if n=='hand_r':continue
   parent=parents[n];old_local=source[parent].inverted()@source[n]
   row[n]=row[parent]@mix(old_local,template_local[n],finger_weight)
  rows.append(row)
 bake(role,rows);recipes[role]={'input_action':entry['action'],'frames':count}

action=bpy.data.actions[authored['reload_continuous']['action']]
r.animation_data.action=action;r.animation_data.action_slot=action.slots[0];s.frame_set(30)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M870_ReloadContact_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'clips':authored,'recipe':recipes,
 'donor':'Urban Coalition 870 reloadinsert.smd','donor_frame':6,
 'grasp':[list(v) for v in grasp],'rigid_contact_adjustment':fit,
 'scope':'Right arm and complete anatomically retargeted UC loading hand only; input shell, gun, left arm and clocks retained.',
 'runtime_tested':False},indent=2))
print('M870_RELOAD_CONTACT_AUTHORED',len(authored))
