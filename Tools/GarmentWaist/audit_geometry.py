"""User-requested reference-space seam audit; no animation, UE or rendering."""
import json, sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/GarmentWaist20261023'
sys.path.insert(0,str(P/'Tools/RangerCrouchFit'));import fit
manifest=fit.read(R/'authored.json');rows=[]
for row in manifest['records']:
    d=fit.read(row['file']);p=np.asarray(d['positions']);contract=d['waist_fit'];top=contract['waist_top_cm']
    guide=fit.canonical(fit.read(manifest['groups'][row['group']]['guide']));pp=np.asarray(guide['positions']);fs=guide['triangles'][:guide['outer_shell_triangles']]
    tree=BVHTree.FromPolygons([Vector(q) for q in pp],fs,all_triangles=True)
    ids=np.flatnonzero(fit.skin_mask(d)&(p[:,2]<=top-.05));gaps=[];missing=0
    for vi in ids:
        q=p[vi];origin=np.array([0.,.8,q[2]]);direction=q-origin;direction[2]=0;radius=np.linalg.norm(direction);direction/=max(radius,1e-12)
        hit,_,_,_=tree.ray_cast(Vector(origin+direction*40),Vector(-direction),40)
        if hit is None:missing+=1;continue
        gaps.append(float((np.asarray(hit)-origin)@direction-radius))
    sloped_gaps=[];sloped_details=[]
    if top<98.5 and not row['group'].startswith('default_'):
        for vi in np.flatnonzero(fit.skin_mask(d)&(p[:,2]>top)&(p[:,2]<top+5.)):
            q=p[vi];origin=np.array([0.,.8,q[2]]);direction=q-origin;direction[2]=0;radius=np.linalg.norm(direction);direction/=max(radius,1e-12)
            hit,_,_,_=tree.ray_cast(Vector(origin+direction*40),Vector(-direction),40)
            if hit is not None:
                gap=float((np.asarray(hit)-origin)@direction-radius);sloped_gaps.append(gap)
                if gap<-.025:sloped_details.append(dict(vertex=int(vi),position=q.tolist(),gap=gap,weights=d['weights'][vi]))
    result=dict(item=row['item'],profile=row['profile'],group=row['group'],seam_vertices=len(ids),
        sloped_upper_band_vertices=len(sloped_gaps),sloped_upper_outside=sum(g<-.025 for g in sloped_gaps),
        sloped_minimum_clearance_cm=min(sloped_gaps) if sloped_gaps else None,
        sloped_details=sloped_details[:5],
        minimum_inside_clearance_cm=min(gaps) if gaps else None,vertices_outside_pants=sum(g<-.025 for g in gaps),unresolved_rays=missing,
        authored_hem_cm=float(p[fit.skin_mask(d),2].min()),waist_top_cm=top)
    rows.append(result)
    print('WAIST_REFERENCE_AUDIT',row['item'],row['group'],row['profile'],result['vertices_outside_pants'],missing,flush=True)
fit.write(R/'reference_seam_audit.json',dict(scope='Every authored vertex in the hidden overlap plus the raised portions of sloped waistbands, in reference pose only',rows=rows,
    vertices_outside_pants=sum(r['vertices_outside_pants'] for r in rows),sloped_upper_outside=sum(r['sloped_upper_outside'] for r in rows),
    unresolved_rays=sum(r['unresolved_rays'] for r in rows),runtime_tested=False))
