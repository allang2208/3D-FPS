"""Fit only the rear linen collar to the accepted idle and saved robe."""
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector, Quaternion
from mathutils.bvhtree import BVHTree

N=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115')
R=N/'IdleBackReviewR2'; O=R/'Authored';O.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
trim=read(O/'trim.json')
robe=read(R/'InputsAfter/robe.json')
head=read(N/'RefinementR4/Authored/head.json')
body=read(R/'InputsAfter/body.json')
anim=read(R/'InputsAfter/saved_idle.json')
names=anim['names'];parents=anim['parents'];ix={n:i for i,n in enumerate(names)}
def fk(frame):
    out=[]
    for i,k in enumerate(frame):
        m=Matrix.LocRotScale(Vector(k[:3]),Quaternion((k[6],*k[3:6])),Vector(k[7:]))
        out.append(out[parents[i]]@m if parents[i]>=0 else m)
    return np.array(out)
reference=fk(anim['reference']); inv=np.linalg.inv(reference)
def bind(data):
    p=np.array(data['positions']);indices=[];bones=[];weights=[]
    for v,items in enumerate(data['weights']):
        for b,w in items:
            # Face-only bones keep their reference local transform under the
            # nearest body bone copied by the production head AnimInstance.
            while data['bones'][b]['name'] not in ix:b=data['bones'][b]['parent']
            indices.append(v);bones.append(ix[data['bones'][b]['name']]);weights.append(w)
    return p,np.array(indices),np.array(bones),np.array(weights)
tp,ti,tb,tw=bind(trim);rp,ri,rb,rw=bind(robe)
hp,hi,hb,hw=bind(head)
bp,bi,bb,bw=bind(body)
def skin(p,idx,bones,weights,matrices):
    blend=np.zeros((len(p),4,4));np.add.at(blend,idx,matrices[bones]*weights[:,None,None])
    return np.einsum('nij,nj->ni',blend,np.column_stack([p,np.ones(len(p))]))[:,:3],blend
faces=np.array(robe['triangles']);mat=np.array(robe['triangle_materials'])
proxy=next(i for i,m in enumerate(robe['materials']) if m['slot']=='RobeSimulationProxy')
keep=(mat!=proxy)&(rp[faces,:,][...,2].mean(1)>132)&(rp[faces,:,][...,1].mean(1)<3)
faces=faces[keep]
head_faces=np.array(head['triangles']);head_faces=head_faces[(hp[head_faces,...,2].mean(1)<148)&(hp[head_faces,...,2].mean(1)>133)]
body_faces=np.array(body['triangles']);centers=bp[body_faces].mean(1)
body_faces=body_faces[(centers[:,2]>133)&(centers[:,2]<148)&(abs(centers[:,0])<8)&(abs(centers[:,1]-1.3)<9)]
linen=sorted({v for t,m in zip(trim['triangles'],trim['triangle_materials']) if m==0 for v in t})
assert linen==list(range(9600)), 'Unexpected collar topology; preserve source'
direction=tp[:9600,:2]-[0,1.3];direction/=np.linalg.norm(direction,axis=1)[:,None]
offset=np.zeros(9600);samples=[0,30,75,150,210,300,360]
for frame in samples:
    matrices=fk(anim['frames'][frame])@inv
    posed_robe,_=skin(rp,ri,rb,rw,matrices)
    posed_head,_=skin(hp,hi,hb,hw,matrices)
    posed_body,_=skin(bp,bi,bb,bw,matrices)
    posed,blend=skin(tp,ti,tb,tw,matrices)
    tree=BVHTree.FromPolygons([Vector(p) for p in posed_robe],faces.tolist(),all_triangles=True)
    neck_tree=BVHTree.FromPolygons([Vector(p) for p in posed_head],head_faces.tolist(),all_triangles=True)
    body_neck_tree=BVHTree.FromPolygons([Vector(p) for p in posed_body],body_faces.tolist(),all_triangles=True)
    for v in linen:
        q=posed[v];out=np.array([q[0],q[1]-1.3,0.]);out/=np.linalg.norm(out)
        for support,clearance in ((tree,.38),(neck_tree,.3),(body_neck_tree,.35)):
            if support is tree and tp[v,1]>=1.3:continue
            hit,_,_,_=support.ray_cast(Vector(q+out*4),Vector(-out),8.)
            if hit is not None:
                needed=float(np.dot(np.array(hit)-q,out))+clearance
                if needed>0:
                    local=np.linalg.solve(blend[v,:3,:3],out*needed)
                    offset[v]=max(offset[v],float(np.dot(local[:2],direction[v])))
# Keep solidified inner/outer shells paired and spread the clearance smoothly.
grid=np.maximum(offset[:4800],offset[4800:]).reshape(25,192)
raw=grid.copy()
for _ in range(12):
    pad=np.pad(grid,((1,1),(0,0)),mode='edge')
    grid=np.maximum(raw,(4*grid+np.roll(grid,1,1)+np.roll(grid,-1,1)+pad[:-2]+pad[2:])/8)
delta=np.tile(grid.ravel(),2)
assert float(delta.max())<2.0, 'Unexpected required collar offset; inspect rather than inflate'
tp[:9600,:2]+=direction*delta[:,None];trim['positions']=tp.tolist()
mesh=bpy.data.meshes.new('RearCollarClearance');mesh.from_pydata(trim['positions'],[],[t[::-1] for t in trim['triangles']]);mesh.update()
for poly in mesh.polygons:poly.use_smooth=True
for i,poly in enumerate(mesh.polygons):
    if trim['triangle_materials'][i]==0:
        trim['normals'][i]=[list(mesh.corner_normals[j].vector) for j in list(poly.loop_indices)[::-1]]
(O/'trim.json').write_text(json.dumps(trim,separators=(',',':')),encoding='utf-8')
report={'sample_frames':samples,'rear_collar_vertices_moved':int(sum(delta>1e-5)),'maximum_outward_correction_cm':float(delta.max()),'minimum_target_clearance_cm':.38,'face_and_hair_modified':False}
(R/'collar_geometry_final.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('NUN_COLLAR_IDLE_CLEARANCE',report,flush=True)
