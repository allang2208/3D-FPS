"""Repair native left elbow/wrist skin stations without changing grip/contact."""
import bpy,json,math,ast,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent;P=S/'M870TriggerGrip20261016';X=O/'Exports/Animations';X.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'M870_TriggerGrip_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene;s.render.fps=60;s.render.fps_base=1
rest={b.name:b.matrix_local.copy() for b in r.data.bones};names=list(rest);parents={b.name:b.parent.name if b.parent else None for b in r.data.bones};local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
d=json.loads((O/'before_diagnosis.json').read_text());ru=rest['lowerarm_l'].translation-rest['upperarm_l'].translation;rf=rest['hand_l'].translation-rest['lowerarm_l'].translation

def basis(axis,normal):
 x=axis.normalized();z=(normal-x*normal.dot(x)).normalized();return Matrix((x,z.cross(x),z)).transposed()
FU=basis(ru,Vector(d['native_hinge']['upper']));FF=basis(rf,Vector(d['native_hinge']['fore']))
def ease(v):
 x=max(0.,min(1.,v));return x*x*x*(10+x*(-15+6*x))
PROXIMAL_FRACTION=0.
ELBOW_BLEND=1.
HINGE_ROLL=0.

def frames(row):
 a,e,h=[row[n].translation for n in ('upperarm_l','lowerarm_l','hand_l')];upper=e-a;fore=h-e;hinge=upper.cross(fore).normalized()
 du=basis(upper,hinge)@FU.transposed();neutral=basis(fore,hinge)@FF.transposed()
 du=Quaternion(upper.normalized(),HINGE_ROLL).to_matrix()@du;neutral=Quaternion(fore.normalized(),HINGE_ROLL).to_matrix()@neutral
 hand=(row['hand_l']@rest['hand_l'].inverted()).to_quaternion();align=(hand@rf).rotation_difference(fore);distal=align.to_matrix()@hand.to_matrix();q=(distal@neutral.transposed()).to_quaternion()
 if q.w<0:q=-q
 angle=2*math.atan2(Vector((q.x,q.y,q.z)).dot(fore.normalized()),q.w)
 return du,neutral,angle

def solve(original,roll):
 row={n:m.copy() for n,m in original.items()};du,neutral,_=frames(row);e=row['lowerarm_l'].translation.copy();a=row['upperarm_l'].translation.copy();fore=row['hand_l'].translation-e
 row['upperarm_l']=Matrix.LocRotScale(a,(du@rest['upperarm_l'].to_3x3()).to_quaternion(),Vector((1,1,1)))
 proximal=Quaternion(fore.normalized(),roll*PROXIMAL_FRACTION).to_matrix()@neutral
 for n in ('lowerarm_l','lowerarm_aux_l','lowerarm_twist_02_l','lowerarm_twist_01_l'):
  off=rest[n].translation-rest['lowerarm_l'].translation;t=off.dot(rf)/rf.length_squared
  amount=PROXIMAL_FRACTION+(1-PROXIMAL_FRACTION)*ease(t/(2/3));driver=Quaternion(fore.normalized(),roll*amount).to_matrix()@neutral
  if n=='lowerarm_aux_l':driver=du.to_quaternion().slerp(proximal.to_quaternion(),ELBOW_BLEND).to_matrix()
  pos=e+t*fore+driver@(off-t*rf)
  row[n]=Matrix.LocRotScale(pos,(driver@rest[n].to_3x3()).to_quaternion(),Vector((1,1,1)))
 return row

tree=ast.parse((P/'author_trigger_grip.py').read_text(encoding='utf-8-sig'));exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='bake'],type_ignores=[]),str(P/'author_trigger_grip.py'),'exec'))
report={'input':str(P/'M870_TriggerGrip_Editable.blend'),'method':'Native S90 R9 skin stations; anatomical upper-arm hinge and elbow blend; hand/contact unchanged','write_world_bones':['upperarm_l','lowerarm_l','lowerarm_aux_l','lowerarm_twist_02_l','lowerarm_twist_01_l'],'clips':{},'scope':{},'runtime_tested':False,'visual_accepted':False}
auth=json.loads((P/'authoring.json').read_text(encoding='utf-8'))
for role,entry in auth['clips'].items():
 action=bpy.data.actions[entry['action']];r.animation_data.action=action;r.animation_data.action_slot=action.slots[0];rate=entry['sample_rate'];count=round(entry['duration']*rate)+1;originals=[]
 for i in range(count):
  frame=i*60/rate;s.frame_set(int(frame),subframe=frame-int(frame));originals.append({b.name:b.matrix.copy() for b in r.pose.bones})
 rolls=np.unwrap([frames(row)[2] for row in originals]);rows=[solve(row,float(roll)) for row,roll in zip(originals,rolls)]
 report['clips'][role]=bake(role,rows,rate);report['scope'][role]={'input_action':entry['action'],'source_roll_range_deg':np.rad2deg([min(rolls),max(rolls)]).tolist(),'hand_and_fingers_world_preserved':True,'shoulder_elbow_wrist_positions_preserved':True}
 print('M870_LEFT_STATIONS_AUTHORED',role,count,flush=True)
a=bpy.data.actions[report['clips']['idle']['action']];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
exec(compile((O/'apply_surface_to_blend.py').read_text(encoding='utf-8-sig'),str(O/'apply_surface_to_blend.py'),'exec'),{'__file__':str(O/'apply_surface_to_blend.py')})
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M870_LeftArm_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
