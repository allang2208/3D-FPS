import bpy,json,math,itertools,numpy as np
from pathlib import Path
from mathutils import Matrix,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;pdir=O/'prism';bpy.ops.wm.open_mainfile(filepath=str(pdir/'A_M4_Prism_idle.blend'));bpy.context.scene.frame_set(0);bpy.context.view_layer.update();r=bpy.data.objects['SK_M4_Infima'];ob=bpy.data.objects['SK_Manny_Arms_Export'];names=[b.name for b in r.data.bones];idx={n:i for i,n in enumerate(names)};parents=[idx[b.parent.name] if b.parent else -1 for b in r.data.bones];rest=np.array([list(map(list,b.matrix_local)) for b in r.data.bones]);old=np.array([list(map(list,r.pose.bones[n].matrix)) for n in names]);lr=np.array([np.linalg.inv(rest[a])@rest[i] if a>=0 else rest[i] for i,a in enumerate(parents)]);weights=np.zeros((len(ob.data.vertices),len(names)))
for v in ob.data.vertices:
 for g in v.groups:
  n=ob.vertex_groups[g.group].name
  if n in idx:weights[v.index,idx[n]]=g.weight
weights/=np.maximum(weights.sum(axis=1,keepdims=True),1e-10);vertices=np.array([list(r.matrix_world.inverted()@ob.matrix_world@v.co)+[1] for v in ob.data.vertices]);left=[i for i,n in enumerate(names) if n.endswith('_l') and n.startswith(('index','middle','ring','pinky','thumb'))];ids=np.flatnonzero(weights[:,left].sum(axis=1)>.05);w=weights[ids];active=np.flatnonzero(w.sum(axis=0)>0);pre=np.einsum('nb,bij,nj->bni',w[:,active],np.linalg.inv(rest[active]),vertices[ids]);ob.data.calc_loop_triangles();mapping=np.full(len(vertices),-1);mapping[ids]=np.arange(len(ids));faces=mapping[np.array([list(t.vertices) for t in ob.data.loop_triangles])];faces=faces[np.all(faces>=0,axis=1)].tolist();trees=[]
for obj in [x for x in bpy.context.scene.objects if x.name.startswith('PH_')]:
 obj.data.calc_loop_triangles();trees.append(BVHTree.FromPolygons([r.matrix_world.inverted()@obj.matrix_world@v.co for v in obj.data.vertices],[tuple(t.vertices) for t in obj.data.loop_triangles],all_triangles=True))
fit=json.loads((pdir/'fit_final.json').read_text());release=json.loads((pdir/'release_profile.json').read_text());G=np.array((r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root'])).to_3x3());smooth=lambda x:x*x*(3-2*x);samples=[]

df={}
for d in ['ring','pinky']:
 bs=[idx[n] for n in names if n.startswith(d+'_') and n.endswith('_l')];own=weights[ids][:,bs].sum(axis=1)>.85;df[d]=[f for f in faces if all(own[i] for i in f)]
best=None
for x,y in sorted(itertools.product([0,-2,2,-4,4,-6,6,-8,8],repeat=2),key=lambda t:t[0]**2+t[1]**2):
 hits=0;out=[]
 for entry in release:
  b={n:list(q) for n,q in entry['basis'].items()};t=smooth(min(1,entry['u']*2));m=Quaternion(b['pinky_01_l']).to_matrix().to_4x4()@Matrix.Rotation(math.radians(x*t),4,'X')@Matrix.Rotation(math.radians(y*t),4,'Y');b['pinky_01_l']=list(m.to_quaternion());p=old.copy()
  for i in left:p[i]=p[parents[i]]@lr[i]@np.array(Quaternion(b[names[i]]).to_matrix().to_4x4())
  points=np.einsum('bij,bnj->ni',p[active],pre)[:,:3];ts={d:BVHTree.FromPolygons(points.tolist(),fs,all_triangles=True) for d,fs in df.items()};hits+=len(ts['ring'].overlap(ts['pinky']));out.append({'u':entry['u'],'basis':b})
 if best is None or hits<best[0]:best=(hits,x,y,out)
 if hits==0:break
print('OPEN_PINKY_SPREAD',best[:3]);assert best[0]==0
(pdir/'release_profile.json').write_text(json.dumps(best[3],indent=2));(pdir/'release_spread.json').write_text(json.dumps({'x_degrees':best[1],'y_degrees':best[2],'self_pairs':best[0]},indent=2))
