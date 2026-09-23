"""Apply the new SVD hand shape to grasp, insertion and release, with full-arm support."""
import ast,json,math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent;D=O/'Animations';D.mkdir(exist_ok=True)

def helpers(path,names):
 tree=ast.parse(path.read_text(encoding='utf-8-sig'))
 exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),str(path),'exec'),globals())

helpers(S/'SVDCompletion20260923/author_svd.py',['sample','select','bake','mix'])
helpers(S/'SVDReloadArm20260923/author_animations.py',['frame','filter_vectors'])
helpers(S/'SVDMagazineSeat20260923/author_animations.py',['ease','finger_basis'])
# Same full-chain retargeting as the seating revision, extended to the complete
# grasp window. Segment lengths always come from the unmodified source poses.
support_path=S/'SVDMagazineSeat20260923/author_animations.py'
text=support_path.read_text();tree=ast.parse(text)
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='support_return')
support=ast.get_source_segment(text,fn).replace('240 < f','18 < f').replace('(f-240)/12','(f-18)/31').replace('(f-240)/6','(f-18)/6')
exec(compile(support,str(support_path)+'::grasp_window','exec'))
fit=json.loads((O/'grasp_fit.json').read_text())
G=Matrix(fit['hand_in_mag']);closed={n:Quaternion(q) for n,q in fit['finger_basis'].items()};opened={n:Quaternion(q) for n,q in fit['open_basis'].items()}
previous=json.loads((S/'SVDMagazineSeat20260923/authoring.json').read_text())
bpy.context.preferences.filepaths.save_version=0;report={}

def hand_targets(poses):
 ready=poses[302];back_local=ready['WPN_root'].inverted()@ready['hand_l']
 entry_basis={n:finger_basis(poses[18],n).to_quaternion() for n in fingers}
 result=[]
 for f,old in enumerate(poses):
  p={n:m.copy() for n,m in old.items()}
  if 18<f<302:
   M=old['WPN_SOCKET_Magazine'];held=M@G
   if f<=49:
    approach=held.copy();approach.translation+=M.to_3x3()@Vector((.025,.006,0))*(1-ease((f-34)/15))
    H=mix(old['hand_l'],approach,ease((f-18)/16));qs={}
    for n in fingers:
     delay={'thumb':0,'index':1,'middle':2,'ring':3,'pinky':4}[n.split('_')[0]]
     ready=entry_basis[n].slerp(opened[n],ease((f-18)/14))
     qs[n]=ready.slerp(closed[n],ease((f-34-delay)/(15-delay)))
   elif f<=244:
    H=held;qs=closed
   else:
    H=held.copy();H.translation+=M.to_3x3()@Vector((.060,.010,-.012))*ease((f-254)/14)
    back=ease((f-268)/34);H=mix(H,old['WPN_root']@back_local,back)
    H.translation+=M.to_3x3()@Vector((.012,0,-.012))*math.sin(math.pi*back)
    qs={}
    for n in fingers:
     delay={'thumb':0,'index':1,'middle':2,'ring':3,'pinky':4}[n.split('_')[0]]
     q=closed[n].slerp(opened[n],ease((f-244-delay)/12))
     qs[n]=q.slerp(finger_basis(old,n).to_quaternion(),ease((f-284)/18))
   p['hand_l']=H
   for n in fingers:
    loc,_,scale=finger_basis(old,n).decompose()
    p[n]=p[parent[n]]@lr[n]@Matrix.LocRotScale(loc,qs[n],scale)
  result.append(p)
 return result

for family in ['base','vertical','canted','prism','angled']:
 source=S/'SVDMagazineSeat20260923'/f'SVD_{family}_Editable.blend'
 bpy.ops.wm.open_mainfile(filepath=str(source));r=bpy.data.objects['SK_M4_Infima']
 rest={b.name:b.matrix_local.copy() for b in r.data.bones};parent={b.name:b.parent.name if b.parent else None for b in r.data.bones}
 lr={n:rest[parent[n]].inverted()@m if parent[n] else m for n,m in rest.items()}
 fingers=[n for n in rest if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
 for clip in ['reload','reload_empty']:
  key=family+'/'+clip;info=previous[key];name=info['name'];a=bpy.data.actions[name]
  original=[sample(r,a,f) for f in range(info['frames']+1)]
  poses=support_return(original,hand_targets(original))
  a.name='REFERENCE_BEFORE_NATURAL_GRASP_'+name
  bake(r,poses,name.removeprefix('A_SVD_'),120)
  report[key]={**info,'source':str(D/(name+'.fbx')),'blend':str(O/f'SVD_{family}_Editable.blend'),'previous_blend':str(source),
   'changed':'Actual left palm anchor and all finger joint rotations rebuilt for SVD width; coupled PIP/DIP curl without finger axial twisting; grasp, insertion, release and full arm retargeted',
   'grasp_fit':str(O/'grasp_fit.json'),'game_tested':False}
  (O/'authoring.json').write_text(json.dumps(report,indent=2));print('SVD_NATURAL_ANIMATION_AUTHORED',key,flush=True)
 sample(r,bpy.data.actions[previous[family+'/reload']['name']],220)
 bpy.ops.wm.save_as_mainfile(filepath=str(O/f'SVD_{family}_Editable.blend'))
print('SVD_NATURAL_ANIMATIONS_COMPLETE',len(report),flush=True)
