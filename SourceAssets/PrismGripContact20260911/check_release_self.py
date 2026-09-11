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
for entry in release:
 p=old.copy()
 for i in left:p[i]=p[parents[i]]@lr[i]@np.array(Quaternion(entry['basis'][names[i]]).to_matrix().to_4x4())
 samples.append((smooth(entry['u']),np.einsum('bij,bnj->ni',p[active],pre)[:,:3]))

out=[];digitfaces={}
for d in ['index','middle','ring','pinky','thumb']:
 bs=[idx[n] for n in names if n.startswith(d+'_') and n.endswith('_l')];own=weights[ids][:,bs].sum(axis=1)>.85;digitfaces[d]=[f for f in faces if all(own[i] for i in f)]
for k,(t,points) in enumerate(samples):
 ts={d:BVHTree.FromPolygons(points.tolist(),fs,all_triangles=True) for d,fs in digitfaces.items()};out.append({a+'-'+b:len(ts[a].overlap(ts[b])) for a,b in itertools.combinations(ts,2)})
(O/'release_self.json').write_text(json.dumps(out,indent=2));print('RELEASE_SELF',[(i,sum(x.values())) for i,x in enumerate(out) if sum(x.values())])
