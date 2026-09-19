import bpy,numpy as np,json,sys,math,itertools
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
src=(O/'refine_natural_exact.py').read_text().split('adjustments={}')[0].replace("Canted_Natural.blend","Canted_Refit.blend").replace("natural_fit.json","canted_refit.json")
exec(compile(src,str(O/'release_solver_generated.py'),'exec'))
base=np.array([list(map(list,r.pose.bones[n].matrix)) for n in names]);basis=np.array([list(map(list,r.pose.bones[n].matrix_basis)) for n in names]);G=base[index['WPN_root']]@np.array(fit['grip_in_root']);qs={n:Matrix(fit['basis'][n]).to_quaternion() for n in fit['basis'] if n.endswith('_l') and n.startswith(tuple(digits))};opened=json.loads((O.parent/'VerticalGripErgonomic20260911/vertical/release_profile.json').read_text())[-1]['basis'];faces=[]
for d in digits:faces+=grip_fs[d]
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
p0,v0=calc(basis);print('CHECK_STATIC',len(BVHTree.FromPolygons(v0.tolist(),faces,all_triangles=True).overlap(tree)),np.max(np.abs(p0-base)),flush=True)
best=None
for vector,delay,rate in itertools.product([(0,.08485,.08485),(0,.12,.12),(.025,.12,.12),(-.025,.12,.12),(0,.16,.08),(-.04,.14,.04)], [0,.15,.30,.45], [1,1.3]):
 hitframes=0;pairs=0
 for u in [k/24 for k in range(1,25)]:
  bas=basis.copy();t=smooth((u-delay)/(1-delay)*rate)
  for n,q in qs.items():bas[index[n],:3,:3]=np.array(q.slerp(Quaternion(opened[n]),t).to_matrix())
  p=base.copy();p[index['hand_l'],:3,3]+=G[:3,:3]@np.array(vector)*smooth(u)
  for i in left:p[i]=p[par[i]]@lr[i]@bas[i]
  v=np.einsum('bij,bnj->ni',p[active],pre)[:,:3];hit=len(BVHTree.FromPolygons(v.tolist(),faces,all_triangles=True).overlap(tree));hitframes+=hit>0;pairs+=hit
 score=pairs*10000+np.linalg.norm(vector)*100+delay*2
 if best is None or score<best[0]:best=(score,vector,delay,rate,hitframes,pairs);print('RELEASE_BEST',best,flush=True)
assert best[5]==0,best
fit['release_vector']=list(best[1]);fit['retreat_start']=0;fit['release_delay']=best[2];fit['release_rate']=best[3]
(O/'canted_refit.json').write_text(json.dumps(fit,indent=2));(O/'release_solution.json').write_text(json.dumps({'vector':best[1],'delay':best[2],'rate':best[3],'tested':24,'pairs':best[5]},indent=2))
