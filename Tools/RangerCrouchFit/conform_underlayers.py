"""Inset only the trouser upper-thigh/waist under this shirt; preserve lower legs."""
import copy,gc,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');sys.path.insert(0,str(P/'Tools/RangerCrouchFit'));import fit
R=fit.R;manifest=fit.read(R/'authored.json');records=[]
for row in manifest['records']:
    if row['item']!='ue_leather_pants':continue
    path=Path(row['file']);archive=R/'BeforeUpperInset'/(row['profile']+'.json');d=fit.read(archive if archive.exists() else path);original=copy.deepcopy(d);p=np.array(d['positions']);fs=fit.exterior(d)
    # Weld only normal accumulation at coincident garment pattern boundaries.
    vn=fit.normals(p,fs);_,inv=np.unique(np.round(p,5),axis=0,return_inverse=True);acc=np.zeros((inv.max()+1,3));np.add.at(acc,inv,vn);vn=acc[inv];vn/=np.maximum(np.linalg.norm(vn,axis=1,keepdims=True),1e-12)
    tree=BVHTree.FromPolygons([Vector(v) for v in p],fs.tolist(),all_triangles=True);out=p.copy();changed=[]
    for i,q in enumerate(p):
        if q[2]<=52:continue
        hit,_,fi,_=tree.find_nearest(Vector(q));tri=fs[fi];bc=fit.bary(np.array(hit),p[tri]);n=bc@vn[tri];n/=max(np.linalg.norm(n),1e-12)
        depth=2.3*float(fit.smooth((q[2]-52)/25));out[i]-=n*depth;changed.append(i)
    triangles=np.array(d['triangles']);alln=fit.normals(out,triangles);moved=np.zeros(len(out),bool);moved[changed]=True
    for fi in np.flatnonzero(np.any(moved[triangles],axis=1)):d['normals'][fi]=alln[triangles[fi]].tolist()
    d['positions']=out.tolist();d['contract']+='; Shirt-only conforming upper-trouser inset, 0 to2.3cm over z52..77cm; original weights and all lower-leg vertices retained'
    d['ranger_underfit']=dict(depth_cm=2.3,blend_z_cm=[52,77],vertices=len(changed),native_weights_unchanged=True)
    archive.parent.mkdir(exist_ok=True)
    if not archive.exists():fit.write(archive,original)
    fit.write(path,d);row['underfit']=d['ranger_underfit'];records.append(dict(profile=row['profile'],**d['ranger_underfit']));print('RANGER_INNER_FIT',row['profile'],flush=True);del d,original;gc.collect()
fit.write(R/'authored.json',manifest);fit.write(R/'upper_inset.json',dict(completed=True,records=records))
