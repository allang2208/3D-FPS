import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'A_M4_Canted_idle.blend'));bpy.context.scene.frame_set(0);bpy.context.view_layer.update();r=bpy.data.objects['SK_M4_Infima']
D=np.load(O/'hand_lbs.npz');names=json.loads((O/'hand_lbs.json').read_text())['names'];parents=D['parents'];rest=D['rest'];old=np.array([list(map(list,r.pose.bones[n].matrix)) for n in names]);idx={n:i for i,n in enumerate(names)};lr=np.array([np.linalg.inv(rest[p])@rest[i] if p>=0 else rest[i] for i,p in enumerate(parents)])
left=[i for i,n in enumerate(names) if n.endswith('_l') and n.startswith(('index','middle','ring','pinky','thumb'))];ids=np.flatnonzero(D['weights'][:,left].sum(axis=1)>.05);w=D['weights'][ids];active=np.flatnonzero(w.sum(axis=0)>0);pre=np.einsum('nb,bij,nj->bni',w[:,active],np.linalg.inv(rest[active]),D['vertices'][ids]);mapping=np.full(len(D['vertices']),-1);mapping[ids]=np.arange(len(ids));faces=mapping[np.load(O/'triangles.npy')];faces=faces[np.all(faces>=0,axis=1)]
trees=[]
for ob in [o for o in bpy.context.scene.objects if o.name.startswith('CG_')]:
 ob.data.calc_loop_triangles();trees.append(BVHTree.FromPolygons([r.matrix_world.inverted()@ob.matrix_world@v.co for v in ob.data.vertices],[tuple(t.vertices) for t in ob.data.loop_triangles],all_triangles=True))
fit=json.loads((O/'fit_final.json').read_text());release=json.loads((O/'release_profile.json').read_text());v=np.array((r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root'])).to_3x3())@np.array(fit['release_vector']);closed={n:Matrix(m).to_quaternion() for n,m in fit['basis'].items()};smooth=lambda t:(lambda x:x*x*(3-2*x))(max(0,min(1,t)))
def evaluate(speed,delay):
 total=0;out=[]
 for entry in release:
  u=entry['u'];ret=smooth((u-delay)/(1-delay));p=old.copy();p[idx['hand_l'],:3,3]+=v*ret;qs={}
  for i in left:
   n=names[i];q=Quaternion(entry['basis'][n]);
   if n.startswith('pinky'):q=closed[n].slerp(Quaternion(release[-1]['basis'][n]),smooth(u*speed))
   qs[n]=list(q);p[i]=p[parents[i]]@lr[i]@np.array(q.to_matrix().to_4x4())
  points=np.einsum('bij,bnj->ni',p[active],pre);tree=BVHTree.FromPolygons(points[:,:3].tolist(),faces.tolist(),all_triangles=True);count=len(set(i for t in trees for i,j in tree.overlap(t)));total+=count;out.append({'u':u,'basis':qs,'retreat':ret})
 return total,out
best=None
for speed in [1.2,1.3,1.4,1.5,1.6,1.7,1.8]:
 for delay in [.04,.06,.08,.10,.12,.14,.16]:
  score,out=evaluate(speed,delay);print('RELEASE',speed,delay,score,flush=True)
  if best is None or score<best[0]:best=(score,speed,delay,out)
  if score==0:break
 if best[0]==0:break
(O/'release_search.json').write_text(json.dumps({'score':best[0],'speed':best[1],'delay':best[2]},indent=2))
if best[0]==0:(O/'release_profile.json').write_text(json.dumps(best[3],indent=2))
print('BEST',best[:3])
