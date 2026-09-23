"""Support the existing SVD magazine grasp with a continuous complete arm chain."""
import bpy,ast,json,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=O.parent;D=O/'Animations';D.mkdir(exist_ok=True)
tree=ast.parse((S/'SVDCompletion20260923/author_svd.py').read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['sample','select','bake','smooth','mix']],type_ignores=[]),'<SVD author helpers>','exec'))
source_info=json.loads((S/'SVDMagazineFit20260923/authoring.json').read_text())
bpy.context.preferences.filepaths.save_version=0
report={};metrics={}

def frame(axis,transverse):
 y=axis.normalized();x=transverse-y*transverse.dot(y);x.normalize();z=x.cross(y)
 return Matrix((x,y,z)).transposed().to_quaternion()

def angle(a,b):return math.degrees(a.normalized().angle(b.normalized()))

def filter_vectors(values):
 # Author a continuous shoulder support curve; the two-bone solve below restores
 # exact segment lengths after filtering. No bone-by-bone world-pose blending.
 kernel=np.array([1,4,6,4,1],dtype=float)/16
 a=np.array(values)
 for _ in range(2):a=np.stack([np.convolve(np.pad(a[:,j],(2,2),mode='edge'),kernel,mode='valid') for j in range(3)],axis=1)
 return [Vector(v) for v in a]

def build(poses,rest):
 cn,un,fn,hn='clavicle_l','upperarm_l','lowerarm_l','hand_l'
 ru=(rest[fn].translation-rest[un].translation).normalized();rf=(rest[hn].translation-rest[fn].translation).normalized()
 across=(rest['index_01_l'].translation-rest['pinky_01_l'].translation).normalized()
 rnormal=ru.cross(rf).normalized();end=336
 support=[];ideal_elbows=[];weights=[]
 for f,p in enumerate(poses):
  A=p[un].translation;E=p[fn].translation;T=p[hn].translation;H=p[hn]
  l1=(E-A).length;l2=(T-E).length;axis=(T-A).normalized()
  d=(H.to_quaternion()@rest[hn].to_quaternion().inverted()@rf).normalized()
  # A modest wrist bend is retained. Move the shoulder toward the closest
  # length-preserving support of that forearm, rather than forcing the wrist.
  turn=d.rotation_difference(axis);amount=min(1.,math.radians(18)/max(turn.angle,1e-6))
  F=Quaternion().slerp(turn,amount)@d;desired=T-F*l2
  direction=(A-desired).normalized()
  # Keep a usable elbow bend where the donor approaches a straight chain.
  # This changes only the support target, never the fixed hand/magazine grasp.
  away=-F;opening=direction.angle(away)
  if opening<math.radians(28):
   pole=(A-E)-away*(A-E).dot(away)
   if pole.length<1e-5:pole=p[un].to_quaternion()@Vector((1,0,0));pole-=away*pole.dot(away)
   pole.normalize();direction=away*math.cos(math.radians(28))+pole*math.sin(math.radians(28))
  target=desired+direction*l1
  w=smooth(f/34)*(1-smooth((f-286)/(end-286))) if f<end else 0.
  support.append(A.lerp(target,w));ideal_elbows.append(E.lerp(desired,w));weights.append(w)
 support=filter_vectors(support);ideal_elbows=filter_vectors(ideal_elbows)
 for f in [0,end]:support[f]=poses[f][un].translation.copy();ideal_elbows[f]=poses[f][fn].translation.copy()
 def roll_offset(p):
  F=(p[hn].translation-p[fn].translation).normalized();target=p[hn].to_quaternion()@rest[hn].to_quaternion().inverted()@across
  carried=p[fn].to_quaternion()@rest[fn].to_quaternion().inverted()@across
  target-=F*target.dot(F);carried-=F*carried.dot(F);target.normalize();carried.normalize()
  return math.atan2(F.dot(target.cross(carried)),target.dot(carried))
 phi_start=roll_offset(poses[0]);phi_end=roll_offset(poses[end]);rows=[];result=[]
 for f,old in enumerate(poses):
  p={n:m.copy() for n,m in old.items()}
  if 0<f<end:
   H=old[hn];T=H.translation;A=support[f];E0=old[fn].translation;A0=old[un].translation
   l1=(E0-A0).length;l2=(T-E0).length;axis=(T-A).normalized();dist=(T-A).length
   if dist>l1+l2-.002:A+=axis*(dist-(l1+l2-.002));dist=(T-A).length
   pole=ideal_elbows[f]-A;pole-=axis*pole.dot(axis);pole.normalize()
   along=(l1*l1-l2*l2+dist*dist)/(2*dist);E=A+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
   U=(E-A).normalized();F=(T-E).normalized();plane=U.cross(F).normalized()
   # Complete-segment forearm rotation from the palm-width axis. In particular
   # there is no 0.65 * principal-angle roll, which jumps at the +/-pi boundary.
   transverse=H.to_quaternion()@rest[hn].to_quaternion().inverted()@across
   fq=frame(F,transverse)@frame(rf,across).inverted()@rest[fn].to_quaternion()
   phi=phi_start*(1-smooth(f/34))+phi_end*smooth((f-286)/(end-286))
   fq=Quaternion(F,phi)@fq
   canonical=frame(U,plane)@frame(ru,rnormal).inverted()@rest[un].to_quaternion()
   # Preserve the donor upper-arm roll while accommodating the new direction.
   carried=(E0-A0).rotation_difference(E-A)@old[un].to_quaternion()
   uq=carried.slerp(canonical,weights[f]*.55)
   p[cn].translation+=A-A0
   p[un]=Matrix.LocRotScale(A,uq,old[un].to_scale());p[fn]=Matrix.LocRotScale(E,fq,old[fn].to_scale())
   for segment in [un,fn]:
    for suffix in ['01','02']:
     n=segment.replace('_l','_twist_'+suffix+'_l')
     if n in p:p[n]=p[segment]@rest[segment].inverted()@rest[n]
   # Hand and every finger retain their exact original component-space poses.
  before=(old[hn].to_quaternion()@rest[hn].to_quaternion().inverted()@rf)
  rows.append({'frame':f,'wrist_bend_before_deg':angle(old[hn].translation-old[fn].translation,before),
   'wrist_bend_authored_deg':angle(p[hn].translation-p[fn].translation,before),
   'shoulder_shift_cm':(p[un].translation-old[un].translation).length*100,
   'reach_ratio':(p[hn].translation-p[un].translation).length/((p[fn].translation-p[un].translation).length+(p[hn].translation-p[fn].translation).length)})
  result.append(p)
 return result,rows

for family in ['base','vertical','canted','prism','angled']:
 source=S/'SVDMatteDetail20260923'/f'SVD_{family}_Editable.blend';bpy.ops.wm.open_mainfile(filepath=str(source))
 r=bpy.data.objects['SK_M4_Infima'];rest={b.name:b.matrix_local.copy() for b in r.data.bones}
 for clip in ['reload','reload_empty']:
  key=family+'/'+clip;info=source_info[key];name=info['name'];a=bpy.data.actions[name]
  original=[sample(r,a,f) for f in range(info['frames']+1)];poses,rows=build(original,rest)
  a.name='REFERENCE_BEFORE_SUPPORT_'+name
  bake(r,poses,name.removeprefix('A_SVD_'),120)
  report[key]={**info,'source':str(D/(name+'.fbx')),'blend':str(O/f'SVD_{family}_Editable.blend'),'previous_blend':str(source),
   'changed':'Left shoulder/elbow support and continuous complete forearm roll; existing hand/finger world poses, right side, weapon mechanics and clock preserved',
   'game_tested':False}
  metrics[key]={'rows':rows,'insert_160_240':{'before_max':max(v['wrist_bend_before_deg'] for v in rows[160:241]),'authored_max':max(v['wrist_bend_authored_deg'] for v in rows[160:241]),'shoulder_shift_max_cm':max(v['shoulder_shift_cm'] for v in rows[160:241])}}
  (O/'authoring.json').write_text(json.dumps(report,indent=2));(O/'support_authoring.json').write_text(json.dumps(metrics,indent=2))
  print('SVD_RELOAD_SUPPORTED',key,metrics[key]['insert_160_240'],flush=True)
 sample(r,bpy.data.actions[source_info[family+'/reload']['name']],220)
 bpy.ops.wm.save_as_mainfile(filepath=str(O/f'SVD_{family}_Editable.blend'))
print('SVD_RELOAD_SUPPORT_AUTHORED',len(report),flush=True)
