"""Retarget original M24 joint directions, preserving native V9 finger offsets."""
import bpy,json,math,ast,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24ArmRebuild20261027/M24_ArmRebuild_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];skin=bpy.data.objects['M24_V9_BareArms']
source=json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())
raw=json.loads((O/'raw_reference.json').read_text())
raw_tips=json.loads((O/'raw_fingertips.json').read_text())
rest={n:Matrix(m) for n,m in source['rest'].items()};parents=source['parents']
local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
C=Matrix(json.loads((O.parent/'M24Hold20261027/hip-calibration.json').read_text())['hip_transform'])@Matrix.Diagonal((100,-100,100,1))
shoulder_offsets={'l':Vector((0,0,0)),'r':Vector((0,0,0))}
tree=ast.parse((O.parent/'M24ArmRebuild20261027/author.py').read_text())
for name in ('under','clone','ease','frame','twist','solve_frames','cost','apply_arm'):
 exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)),name,'exec'))

def semantic(p,middle,index,pinky,wrist):
 x=(p[middle].translation-p[wrist].translation).normalized()
 y=p[index].translation-p[pinky].translation;y=(y-x*y.dot(x)).normalized()
 return Matrix((x,y,x.cross(y))).transposed()
target_frame=semantic(rest,'middle_01_r','index_01_r','pinky_01_r','hand_r')
digits=[n for n in rest if under(n,'hand_r') and n!='hand_r']
raw_rest={n:Matrix(v) for n,v in raw['rest'].items()}
raw_rest_frame=semantic(raw_rest,'R_middle1','R_point1','R_pink1','R_wrist')

def raw_hand(row,native_frame):
 k=str(int(max(1,min(201,native_frame))));p={n:Matrix(v) for n,v in raw['poses'][k].items()}
 # WPN_root was rebased during the game's import. The unchanged mechanical
 # bolt frame is the matching registration surface for the original FBX.
 wr=Matrix(raw['parts'][k]['bolt']);v,q,sc=wr.decompose();wr=Matrix.LocRotScale(v,q,Vector((1,1,1)))
 mapping=row['WPN_BoltHandle']@wr.inverted()
 p={n:mapping@m for n,m in p.items()}
 pf=semantic(p,'R_middle1','R_point1','R_pink1','R_wrist')
 orientation=pf@target_frame.transposed()
 q=(orientation@rest['hand_r'].to_3x3()).to_quaternion()
 location=p['R_middle1'].translation-orientation@(rest['middle_01_r'].translation-rest['hand_r'].translation)
 out={'hand_r':Matrix.LocRotScale(location,q,Vector((1,1,1)))}
 for n in digits:out[n]=out['hand_r']@rest['hand_r'].inverted()@rest[n]
 for donor,target in [('thumb','thumb'),('point','index'),('middle','middle'),('ring','ring'),('pink','pinky')]:
  for j in (1,2,3):
   n=f'{target}_{j:02d}_r';dn='R_'+donor+str(j);parent=parents[n]
   m=out[parent]@local_rest[n]
   if j<3:
    d=p['R_'+donor+str(j+1)].translation-p[dn].translation
    rd=rest[f'{target}_{j+1:02d}_r'].translation-rest[n].translation
   else:
    # The FBX source's length axis is Y; the native V9 terminal length axis is X.
    d=mapping@Vector(raw_tips[k][dn])-p[dn].translation;rd=rest[n].to_3x3()@Vector((1,0,0))
   current=m.to_quaternion()@(rest[n].to_quaternion().inverted()@rd)
   rot=current.rotation_difference(d)@m.to_quaternion()
   out[n]=Matrix.LocRotScale(m.translation,rot,Vector((1,1,1)))
 return out

roles=('fire','cycle','reload_empty','reload_empty_mag10')
clips={role:[{n:Matrix(m) for n,m in row.items()} for row in source['clips'][role]['poses']] for role in roles}
for role,rows in clips.items():
 shift={'fire':0,'cycle':4,'reload_empty':52,'reload_empty_mag10':52}[role]
 for f,row in enumerate(rows):
  t=f-shift;w=ease((t-7)/9)*(1-ease((t-41)/10))
  if w<=0:continue
  native_frame=f+1 if role=='fire' else f+92 if role=='cycle' else f+44
  mapped=raw_hand(row,native_frame)
  for n in ['hand_r',*digits]:
   a=row[n];b=mapped[n]
   if n=='hand_r':row[n]=a.lerp(b,w)
   else:
    pa=Matrix(source['clips'][role]['poses'][f][parents[n]])
    a=pa.inverted()@a;b=mapped[parents[n]].inverted()@b
    row[n]=row[parents[n]]@Matrix.LocRotScale(local_rest[n].translation,a.to_quaternion().slerp(b.to_quaternion(),w),Vector((1,1,1)))
  phis=np.arange(-105,106,3);p=float(min(phis,key=lambda x:cost(row,'r',float(x))))
  apply_arm(row,'r',p)

tree=ast.parse((O.parent/'M24Hold20261027/author_hold.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='bake')
node.body=[n for n in node.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='twists')]
report={'clips':{}}
exec(compile(ast.unparse(node),'native_bake','exec'))
for role,rows in clips.items():
 old=bpy.data.actions['A_M24_'+role];r.animation_data.action=None;bpy.data.actions.remove(old);bake(role,rows)
(O/'candidate_poses.json').write_text(json.dumps({role:[{n:[list(v) for v in m] for n,m in row.items()} for row in rows] for role,rows in clips.items()}))
r.animation_data.action=bpy.data.actions['A_M24_fire'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(29)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_BoltRematch_Candidate.blend'))
print('CANDIDATE_SAVED',flush=True)
