"""Remove the residual elbow roll discontinuity without moving the magazine or hand."""
import ast,json,math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent;D=O/'Animations';D.mkdir(exist_ok=True)
tree=ast.parse((S/'SVDCompletion20260923/author_svd.py').read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['sample','select','bake']],type_ignores=[]),'<SVD helpers>','exec'))
previous=json.loads((S/'SVDContactWrap20260923/authoring.json').read_text())
bpy.context.preferences.filepaths.save_version=0
report={}

def ease(x):
 x=max(0,min(1,x));return x*x*x*(x*(x*6-15)+10)

def repair(poses,rest):
 u,f,h='upperarm_l','lowerarm_l','hand_l'
 ru=(rest[f].translation-rest[u].translation).normalized()
 axis_local=rest[u].to_quaternion().inverted()@ru
 twists=[]
 for p in poses:
  U=(p[f].translation-p[u].translation).normalized()
  Df=p[f].to_quaternion()@rest[f].to_quaternion().inverted()
  target=(Df@ru).rotation_difference(U)@Df@rest[u].to_quaternion()
  delta=p[u].to_quaternion().inverted()@target
  if delta.w<0:delta.negate()
  twists.append(2*math.atan2(Vector((delta.x,delta.y,delta.z)).dot(axis_local),delta.w))
 # Unwrap in one fixed rest-local axis, so crossing +/-pi cannot reverse the arm.
 twists=np.unwrap(twists)
 # The closest continuous branch is sufficient for this action; do not add turns.
 twists-=round(float(np.median(twists[49:260]))/(2*math.pi))*2*math.pi
 rows=[]
 for frame,p in enumerate(poses):
  weight=ease((frame-18)/31)*(1-ease((frame-340)/45))
  if weight<=0:continue
  theta=float(twists[frame])*weight
  q=p[u].to_quaternion()@Quaternion(axis_local,theta)
  p[u]=Matrix.LocRotScale(p[u].translation,q,p[u].to_scale())
  for suffix in ['01','02']:
   name='upperarm_twist_'+suffix+'_l'
   p[name]=p[u]@rest[u].inverted()@rest[name]
  if frame in [49,80,120,160,200,220,240,252,268,284,302,320,340,360,384]:
   rows.append({'frame':frame,'upper_roll_correction_deg':math.degrees(theta)})
 return poses,rows

for family in ['base','vertical','canted','prism','angled']:
 source=S/'SVDContactWrap20260923'/f'SVD_{family}_Editable.blend'
 bpy.ops.wm.open_mainfile(filepath=str(source));r=bpy.data.objects['SK_M4_Infima']
 rest={b.name:b.matrix_local.copy() for b in r.data.bones}
 for clip in ['reload','reload_empty']:
  key=family+'/'+clip;info=previous[key];name=info['name'];a=bpy.data.actions[name]
  poses=[sample(r,a,f) for f in range(info['frames']+1)]
  poses,rows=repair(poses,rest)
  a.name='REFERENCE_BEFORE_ELBOW_CONTINUITY_'+name
  bake(r,poses,name.removeprefix('A_SVD_'),120)
  report[key]={**info,'source':str(D/(name+'.fbx')),'blend':str(O/f'SVD_{family}_Editable.blend'),'previous_blend':str(source),
    'changed':'Upper-arm and weighted auxiliary bones carry the forearm roll continuously; component-space hand, fingers, forearm, magazine and weapon tracks retained',
    'roll_corrections':rows,'game_tested':False}
  (O/'authoring.json').write_text(json.dumps(report,indent=2));print('SVD_ARM_CONTINUITY_AUTHORED',key,flush=True)
 sample(r,bpy.data.actions[previous[family+'/reload']['name']],220)
 bpy.ops.wm.save_as_mainfile(filepath=str(O/f'SVD_{family}_Editable.blend'))
print('SVD_ARM_CONTINUITY_COMPLETE',len(report),flush=True)
