"""Scoped reference-pose geometry review; no game or runtime simulation claims."""
import json,sys,math,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector,kdtree
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'SetFitReview20261115'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):Path(p).write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8')
def normals(p,f):
    n=-np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
    return n/np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
def bvh(d,mask=None):
    p=np.array(d['positions']);f=np.array(d['triangles'],dtype=int)
    if mask is not None:f=f[mask]
    return BVHTree.FromPolygons(p.tolist(),f.tolist(),all_triangles=True),normals(p,f)
def load(key):
    row=next(x for x in read(R/'plan.json')['rows'] if x['key']==key)
    return read(row['candidates'][0])
def contact(p,f,tree,bn):
    # Sample each triangle at its centroid as well as all used vertices.
    ids=np.unique(f);points=np.concatenate([p[ids],p[f].mean(1)])
    signed=[];dist=[];nearest=[]
    for q in points:
        v,n,index,d=tree.find_nearest(Vector(q));signed.append(float(np.dot(q-np.array(v),bn[index])));dist.append(d);nearest.append(index)
    signed=np.array(signed);dist=np.array(dist)
    bad=np.flatnonzero(signed<-.10);worst=np.argsort(signed)[:20]
    return dict(samples=len(points),below_minus_1mm=int(len(bad)),minimum_signed_cm=float(signed.min()),signed_percentiles_cm=np.quantile(signed,[.01,.05,.5,.95,.99]).tolist(),nearest_dist_percentiles_cm=np.quantile(dist,[.01,.5,.99]).tolist(),worst=[dict(point=points[i].tolist(),signed_cm=float(signed[i])) for i in worst]),signed,points
owners_only='--owners' in sys.argv
reports=[x for x in read(R/'fit-source.json')['rows'] if not x['kind'].endswith('owner')] if owners_only else []
for rig in ['Jason','Kaitlin']:
    body=load(rig+'_body');bt,bn=bvh(body)
    detail=read(S/'CombatShirtR3/Authored'/f'shirt_detail_{rig}.json');raw=read(S/'CombatShirtR3/Authored'/f'shirt_cloth_{rig}.json');outer_count=len(raw['positions'])//2
    for kind in ['shirt_bare_waist_world','shirt_tactical_world','shirt_tactical_owner','pants','pants_tactical','boots','gloves']:
        if owners_only and not kind.endswith('owner'):continue
        d=load(rig+'_'+kind);p=np.array(d['positions']);f=np.array(d['triangles'],dtype=int);m=np.array(d['triangle_materials']);n=normals(p,f)
        if kind.startswith('shirt'):
            # The author merge preserves the original sewn outer sheet as the
            # initial vertices. Owner subsets use their explicit cloth slots.
            if kind.endswith('owner'):
                wd=load(rig+'_shirt_tactical_world');wp=np.array(wd['positions']);wf=np.array(wd['triangles']);wi=np.unique(wf[(wf<outer_count).all(1)]);kd=kdtree.KDTree(len(wi))
                for ki,vi in enumerate(wi):kd.insert(Vector(wp[vi]),ki)
                kd.balance();outer_vertex=np.array([kd.find(Vector(v))[2]<.002 for v in p]);mask=outer_vertex[f].all(1)&np.isin(m,[0,1,2])
            else:mask=(f<outer_count).all(1)
        else:mask=np.array([not d['material_slots'][mi].startswith('NATIVE:') for mi in m])
        # Exclude inside facings from the clearance test. Actual exterior faces
        # have normals aligned with the nearest native surface.
        centers=p[f].mean(1)
        for i in np.flatnonzero(mask):
            hit=bt.find_nearest(Vector(centers[i]))
            if np.dot(n[i],bn[hit[2]])<.15:mask[i]=False
        report,signed,points=contact(p,f[mask],bt,bn)
        report.update(rig=rig,kind=kind,exterior_triangles=int(mask.sum()),reference='authored geometry pending saved-mesh correspondence',method='Nearest native outward triangle normal; vertex and centroid samples; not an exact penetration volume')
        if kind.startswith('shirt'):
            bones={b['name']:np.array(b['position']) for b in d['bones']}
            regions={}
            for name,lo,hi in [('hem',92,108),('torso',108,140),('shoulder_neck',140,170)]:
                use=(points[:,2]>=lo)&(points[:,2]<hi)&(abs(points[:,0])<23)
                if use.any():regions[name]=dict(count=int(use.sum()),below_minus_1mm=int((signed[use]<-.1).sum()),min_cm=float(signed[use].min()),median_cm=float(np.median(signed[use])))
            report['regions']=regions
        reports.append(report);print('FIT',rig,kind,'negative',report['below_minus_1mm'],'min',round(report['minimum_signed_cm'],4),flush=True)
    # Native body material extents provide the actual coverage context.
    p=np.array(body['positions']);f=np.array(body['triangles']);m=np.array(body['triangle_materials'])
    write(R/(rig+'-body-sections.json'),[dict(slot=slot,index=i,triangles=int((m==i).sum()),bounds=[p[f[m==i]].reshape(-1,3).min(0).tolist(),p[f[m==i]].reshape(-1,3).max(0).tolist()] if (m==i).any() else None) for i,slot in enumerate(body['material_slots'])])
write(R/'fit-source.json',dict(rows=reports,reference_pose_only=True,gameplay=False))
