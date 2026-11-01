"""Single right-hand conductor lift; left releases and hangs naturally."""
import ast,copy,json,math
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent;R=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
FPS=240
# Retain the accepted relaxed left arm from the recall family.
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'RecallWeightV4/ThunderHammer_RecallWeightV4_Editable.blend'))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];a=bpy.data.actions['A_ThunderHammer_RecallReady_V2']
rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(120)
hang={b.name:b.matrix.copy() for b in rig.pose.bones}
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ChargeRestoreV6/ThunderHammer_ChargeRestoreV6_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
a=bpy.data.actions['A_ThunderHammer_ThrowCharge'];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
scene.frame_set(0);idle={b.name:b.matrix.copy() for b in rig.pose.bones}
scene.frame_set(480);raised={b.name:b.matrix.copy() for b in rig.pose.bones}
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local_rest={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
closed={b.name:idle[b.parent.name].inverted()@idle[b.name] for b in rig.data.bones if b.name.startswith(('thumb','index','middle','ring','pinky'))}
common=(P.parent/'ThrowRefineV3/author_motion.py').read_text(encoding='utf-8')
tree=ast.parse(common)
helpers={'smooth','blend','unwrap','framed','project','pose_local'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in helpers],type_ignores=[]),'<native_helpers>','exec'))
grip=idle['WPN_root'].inverted()@idle['hand_r']
top=raised['WPN_root'].copy()
# Camera-right presentation is authored into the complete grasp. The shaft is
# held by the same right-hand grip throughout; no wrist swap or regrasp.
top.translation+=Vector((.14,.025,0))
left_top=hang['hand_l'].copy()
defs=[]
for kind,seconds in [('charge',2.),('release',.72)]:
 for i in range(round(seconds*FPS)+1):
  t=i/FPS
  if kind=='charge':
   lift=smooth((t-.12)/1.48)
   wpn=blend(idle['WPN_root'],top,lift)
   wpn.translation.y+=.035*math.sin(math.pi*lift)
   left=blend(idle['hand_l'],left_top,smooth((t-.02)/.72))
   # Peel away from the shaft before the hand descends.
   left.translation.x-=.035*math.sin(math.pi*smooth(t/.72))
   shoulder_l=idle['upperarm_l'].translation.lerp(hang['upperarm_l'].translation,smooth(t/.6))
   shoulder_r=idle['upperarm_r'].translation.lerp(Vector((.235,-.055,-.155)),lift)
   opening=smooth((t-.03)/.28)
  else:
   recover=smooth((t-.16)/.56)
   loaded=top.copy();loaded.translation+=Vector((0,-.025,-.022))*math.sin(math.pi*min(t/.16,1))**2
   wpn=blend(loaded,idle['WPN_root'],recover)
   left=blend(left_top,idle['hand_l'],smooth((t-.28)/.44))
   shoulder_l=hang['upperarm_l'].translation.lerp(idle['upperarm_l'].translation,smooth((t-.28)/.44))
   shoulder_r=Vector((.235,-.055,-.155)).lerp(idle['upperarm_r'].translation,recover)
   opening=1-smooth((t-.48)/.20)
  defs.append(dict(kind=kind,t=t,wpn=wpn,hands={'r':wpn@grip,'l':left},shoulders={'r':shoulder_r,'l':shoulder_l},opening=opening))
# Solve the complete native arm chains on their two-bone circles; preserve bone
# lengths and distribute forearm roll using the project's V9 skin contract.
solver=common[common.index('arm={}'):common.index('def finger_pose')]
exec(compile(solver,'<native_hinged_solver>','exec'))
poses=[];twists={}
for i,d in enumerate(defs):
 out=copy.deepcopy(idle)
 for side in ('l','r'):solve(out,side,i,twists)
 loc=pose_local(out)
 for bone in rig.data.bones:
  if bone.name in closed and bone.name.endswith('_l'):
   hn=hang[bone.parent.name].inverted()@hang[bone.name]
   loc[bone.name]=blend(closed[bone.name],hn,d['opening'])
 for bone in rig.data.bones:out[bone.name]=out[bone.parent.name]@loc[bone.name] if bone.parent else loc[bone.name]
 out['WPN_root']=d['wpn'].copy()
 # Native-local entry prevents a shoulder pop; weapon/right hand keep contact.
 if d['kind']=='charge' and d['t']<.12:
  a,b=pose_local(idle),pose_local(out);w=smooth(d['t']/.12);joined={}
  for bone in rig.data.bones:
   m=blend(a[bone.name],b[bone.name],w);joined[bone.name]=joined[bone.parent.name]@m if bone.parent else m
  joined['WPN_root']=out['WPN_root'];out=joined
 poses.append(out)
count=2*FPS+1;charge=poses[:count];release=poses[count:]
charge[0]=copy.deepcopy(idle);release[0]=copy.deepcopy(charge[-1]);release[-1]=copy.deepcopy(idle)
baker=ast.parse((R/'SourceAssets/SteelWarhammer20261014/SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in baker.body if isinstance(n,ast.FunctionDef) and n.name in {'apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))
names=['A_ThunderHammer_CallCharge','A_ThunderHammer_CallRelease']
for name,rows in zip(names,[charge,release]):bake(name,rows,FPS)
rig.animation_data.action=bpy.data.actions[names[0]];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_set(480)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'JiLeiMotionV1_Editable.blend'))
(P/'motion.json').write_text(json.dumps(dict(fps=FPS,clips=names,charge_seconds=2,release_seconds=.72,
 right='Fixed original grip; whole-arm lift and V9 distributed twist',left='Natural hang from RecallWeightV4; peel then lower; return late',
 right_grip_local=[list(r) for r in grip],runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('JI_LEI_MOTION_EXPORTED',flush=True)
