"""Blender background: triangle intersections and saved-pose skinning, no gameplay."""
import json,sys,time
from pathlib import Path
from collections import Counter
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');ROOT=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';OUT=ROOT/('ClearanceAfter' if '--saved-coupled' in sys.argv else 'ClearanceReview')
def read(p):return json.loads(p.read_text())
def matrix(b):
    m=np.eye(4);m[:3,:3]=np.asarray(b['axes']).T;m[:3,3]=b['position'];return m
def prepare(d,skin=False):
    p=np.asarray(d['positions']);t=np.asarray(d['triangles'],dtype=int)
    if skin:t=t[np.asarray(d['triangle_materials'])==2]
    used=np.unique(t);remap=np.full(len(p),-1,dtype=int);remap[used]=np.arange(len(used))
    p=p[used];t=remap[t];weights=[d['weights'][i] for i in used];groups=[]
    for bn in sorted({k for w in weights for k in w}):
        ids=np.array([i for i,w in enumerate(weights) if bn in w]);w=np.array([weights[i][bn] for i in ids])
        groups.append((bn,ids,w,np.c_[p[ids],np.ones(len(ids))]@np.linalg.inv(matrix(d['bones'][bn])).T))
    kinds=None
    if 'uv2' in d:
        f=np.asarray(d['uv2'])[:,:,1];kinds=np.where(f.max(1)==0,0,np.where(f.min(1)==1,1,2))
    return dict(p=p,t=t,groups=groups,original_ids=used,kinds=kinds)
def deform(d,bones):
    p=np.zeros_like(d['p'])
    for bn,ids,w,local in d['groups']:p[ids]+=(local@matrix(bones[bn]).T)[:,:3]*w[:,None]
    return p
def tree(p,t):return BVHTree.FromPolygons(p.tolist(),t[:,::-1].tolist(),all_triangles=True,epsilon=0.)
def measure(s,g,sp=None,gp=None):
    sp=s['p'] if sp is None else sp;gp=g['p'] if gp is None else gp
    st=tree(sp,s['t']);gt=tree(gp,g['t']);contacts=st.overlap(gt);overlap=[];max_depth=0.;worst_pair=None;sum_depth=0.
    # BVH also reports an intentionally shared edge. A crossing must straddle
    # both triangle planes; a point/edge touch is the watertight opening seam.
    if contacts:
        ix=np.asarray(contacts);a=sp[s['t'][ix[:,0]]];b=gp[g['t'][ix[:,1]]]
        an=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]);bn=np.cross(b[:,1]-b[:,0],b[:,2]-b[:,0])
        an/=np.maximum(np.linalg.norm(an,axis=1)[:,None],1e-16);bn/=np.maximum(np.linalg.norm(bn,axis=1)[:,None],1e-16)
        da=np.einsum('nki,ni->nk',a-b[:,0,None,:],bn);db=np.einsum('nki,ni->nk',b-a[:,0,None,:],an)
        tol=1e-5
        cross=(da.min(1)<-tol)&(da.max(1)>tol)&(db.min(1)<-tol)&(db.max(1)>tol)
        depths=np.minimum.reduce([-da.min(1),da.max(1),-db.min(1),db.max(1)])
        max_depth=float(max(0.,depths.max())*10)
        sum_depth=float(np.square(np.maximum(depths,0)*10).sum())
        worst_pair=list(contacts[int(np.argmax(depths))]) if max_depth>0 else None
        overlap=[contacts[i] for i in np.flatnonzero(cross)]
    # Original mesh winding is UE clockwise. Reversed triangles give outward normals.
    dist=[];bad=[]
    for i,p in enumerate(gp if '--coverage' not in sys.argv and '--saved-coupled' not in sys.argv else []):
        hit,n,fi,d=st.find_nearest(Vector(p))
        signed=float(np.dot(p-np.asarray(hit),np.asarray(n)))
        dist.append(signed)
        if signed<-.005:bad.append(i) # penetration beyond 0.05 mm
    return dict(triangle_pairs=len(overlap),max_plane_cross_mm=max_depth,sum_squared_cross_mm=sum_depth,worst_pair=worst_pair,seam_touch_pairs=len(contacts)-len(overlap),skin_faces=len({a for a,b in overlap}),glove_faces=len({b for a,b in overlap}),
        outer_pairs=int(sum(g['kinds'][b]==0 for a,b in overlap)) if g['kinds'] is not None else None,
        below_skin_005mm=len(bad),min_signed_mm=float(min(dist)*10) if dist else 0,p01_signed_mm=float(np.percentile(dist,1)*10) if dist else 0,
        bad_vertices=bad[:100],pairs=[list(p) for p in overlap[:100]])
report=dict(scope='Saved UE mesh surfaces and compressed animation samples; not PIE',static=[],poses=[])
manifest=read(OUT/'mesh-manifest.json')
for entry in manifest:
    name=entry['profile'];s=prepare(read(OUT/(name+'_skin.json')),True);g=prepare(read(OUT/(name+'_glove.json')))
    if '--coverage' in sys.argv:s=prepare(read(ROOT/'SkinCoverage'/(name+'_review.json')),True)
    if '--authored' in sys.argv:g=prepare(read(ROOT/'Authored'/(name+'.json')))
    row=dict(profile=name,lod=0,**measure(s,g));report['static'].append(row)
    print('CLEARANCE_REST',name,row['triangle_pairs'],round(row['min_signed_mm'],4),row['below_skin_005mm'],flush=True)
for name in (() if '--authored' in sys.argv else ('M4','PKM','A762')):
    for lod in (1,2):
        s=prepare(read(OUT/f'{name}_skin_lod{lod}.json'),True);g=prepare(read(OUT/f'{name}_glove_lod{lod}.json'))
        row=dict(profile=name,lod=lod,**measure(s,g));report['static'].append(row)
        print('CLEARANCE_REST_LOD',name,lod,row['triangle_pairs'],round(row['min_signed_mm'],4),flush=True)
(OUT/('clearance-author-rest.json' if '--authored' in sys.argv else 'clearance-rest.json')).write_text(json.dumps(report,indent=2))
if '--rest-only' not in sys.argv:
    for name in ('PKM','M4','A762'):
        s=prepare(read(OUT/(name+'_skin.json')),True);g=prepare(read(OUT/(name+'_glove.json')))
        if '--coverage' in sys.argv:s=prepare(read(ROOT/'SkinCoverage'/(name+'_review.json')),True)
        if '--authored' in sys.argv:g=prepare(read(ROOT/'Authored'/(name+'.json')))
        for f in sorted(OUT.glob(name+'__*_poses.json')):
            d=read(f);rows=[]
            poses=d['poses']
            if '--quick' in sys.argv:poses=[poses[i] for i in sorted(set(np.linspace(0,len(poses)-1,5).astype(int)))]
            for pose in poses:
                result=measure(s,g,deform(s,pose['bones']),deform(g,pose['bones']))
                rows.append(dict(time=pose['time'],**result))
            row=dict(profile=name,label=d['label'],asset=d['asset'],samples=rows);report['poses'].append(row)
            print('CLEARANCE_POSE',name,d['label'],len(rows),max(r['triangle_pairs'] for r in rows),round(min(r['min_signed_mm'] for r in rows),4),flush=True)
            (OUT/('clearance-author-full.json' if '--authored' in sys.argv else 'clearance-full.json')).write_text(json.dumps(report,indent=2))
print('CLEARANCE_CHECK_COMPLETE',len(report['static']),len(report['poses']),flush=True)
