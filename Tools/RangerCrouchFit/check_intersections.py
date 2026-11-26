"""Exact surface intersection check of the reported clothing pair.

Uses real garment triangles, without artificial volume caps at open cuffs/waist.
"""
import json,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');sys.path.insert(0,str(P/'Tools/RangerCrouchFit'));import fit
R=fit.R
def segment_tri(start,end,tri):
    ray=end-start;e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0];h=np.cross(ray,e2);det=np.einsum('ij,ij->i',e1,h);valid=abs(det)>1e-9
    inv=np.zeros_like(det);inv[valid]=1/det[valid];s=start-tri[:,0];u=np.einsum('ij,ij->i',s,h)*inv;q=np.cross(s,e1);v=np.einsum('ij,ij->i',ray,q)*inv;t=np.einsum('ij,ij->i',e2,q)*inv
    return valid&(u>=-1e-7)&(v>=-1e-7)&(u+v<=1+1e-7)&(t>1e-6)&(t<1-1e-6)
def crossing(a,b):
    hit=np.zeros(len(a),bool)
    for i in range(3):hit|=segment_tri(a[:,i],a[:,(i+1)%3],b)|segment_tri(b[:,i],b[:,(i+1)%3],a)
    return hit
def prepare(d,shirt=False):
    p=np.array(d['positions']);fs=np.array(d['triangles']);original=np.arange(len(fs))
    if shirt:
        slots=np.array(d['triangle_materials']);mask=fit.skin_mask(d);keep=np.all(mask[fs],axis=1)&np.isin(slots,[0,1,3,4]);fs=fs[keep];original=original[keep]
    ids=np.unique(fs);m=np.full(len(p),-1,int);m[ids]=np.arange(len(ids));return p[ids],m[fs],[d['weights'][i] for i in ids],original
inputs=fit.read(R/'inputs.json');pants=fit.read(R/'Authored/ue_leather_pants/LeatherPants.json');shirt=fit.read(R/'Authored/ue_field_sweater/Jason.json');pp,pf,pw,pids=prepare(pants);sp,sf,sw,sids=prepare(shirt,True)
USE_POSE_CLEARANCE=globals().get('USE_POSE_CLEARANCE',False)
if USE_POSE_CLEARANCE:
    import pose_clearance
    original_positions=np.array(shirt['positions']);all_shirt_faces=np.array(shirt['triangles']);shader_ids=np.unique(all_shirt_faces[sids])
frames=[('Reference',None)]+[(k+'@'+str(i),sample['bones']) for k,row in inputs['clips'].items() for i,sample in enumerate(row['samples'])];rows=[]
for name,frame in frames:
    p=pp if frame is None else fit.skinned(pp,pw,fit.transforms(pants,frame));s=sp if frame is None else fit.skinned(sp,sw,fit.transforms(shirt,frame))
    if USE_POSE_CLEARANCE:
        tr=None if frame is None else fit.transforms(shirt,frame);full=original_positions if frame is None else fit.skinned(original_positions,shirt['weights'],tr);s=pose_clearance.offset(shirt,full,tr)[shader_ids]
    pb=BVHTree.FromPolygons([Vector(v) for v in p],pf.tolist(),all_triangles=True);sb=BVHTree.FromPolygons([Vector(v) for v in s],sf.tolist(),all_triangles=True);pairs=np.array(sb.overlap(pb),int).reshape(-1,2)
    if len(pairs):pairs=pairs[crossing(s[sf[pairs[:,0]]],p[pf[pairs[:,1]]])]
    rows.append(dict(pose=name,intersecting_triangle_pairs=len(pairs),shirt_triangles=sorted(set(int(sids[i]) for i in pairs[:,0])),pants_triangles=sorted(set(int(pids[i]) for i in pairs[:,1]))))
    print('ACTUAL_SURFACE_CROSSING',name,len(pairs),flush=True)
fit.write(R/('surface_check_pose_clearance.json' if USE_POSE_CLEARANCE else 'surface_check.json'),dict(completed=True,method='BVH plus exact segment-triangle crossings; real garment geometry; no analysis caps',pose_clearance=USE_POSE_CLEARANCE,samples=rows,total_intersections=sum(row['intersecting_triangle_pairs'] for row in rows),runtime_tested=False))
