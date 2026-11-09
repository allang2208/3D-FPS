"""Requested contact sweep on UE's evaluated skin, including V9 morphs."""
from pathlib import Path
import sys,json,pickle,numpy as np,trimesh
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'Repair06'))
from contact_sweep import intersect
r=Path(__file__).resolve().parent;folder=Path(sys.argv[1]);g=pickle.load(open(r/'geometry.pkl','rb'))
faces=np.fromfile(folder/'surface.indices',np.uint32).reshape(-1,3);mat=np.fromfile(folder/'surface.materials',np.uint32);left=np.fromfile(folder/'surface.left',np.uint8)>0
lf=faces[left[faces].all(1)];report={};views=json.loads((folder/'review.json').read_text(encoding='utf-8-sig'))['views']
for view in views:
    name=view['view'];v=np.fromfile(folder/(name+'.vertices'),np.float32).reshape(-1,3).astype(float);hand=v[lf];mi=hand.min(1);ma=hand.max(1)
    obstacles={slot:(v,faces[mat==i]) for i,slot in enumerate(g['slots']) if i not in (7,8,9,10) and not any(s in slot for s in ('__New','Glass','Reticle','Belt','Bullet'))}
    for file in folder.glob(name+'_SM*.vertices'):
        obstacles[file.stem.removeprefix(name+'_')]=(np.fromfile(file,np.float32).reshape(-1,3).astype(float),np.fromfile(file.with_suffix('.indices'),np.uint32).reshape(-1,3))
    results={}
    for obstacle,(p,fs) in obstacles.items():
        mesh=trimesh.Trimesh(p,fs,process=False);tri=p[fs];lo=tri.min((0,1));hi=tri.max((0,1));near=np.nonzero(((ma>=lo)&(mi<=hi)).all(1))[0];hits=[]
        for j in near:
            for k in mesh.triangles_tree.intersection(np.r_[mi[j],ma[j]]):
                if intersect(hand[j],tri[k]):hits.append(j);break
        if hits:
            solid=trimesh.Trimesh(p,fs,process=True);solid.remove_unreferenced_vertices();solid.fix_normals()
            record=dict(triangles=len(hits),closed_volume=bool(solid.is_volume))
            if solid.is_volume:
                points=v[np.unique(lf[hits])];dist=trimesh.proximity.signed_distance(solid,points)
                record['deepest_vertex_mm']=float(max(0.,dist.max())*10.)
            results[obstacle]=record
    record=dict(runtime_time=view['source_seconds'],action_time=view.get('action_seconds'),correctives=view['corrective_count'],collisions=results)
    report[name]=record;print(name,results,flush=True)
(folder/'native_contacts.json').write_text(json.dumps(report,indent=2))
