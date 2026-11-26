"""Legacy Body sleeve: retain its own shape, pair it with current native skin."""
import sys,copy,numpy as np,bpy,bmesh
from pathlib import Path
from mathutils import Vector,kdtree
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
sys.path.insert(0,str(Path(__file__).parent))
from combat3_cuff_solver import P,R,C,read,write,unit,smooth,settle,cuff_weights
from combat3_cloth import mesh
from shirt_geometry import smooth_transport
d=read(R.parent/'CombatShirtR2/Authored/shirt_fp_Body.json');old=np.array(d['positions']);faces=np.array(d['triangles']);fabric=faces[np.array(d['triangle_materials'])==0];ob=mesh('BodyNativeClothProxy',old,fabric.tolist());bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(ob.data);bm.free();q=np.array([v.co[:] for v in ob.data.vertices])*[100,-100,100];tri=np.array([list(f.vertices) for f in ob.data.polygons]);bones={b['name']:np.array(b['position']) for b in d['bones']};names={b['index']:b['name'] for b in d['bones']};physical=np.zeros((len(old),2));pins=np.zeros(len(q));kd=kdtree.KDTree(len(old))
for i,p in enumerate(old):kd.insert(Vector(p),i)
kd.balance();sourceids=np.array([kd.find(Vector(p))[1] for p in q]);left=np.array([sum(w for bi,w in ws if names[bi].endswith('_l')) for ws in d['weights']]);right=np.array([sum(w for bi,w in ws if names[bi].endswith('_r')) for ws in d['weights']])
for side,selected in [('l',left>=right),('r',left<right)]:
    a,e,w=[bones[k+'_'+side] for k in ['upperarm','lowerarm','hand']];upper=unit(e-a);lower=unit(w-e);ids=np.flatnonzero(selected);dist=-(old[ids]-w)@lower;cuff_weights(d,ids,dist,side);proxy=np.flatnonzero(selected[sourceids]);pd=-(q[proxy]-w)@lower;pins[proxy]=1-smooth((pd-4.4)/3)
    p=old[ids];along=(p-e)@lower;blend=smooth((along+4)/8);axis=upper*(1-blend[:,None])+lower*blend[:,None];axis/=np.linalg.norm(axis,axis=1,keepdims=True);seed=unit(np.cross(upper,lower));cross=np.cross(axis,seed);delta=p-e;theta=np.arctan2(np.einsum('ij,ij->i',delta,cross),delta@seed);long=np.linalg.norm(e-a)+np.einsum('ij,ij->i',delta,axis);physical[ids]=np.column_stack([theta*5.8/8,long/8])
edges=np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),1);edges,n=np.unique(edges,axis=0,return_counts=True);border=np.unique(edges[n==1]);kd=kdtree.KDTree(len(border))
for i,vi in enumerate(border):kd.insert(Vector(q[vi]),i)
kd.balance();pins=np.maximum(pins,np.array([1-smooth((kd.find(Vector(p))[2]-.85)/2.4) for p in q]));pins[border]=1
row=next(x for x in read(C/'captured.json')['rows'] if x['key']=='Native_Body');body=read(row['file']);native_delta=max(np.linalg.norm(bones[name]-body['bones'][name]['position']) for name in bones if name.startswith(('upperarm','lowerarm','hand_')) and name in body['bones'])
if native_delta>.01:raise RuntimeError('Legacy Body native reference changed: '+str(native_delta))
moved=settle('FP_Body',q,tri,pins,body,frames=36);tree=BVHTree.FromPolygons(q.tolist(),tri.tolist(),all_triangles=True);new=old.copy()
for i,p in enumerate(old):
    hit=tree.find_nearest(Vector(p));ids=tri[hit[2]];new[i]+=np.array(barycentric_transform(hit[0],*[Vector(v) for v in q[ids]],*[Vector(v) for v in moved[ids]]))-np.array(hit[0])
d['positions']=new.tolist();smooth_transport(d,old);d['uv']=[]
for face in faces:
    uv=physical[face].copy()
    if np.ptp(uv[:,0])>2:uv[uv[:,0]<0,0]+=2*np.pi*5.8/8
    d['uv'].append(uv.tolist())
dest='/Game/Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR3/Materials/';d['materials']=[dest+'M_CombatRipstop',dest+'M_CombatThread'];d['cloth_production']=dict(method='Own native Body sleeve; fixed wrist band; current native skin collision',native_sha256=row['sha256'],frames=36,runtime_simulation=False);file=C/'Authored/shirt_fp_Body.json';write(file,d);write(C/'fp-batch-Body.json',dict(completed=True,rows=[dict(rig='Body',file=str(file),native=d['source'])]));print('BODY_NATIVE_CUFF_REPAIRED',flush=True)
