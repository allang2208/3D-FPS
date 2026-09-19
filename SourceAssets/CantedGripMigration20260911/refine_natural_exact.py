import bpy,numpy as np,json,math,itertools,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;sys.path.insert(0,str(O));from audit_m4 import apply,render
bpy.ops.wm.open_mainfile(filepath=str(O/'Canted_Natural.blend'));r=bpy.data.objects['SK_M4_Infima'];ob=bpy.data.objects['SK_Manny_Arms_Export'];ob.data.calc_loop_triangles();fit=json.loads((O/'natural_fit.json').read_text());D=np.load(O/'exact_state.npz');names=json.loads((O.parent/'CantedForegrip20260911/ThumbClose/hand_lbs.json').read_text())['names'];index={n:i for i,n in enumerate(names)};par=D['parents'];rest=D['rest'];base=D['pose'].copy();lr=np.array([np.linalg.inv(rest[p])@rest[i] if p>=0 else rest[i] for i,p in enumerate(par)]);basis=np.array([np.linalg.inv(lr[i])@(np.linalg.inv(base[p])@base[i] if p>=0 else base[i]) for i,p in enumerate(par)]);digits=['index','middle','ring','pinky','thumb'];W=D['weights'];labels=np.argmax(W,axis=1);tri=np.array([tuple(t.vertices) for t in ob.data.loop_triangles]);selected=np.flatnonzero(W[:,[index['hand_l']]+[i for i,n in enumerate(names) if n.endswith('_l') and n.startswith(tuple(digits))]].sum(axis=1)>.05);mapping=np.full(len(W),-1);mapping[selected]=np.arange(len(selected));active=np.flatnonzero(W[selected].sum(axis=0)>0);pre=np.einsum('nb,bij,nj->bni',W[selected][:,active],np.linalg.inv(rest[active]),D['vertices'][selected]);left=[i for i,n in enumerate(names) if n.endswith('_l') and n.startswith(tuple(digits))];self_fs={};grip_fs={};ids={};tips={}
for d in digits:
 boneids=[i for i,n in enumerate(names) if n.startswith(d+'_') and n.endswith('_l')];mask=W[:,boneids].sum(axis=1)>.85;ids[d]=mapping[np.flatnonzero(mask)];self_fs[d]=mapping[tri[np.all(mask[tri],axis=1)]].tolist();mask=np.isin(labels,boneids);grip_fs[d]=mapping[tri[np.any(mask[tri],axis=1)]].tolist();tips[d]=mapping[np.flatnonzero(W[:,index[d+'_03_l']]>.8)]
M=np.load(O/'grip_surface.npz');tree=BVHTree.FromPolygons(M['vertices'].tolist(),M['faces'].tolist(),all_triangles=True)
def calc(bas):
 p=base.copy()
 for i in left:p[i]=p[par[i]]@lr[i]@bas[i]
 return p,np.einsum('bij,bnj->ni',p[active],pre)[:,:3]
adjustments={}
for d in digits:
 origin=basis.copy();cur=calc(origin)[1];others={dd:BVHTree.FromPolygons(cur.tolist(),self_fs[dd],all_triangles=True) for dd in digits if dd!=d};best=None
 specs=[(d+'_metacarpal_l','y'),(d+'_01_l','z'),(d+'_02_l','z'),(d+'_03_l','z')] if d!='thumb' else [('thumb_01_l','y'),('thumb_02_l','z'),('thumb_03_l','z')]
 def evaluate(x):
  global best
  bas=origin.copy()
  for (n,axis),angle in zip(specs,x):bas[index[n],:3,:3]=bas[index[n],:3,:3]@np.array(Quaternion({'x':(1,0,0),'y':(0,1,0),'z':(0,0,1)}[axis],math.radians(angle)).to_matrix())
  p,v=calc(bas);vv=v.tolist();gt=BVHTree.FromPolygons(vv,grip_fs[d],all_triangles=True);dt=BVHTree.FromPolygons(vv,self_fs[d],all_triangles=True);hits=len(gt.overlap(tree));selfhits=sum(len(dt.overlap(t)) for t in others.values());near=sum(sorted(tree.find_nearest(Vector(v[i]))[3] for i in ids[d][::3])[:6])/6*1000;tip=sum(sorted(tree.find_nearest(Vector(v[i]))[3] for i in tips[d][::3])[:4])/4*1000
  score=(hits+selfhits)*1e5+max(near-.8,0)**2*80+max(tip-2,0)**2*12+sum(a*a for a in x)*.04
  if best is None or score<best[0]:best=(score,list(x),hits,selfhits,near,tip,bas)
 for step in [12,6,3,1]:
  center=[0]*len(specs) if best is None else best[1]
  for delta in itertools.product([-step,0,step],repeat=len(specs)):
   x=[a+b for a,b in zip(center,delta)]
   if d!='thumb' and abs(x[0])>10:continue
   evaluate(x)
  print('EXACT_DIGIT',d,step,best[:6],flush=True)
 basis=best[6];adjustments[d]={'angles':best[1],'grip_pairs':best[2],'self_pairs':best[3],'near_mm':best[4],'tip_mm':best[5]}
p,v=calc(basis);apply(r,{n:Matrix(p[i]) for i,n in enumerate(names)},{n:Matrix(rest[i]) for i,n in enumerate(names)});fit['basis']={n:[list(x) for x in r.pose.bones[n].matrix_basis] for n in fit['basis']};fit['exact_digit_refinement']=adjustments;(O/'canted_refit.json').write_text(json.dumps(fit,indent=2));(O/'exact_digit_refinement.json').write_text(json.dumps(adjustments,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'Canted_Refit.blend'));render(r,r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root']),'exact_final')
