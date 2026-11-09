"""Stable triangle-level native surface sweep using Blender's BVH backend."""
import pickle,json,sys,numpy as np
from pathlib import Path
from mathutils.bvhtree import BVHTree
r=Path(__file__).parent;label=next((x.split('=')[1] for x in sys.argv if x.startswith('--label=')),'candidate')
d=pickle.load(open(r/(label+'_surfaces.pkl'),'rb'));g=pickle.load(open(r/'geometry.pkl','rb'));faces=d['allfaces'];lf=faces[d['left'][faces].all(1)];handids,localfaces=np.unique(lf,return_inverse=True);localfaces=localfaces.reshape(-1,3).tolist();report={};cache={}
for key,s in d['samples'].items():
    if float(key.split('_')[1]) in (0.,3.8):continue
    objects=dict(s['parts']);objects['Receiver']=dict(vertices=s['vertices'],faces=faces[d['sections']==g['slots'].index('M249_Factory_Receiver')]);row={}
    for name,p in objects.items():
        v=np.array(p['vertices']);f=np.array(p['faces'])
        if name not in cache:cache[name]=(v[0].copy(),BVHTree.FromPolygons(v.tolist(),f.tolist(),all_triangles=True,epsilon=0.0))
        origin,tree=cache[name];hand=BVHTree.FromPolygons((s['vertices'][handids]-(v[0]-origin)).tolist(),localfaces,all_triangles=True,epsilon=0.0)
        hits=hand.overlap(tree)
        if hits:
            ids=np.unique([i for i,j in hits]);bones=sorted({g['names'][i] for i in d['dominant'][lf[ids]].ravel()});row[name]=dict(triangles=len(ids),bones=bones)
    report[key]=row;print('CONTACT',key,row,flush=True)
(r/(label+'_contacts_bvh.json')).write_text(json.dumps(report,indent=2))
print('NATIVE_SURFACE_CONTACT_SWEEP_COMPLETE',label,flush=True)
