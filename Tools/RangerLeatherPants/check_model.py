"""User-requested checks of the authored trousers and their native-fit variants."""
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/RangerLeatherPants20261021';OUT=R/'Review';OUT.mkdir(exist_ok=True)
rows=[]
for name in ('Jason','Jason_ShortBootsFit','Jason_HighBootsFit'):
    file=R/'Authored/ue_leather_pants'/(name+'.json');d=json.loads(file.read_bytes());p=np.array(d['positions']);f=np.array(d['triangles']);ns=np.array(d['normals']);uv=np.array(d['uv']);slots=np.array(d['triangle_materials'])
    cross=-np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]);area=np.linalg.norm(cross,axis=1)*.5;uvcross=np.abs(np.cross(uv[:,1]-uv[:,0],uv[:,2]-uv[:,0]))*.5
    corner_alignment=np.einsum('ij,ij->i',cross,ns.mean(1))/np.maximum(np.linalg.norm(cross,axis=1)*np.linalg.norm(ns.mean(1),axis=1),1e-12)
    weights=d['weights'];sums=np.array([sum(w.values()) for w in weights]);unknown=sorted(set(k for w in weights for k in w)-set(d['bones']));edges=np.sort(np.concatenate((f[:,[0,1]],f[:,[1,2]],f[:,[2,0]])),axis=1);_,counts=np.unique(edges,axis=0,return_counts=True)
    issues=[]
    for part in d['parts']:
        start=part['first_triangle'];end=start+part['triangles'];bad=(area[start:end]<1e-9)|(uvcross[start:end]<1e-12)|(corner_alignment[start:end]<-.01)
        if bad.any():issues.append(dict(name=part['name'],degenerate_faces=int(sum(area[start:end]<1e-9)),degenerate_uv=int(sum(uvcross[start:end]<1e-12)),opposed_normals=int(sum(corner_alignment[start:end]<-.01))))
    row=dict(profile=name,source_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),vertices=len(p),triangles=len(f),bounds_cm=[p.min(0).tolist(),p.max(0).tolist()],finite=bool(np.isfinite(p).all() and np.isfinite(ns).all() and np.isfinite(uv).all()),degenerate_faces=int(sum(area<1e-9)),degenerate_uv_faces=int(sum(uvcross<1e-12)),opposed_normals=int(sum(corner_alignment<-.01)),zero_normals=int(sum(np.linalg.norm(ns,axis=2).ravel()<.1)),max_weight_sum_error=float(abs(sums-1).max()),max_influences=max(map(len,weights)),unknown_bones=unknown,boundary_edges=int(sum(counts==1)),nonmanifold_edges=int(sum(counts>2)),issues=issues)
    rows.append(row);print(name,{k:v for k,v in row.items() if k not in ('issues','bounds_cm','source_sha256')},'problem parts',len(issues),flush=True)
textures=[]
for path in sorted((R/'Textures').glob('*.png')):
    with Image.open(path) as im:
        a=np.array(im);entry=dict(name=path.name,size=list(im.size),mode=im.mode)
        if 'Normal' in path.name:
            n=a.astype(float)/255*2-1;entry.update(normal_z_mean=float(n[:,:,2].mean()),normal_z_min=float(n[:,:,2].min()),mean_vector_length=float(np.linalg.norm(n,axis=2).mean()))
        textures.append(entry)
result=dict(scope='User requested offline model inspection; no UE or gameplay',models=rows,textures=textures)
(OUT/'geometry_report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
