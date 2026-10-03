"""Fit native finger rotations and whole-hand offsets to the actual RSH surfaces."""
import sys,json,math,bpy,numpy as np,ast
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O))
from pose_geometry import *
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['single','idle']
family=args[0];kind=args[1] if len(args)>1 else 'idle'
rig,D,profile,meta=load(family)
source=O/'BeforeAuthored/Integration'/('Single' if family=='single' else 'Dual/'+family)
bpy.ops.wm.open_mainfile(filepath=str(source/('RSH12_'+family+'_Editable.blend')))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.animation_data_clear();rig.data.pose_position='POSE'
meta=json.loads((source/'authoring.json').read_text())
# The output is an absolute correction to the original shared 715 pose.
# Never fit against the last authored profile, which already contains a correction.
profile=json.loads((source/'profile.json').read_text());base=source_pose(rig,D,profile,kind);rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
ra=rest['WPN_root']@Matrix(meta['alignment']);root=base['WPN_root']@rest['WPN_root'].inverted()@ra
registration=Matrix.Translation((0,.018,-.006))@Matrix.Translation((0,.086,.011))@Matrix.Rotation(math.radians(6),4,'X')@Matrix.Translation((0,-.086,-.011))
canonical=(root@registration).inverted();raw=json.loads((B/'canonical_parts.json').read_text())
solid=[]
for part in raw:
 if part['name'] not in ('9_l','7_l','11_l','17_l','8_l'):continue
 vv=[Vector(v) for v in part['verts']];solid.append((BVHTree.FromPolygons(vv,part['faces']),Vector(tuple(min(v[a] for v in vv) for a in range(3))),Vector(tuple(max(v[a] for v in vv) for a in range(3)))))
direction=Vector((.371,.691,.591)).normalized()
def depth(pt):
 result=0.
 for tree,lo,hi in solid:
  if any(pt[a]<lo[a] or pt[a]>hi[a] for a in range(3)):continue
  origin=pt+direction*1e-7;count=0
  for i in range(10):
   hit,_,_,_=tree.ray_cast(origin,direction,.5)
   if hit is None:break
   count+=1;origin=hit+direction*1e-6
  if count%2:result=max(result,tree.find_nearest(pt)[3]*1000)
 return result
ob=next(o for o in bpy.data.objects if o.type=='MESH');groups={g.index:g.name for g in ob.vertex_groups};names=list(rest)
tree=ast.parse((SA/'author_single_action.py').read_text());function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='arm_at')
env=dict(names=names,Matrix=Matrix,Vector=Vector,Quaternion=Quaternion,math=math)
exec(compile(ast.Module(body=[function],type_ignores=[]),'<native_arm_ik>','exec'),env);arm_at=env['arm_at']
solutions={}
for side in (('r','l') if family=='single' else (family,)):
 samples=[]
 for v in ob.data.vertices:
  ww=[(groups[g.group],g.weight) for g in v.groups if groups[g.group] in rest and g.weight>.001]
  label=max(ww,key=lambda a:a[1])[0] if ww else ''
  if label.endswith('_'+side) and label.startswith(('hand','thumb','index','middle','ring','pinky')):samples.append((rig.matrix_world.inverted()@ob.matrix_world@v.co,ww))
 used=list({n for _,ww in samples for n,w in ww});bind={n:np.asarray([list(row) for row in rest[n].inverted()]) for n in used}
 coords=np.array([[*pt,1.] for pt,ww in samples]);weights=np.array([[dict(ww).get(n,0.) for n in used] for pt,ww in samples]);weights/=weights.sum(axis=1)[:,None]
 labels=[max(ww,key=lambda nw:nw[1])[0] for pt,ww in samples]
 # Contact comes from distal skin, so a proximal corner cannot satisfy a floating tip.
 for name in ('thumb_03_'+side,'middle_03_'+side,'ring_03_'+side,'pinky_03_'+side):
  local_points=[(i,(rest[name].inverted()@pt).y) for i,((pt,ww),label) in enumerate(zip(samples,labels)) if label==name]
  local_points.sort(key=lambda iv:iv[1]);allowed={i for i,y in local_points[-max(1,len(local_points)//3):]}
  for i,y in local_points:
   if i not in allowed:labels[i]=''
 grip_tree=next(tree for (tree,lo,hi),part in zip(solid,[p for p in raw if p['name'] in ('9_l','7_l','11_l','17_l','8_l')]) if part['name']=='9_l')
 locals={n:base[rig.data.bones[n].parent.name].inverted()@base[n] if rig.data.bones[n].parent else base[n] for n in names}
 chain=[n for n in names if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky'))]
 parameters=[('offset',i) for i in range(3)]+[(n,axis) for n in chain for axis in ('X','Z')]
 x=[0.]*len(parameters);x[0]=-.002 if side=='r' else .015;x[1]=0 if side=='r' else .016
 previous_file=O/('hand_contact_'+family+'_'+kind+'.json')
 if previous_file.exists():
  previous=json.loads(previous_file.read_text())['hands'][side];x[:3]=previous['offset_canonical'];angles={}
  for n,v in previous['local_rotation_delta'].items():
   source=locals[n].to_quaternion();dq=Quaternion((v[6],*v[3:6]));angles[n]=(source.inverted()@dq@source).to_euler('XYZ')
  for i,(n,axis) in enumerate(parameters[3:],3):x[i]=angles[n]['XYZ'.index(axis)]
 def pose(xx):
  hand='hand_'+side;translation=Vector(xx[:3]);delta=Matrix.Translation(root.to_quaternion()@translation);p={n:m.copy() for n,m in base.items()};arm_at(p,base,side,delta@base[hand])
  rotations={}
  for (n,axis),value in zip(parameters[3:],xx[3:]):rotations[n]=rotations.get(n,Matrix.Identity(4))@Matrix.Rotation(value,4,axis)
  for n in chain:p[n]=p[rig.data.bones[n].parent.name]@locals[n]@rotations.get(n,Matrix.Identity(4))
  return p
 def evaluate(xx,report=False):
  p=pose(xx);matrices=np.stack([np.asarray([list(row) for row in canonical@p[n]])@bind[n] for n in used]);pts=np.einsum('pbij,pj,pb->pi',np.broadcast_to(matrices,(len(coords),*matrices.shape)),coords,weights,optimize=True)
  depths=[depth(Vector(pt[:3])) for pt in pts];penetration=sum(max(0,d-.35)**2 for d in depths)/len(depths)
  # Keep a grasp: penalize drifting the whole hand and changing phalanx angles.
  regular=.0015*sum(math.degrees(v)**2 for v in xx[3:])+.008*sum((v*1000)**2 for v in xx[:3])
  gaps={n:1e4 for n in ('thumb_03_'+side,'middle_03_'+side,'ring_03_'+side,'pinky_03_'+side,'hand_'+side)}
  for label,pt in zip(labels,pts):
   if label in gaps:gaps[label]=min(gaps[label],grip_tree.find_nearest(Vector(pt[:3]))[3]*1000)
  contact=sum(max(0,d-.6)**2 for d in gaps.values())
  score=penetration*150+regular+max(depths)**2*150+contact*2
  return (score,max(depths),sum(d>.5 for d in depths),p) if report else score
 score=evaluate(x)
 if family=='l' and score>500:
  # A hand starting inside a broad grip can sit on a max-depth plateau.
  # Seed a complete hand placement before refining individual joints.
  for tx in (-.04,-.02,0.,.02,.04,.06):
   for ty in (-.025,0.,.025):
    for tz in (-.025,0.,.025):
     candidate=x[:];candidate[:3]=[tx,ty,tz];value=evaluate(candidate)
     if value<score:x=candidate;score=value
  print('CONTACT_COARSE_HAND',side,round(score,3),x[:3],flush=True)
 for level in range(6):
  distance=.008*(.6**level);angle=math.radians(12)*(.6**level)
  for sweep in range(3):
   changed=False
   for i,(name,axis) in enumerate(parameters):
    step=distance if i<3 else angle;best=x[i];bestscore=score
    for sign in (-1,1):
     candidate=x[:];candidate[i]+=step*sign
     limit=.06 if i<3 else math.radians(20 if '_metacarpal_' in name else 65)
     if abs(candidate[i])>limit:continue
     value=evaluate(candidate)
     if value<bestscore:best=candidate[i];bestscore=value
    if best!=x[i]:x[i]=best;score=bestscore;changed=True
   if not changed:break
  print('CONTACT_FIT',side,level,round(score,3),flush=True)
 score,maximum,count,p=evaluate(x,True)
 deltas={}
 for n in chain:
  parent=rig.data.bones[n].parent.name;lp=p[parent].inverted()@p[n];deltas[n]=packed(lp@locals[n].inverted())
 solutions[side]=dict(offset_canonical=x[:3],hand_canonical=list(root.inverted()@base['hand_'+side].translation),local_rotation_delta=deltas,fit_sample_count=len(samples),penetration_max_mm=maximum,penetrating_sample_count=count,score=score)
 print('CONTACT_RESULT',side,maximum,count,x[:3],flush=True)
(O/('hand_contact_'+family+'_'+kind+'.json')).write_text(json.dumps(dict(registration=[list(row) for row in registration],hands=solutions),indent=2))
