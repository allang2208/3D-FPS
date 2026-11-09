"""Triangle contact sweep against both actual magazine bodies and receiver."""
from pathlib import Path
import sys,pickle,json,numpy as np,trimesh
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r.parent/'Repair06'));from contact_sweep import intersect
label=sys.argv[1] if len(sys.argv)>1 else 'before';d=pickle.load(open(r/(label+'_surfaces.pkl'),'rb'));g=pickle.load(open(r/'geometry.pkl','rb'))
faces=d['allfaces'];left=d['left'];lf=faces[left[faces].all(1)];report={};colliders={}
for key,s in d['samples'].items():
    if '--30' in sys.argv and not key.startswith('30_'):continue
    t=float(key.split('_')[1])
    if t in (0,3.8):continue
    hand=s['vertices'][lf];lo=hand.min(1);hi=hand.max(1);result={}
    objects=dict(s['parts']);objects['Receiver']=dict(vertices=s['vertices'],faces=faces[d['sections']==g['slots'].index('M249_Factory_Receiver')])
    for name,obj in objects.items():
        v=np.array(obj['vertices']);f=np.array(obj['faces'])
        if name not in colliders:
            m=trimesh.Trimesh(v.copy(),f.copy(),process=False);colliders[name]=(m,m.triangles_tree,v[0].copy(),v[f].copy())
        m,tree,origin,tri=colliders[name];delta=v[0]-origin;testhand=hand-delta;testlo=lo-delta;testhi=hi-delta;b0=tri.min((0,1));b1=tri.max((0,1));ids=np.nonzero(((testhi>=b0)&(testlo<=b1)).all(1))[0]
        if not len(ids):continue
        hits=[];bones=set()
        for j in ids:
            for k in tree.intersection(np.r_[testlo[j],testhi[j]]):
                if intersect(testhand[j],tri[k]):hits.append(j);bones.update(g['names'][i] for i in d['dominant'][lf[j]]);break
        if hits:result[name]=dict(triangles=len(hits),bones=sorted(bones))
    report[key]=result;print(key,result,flush=True)
(r/(label+'_contacts.json')).write_text(json.dumps(report,indent=2))
