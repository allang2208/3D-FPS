import bpy,json,sys,itertools,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
source=(O/'refine_canted_surface.py').read_text().split('for xyz in')[0];exec(compile(source,str(O/'contact_generated.py'),'exec'))
D=np.load(O.parent/'CantedForegrip20260911/ThumbClose/hand_lbs.npz');names=json.loads((O.parent/'CantedForegrip20260911/ThumbClose/hand_lbs.json').read_text())['names'];index={n:i for i,n in enumerate(names)};parents=D['parents'];restnp=D['rest'];oldnp=np.array([list(map(list,old[n])) for n in names]);lr=np.array([np.linalg.inv(restnp[parent])@restnp[i] if parent>=0 else restnp[i] for i,parent in enumerate(parents)]);basis=np.array([np.linalg.inv(lr[i])@(np.linalg.inv(oldnp[parent])@oldnp[i] if parent>=0 else oldnp[i]) for i,parent in enumerate(parents)])
selected=np.array(sorted(set(i for t in faces for i in t)));mapping=np.full(len(D['vertices']),-1);mapping[selected]=np.arange(len(selected));fs=mapping[faces].tolist();weights=D['weights'][selected];active=np.flatnonzero(weights.sum(axis=0)>0);pre=np.einsum('nb,bij,nj->bni',weights[:,active],np.linalg.inv(restnp[active]),D['vertices'][selected]);left=[i for i,n in enumerate(names) if n.endswith('_l') and n.startswith(tuple(digits))];Brot=np.array(B.to_3x3());world=np.array(r.matrix_world)
def calc(x):
 y,z,mcp,pip=x;p=oldnp.copy();p[index['hand_l'],:3,3]+=Brot@np.array([0,y,z])/1000
 for i in left:
  n=names[i];b=basis[i].copy()
  if not n.startswith('thumb') and '_0' in n:
   angle=mcp if '_01_' in n else pip if '_02_' in n else pip*.62;b[:3,:3]=b[:3,:3]@np.array(Quaternion((0,0,1),math.radians(angle)).to_matrix())
  p[i]=p[parents[i]]@lr[i]@b
 v=(np.einsum('bij,bnj->ni',p[active],pre)@world.T)[:,:3];return p,v
best=None
def evaluate(x):
 global best
 p,v=calc(x);hit=len(BVHTree.FromPolygons(v.tolist(),fs,all_triangles=True).overlap(tree));gap=[]
 for digit in digits[:4]:
  ii=[mapping[i] for i in ids[digit] if mapping[i]>=0];gap.append(sum(sorted(tree.find_nearest(Vector(v[i]))[3] for i in ii)[:8])/8*1000)
 score=hit*10000+sum(max(0,g-2)**2*20 for g in gap)+x[0]**2+x[1]**2+(x[2]**2+x[3]**2)*.5
 if best is None or score<best[0]:best=(score,list(x),hit,gap);print('CONTACT',best,flush=True)
 return score
for x in itertools.product([0,4,8,12,16],[-12,-6,0,6],[-12,-6,0,6,12],[-12,-6,0,6,12]):evaluate(x)
for step in [3,1]:
 center=best[1]
 for delta in itertools.product([-step,0,step],repeat=4):
  x=[a+b for a,b in zip(center,delta)]
  if abs(x[2])<=16 and abs(x[3])<=18 and abs(x[0])<=20 and abs(x[1])<=18:evaluate(x)
assert best[2]==0,best
p,v=calc(best[1]);pose={n:Matrix(p[i]) for i,n in enumerate(names)};from audit_m4 import support
code=(O/'build_akm.py').read_text();exec(code[code.index('def arm('):code.index('def render(')],globals());arm(pose,rest,pose['hand_l'],1,Vector((0,0,0)));apply(r,pose,rest)
f['hand_in_root']=[list(x) for x in pose['WPN_root'].inverted()@pose['hand_l']];f['basis']={n:[list(x) for x in r.pose.bones[n].matrix_basis] for n in f['basis']};f['surface_parameters']=best[1]
(O/'canted_refit.json').write_text(json.dumps(f,indent=2));(O/'surface_refinement.json').write_text(json.dumps({'parameters':best[1],'pairs':best[2],'finger_gap_mm':best[3]},indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'Canted_Refit.blend'));render(r,G,'surface')
