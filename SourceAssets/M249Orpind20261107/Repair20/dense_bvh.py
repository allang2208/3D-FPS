"""120 Hz complete contact sweep of both actions, five grip layers and both magazines."""
import pickle,json,sys,numpy as np
from pathlib import Path
from mathutils import Quaternion
from mathutils.bvhtree import BVHTree
r=Path(__file__).parent;label=next((s.split('=')[1] for s in sys.argv if s.startswith('--label=')),'candidate')
g=pickle.load(open(r.parent/'Repair19/geometry.pkl','rb'));cache=pickle.load(open(r/(label+'_world.pkl'),'rb'));sur=pickle.load(open(r.parent/'Repair19/saved_surfaces.pkl','rb'));ns=g['names'];ix={n:i for i,n in enumerate(ns)}
def matrix(a):
    m=np.eye(4);m[:3,:3]=np.array(Quaternion((a[6],*a[3:6])).to_matrix())*a[7:];m[:3,3]=a[:3];return m
ib=np.linalg.inv(np.array([matrix(a) for a in g['bind']]))
dom=np.array([max(ws,key=lambda q:q[1])[0] for ws in g['weights']]);left=np.array([n.endswith('_l') for n in ns])[dom];faces=np.array(g['faces']);lf=faces[left[faces].all(1)];ids,ff=np.unique(lf,return_inverse=True);ff=ff.reshape(-1,3);v=np.array(g['vertices'])[ids];groups={}
for j,i in enumerate(ids):
    for b,weight in g['weights'][i]:
        js,pts=groups.setdefault(b,([],[]));js.append(j);pts.append(np.r_[v[j],1]*weight)
groups=[(b,np.array(js),np.array(pts)) for b,(js,pts) in groups.items()]
trees={name:BVHTree.FromPolygons(part['vertices'],part['faces'],all_triangles=True) for name,part in g['parts'].items()}
source=sur['samples']['30_0.72'];receiver=faces[np.array(g['sections'])==g['slots'].index('M249_Factory_Receiver')];trees['Receiver']=BVHTree.FromPolygons(source['vertices'].tolist(),receiver.tolist(),all_triangles=True)
report={};sample_count=0
for key,data in cache.items():
    if not key.startswith('side_'):continue
    hits=[]
    for k,t in enumerate(data['times']):
        w=data['world'][k];xf=w@ib;p=np.zeros_like(v)
        for b,js,pts in groups:p[js]+=pts@xf[b,:3,:].T
        row={}
        for bone,parts in [('WPN_root',('SM_M249_SidePort','Receiver')),('WPN_SOCKET_Magazine',('SM_m249_side_mag_30','SM_m249_side_mag_45'))]:
            m=w[ix[bone]];rot=m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0);local=(p-m[:3,3])@rot;hand=BVHTree.FromPolygons(local.tolist(),ff.tolist(),all_triangles=True)
            for name in parts:
                overlaps=hand.overlap(trees[name])
                if overlaps:
                    rows=np.unique([a for a,b in overlaps]);row[name]=dict(triangles=len(rows),bones=sorted({ns[i] for i in dom[lf[rows]].ravel()}))
        sample_count+=1
        if row:hits.append(dict(time=float(t),contacts=row))
    report[key]=hits;print('DENSE_CONTACT',key,len(hits),'frames',flush=True)
(r/(label+'_dense_contacts.json')).write_text(json.dumps(dict(hz=120,samples=sample_count,results=report,correctives_included=False),indent=2))
print('DENSE_CONTACT_SWEEP_SAVED',sample_count,flush=True)
