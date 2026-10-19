"""Requested inspection of the repaired sleeve topology and cloth crossings."""
import json,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/GarmentSleeveRepair20261018'
results=[]
for item in ('ue_field_sweater','ue_field_sweater_charcoal','ue_chainmail_shirt'):
    for file in sorted((R/'Authored'/item).glob('*.json')):
        d=json.loads(file.read_text());p=np.array(d['positions']);f=np.array(d['triangles']);m=np.array(d['triangle_materials'])
        _,ix,remap=np.unique(np.round(p,5),axis=0,return_index=True,return_inverse=True);wf=remap[f]
        edges=np.sort(np.concatenate([wf[:,[0,1]],wf[:,[1,2]],wf[:,[2,0]]]),axis=1);_,count=np.unique(edges,axis=0,return_counts=True)
        # Ring-to-ring contact is intentional interlaced metal. The two largest
        # connected shells are the continuous sleeves, including their cuffs.
        selected=np.arange(len(f))
        if item=='ue_chainmail_shirt':
            parent=list(range(len(ix)))
            def root(i):
                while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
                return i
            for tri in wf:
                a=root(int(tri[0]))
                for v in tri[1:]:parent[root(int(v))]=a
            component=np.array([root(int(tri[0])) for tri in wf]);labels,counts=np.unique(component,return_counts=True)
            main=labels[counts>1000]
            selected=np.where(np.isin(component,main))[0]
        tf=wf[selected];tree=BVHTree.FromPolygons([Vector(v) for v in p[ix]],tf.tolist(),all_triangles=True,epsilon=0)
        bad=[(a,b) for a,b in tree.overlap(tree) if a<b and not set(tf[a])&set(tf[b])]
        report=dict(item=item,profile=file.stem,vertices=len(p),triangles=len(f),finite=bool(np.isfinite(p).all()),open_edges=int(sum(count==1)),nonmanifold_edges=int(sum(count>2)),duplicate_faces=int(len(f)-len(np.unique(np.sort(wf,axis=1),axis=0))),max_edge_cm=float(np.linalg.norm(p[f]-p[np.roll(f,1,axis=1)],axis=2).max()),cloth_intersections=len(bad),intersection_examples=[[int(selected[a]),int(selected[b])] for a,b in bad[:8]])
        results.append(report);print(item,file.stem,report['open_edges'],report['nonmanifold_edges'],report['duplicate_faces'],report['cloth_intersections'],flush=True)
        (R/'authored_inspection.json').write_text(json.dumps(results,indent=2))
