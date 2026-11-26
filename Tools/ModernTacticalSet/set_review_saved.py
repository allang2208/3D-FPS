"""Check the freshly read saved meshes, their LODs and source correspondence."""
import json,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'SetFitReview20261115'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=read(R/'plan.json');rows=[]
for row in plan['rows']:
    file=R/'Captured'/(row['key']+'.json')
    if not file.exists():raise RuntimeError('Read pending: '+row['key'])
    c=read(file);d=c.get('source_model',c['lods'][0]);p=np.array(d['positions']);f=np.array(d['triangles'],int)
    area=np.linalg.norm(np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]),axis=1)*.5
    edge=np.max(np.stack([np.linalg.norm(p[f[:,a]]-p[f[:,b]],axis=1) for a,b in [(0,1),(1,2),(2,0)]]),axis=0)
    needles=(edge>1)&(edge**2/np.maximum(2*area,1e-12)>250)
    report=dict(key=row['key'],role=row['role'],rig=row['rig'],asset=row['path'],asset_sha256=c['asset_sha256'],vertices=len(p),triangles=len(f),nonfinite_positions=int((~np.isfinite(p)).any(1).sum()),degenerate_triangles=int((area<1e-10).sum()),needle_candidates=int(needles.sum()),needle_candidates_need_visual_review=True,max_edge_cm=float(edge.max()),materials_missing=sum(x is None for x in c['materials']),lods=[])
    if 'weights' in d:
        boneids={b['index'] for b in d['bones']};sums=np.array([sum(w for bi,w in ws) for ws in d['weights']]);invalid=sum(any(bi not in boneids or not np.isfinite(w) or w<0 for bi,w in ws) for ws in d['weights'])
        report['binding']=dict(unweighted=int((sums<.01).sum()),invalid_vertices=invalid,max_normalization_error=float(abs(sums-1).max()),max_influences=max(map(len,d['weights'])),source_model_only=True)
    if 'normals' in d:
        ns=np.array(d['normals']);uv=np.array(d['uv']);report['nonfinite_normals']=int((~np.isfinite(ns)).any(2).any(1).sum());report['nonfinite_uv']=int((~np.isfinite(uv)).any(2).any(1).sum())
    tree=cKDTree(p)
    for lod in c['lods']:
        if 'error' in lod:report['lods'].append(lod);continue
        lp=np.array(lod['positions']);dist=tree.query(lp,workers=2)[0]
        report['lods'].append(dict(lod=lod['lod'],vertices=len(lp),triangles=len(lod['triangles']),source_vertex_distance_max_cm=float(dist.max()),source_vertex_distance_p99_cm=float(np.quantile(dist,.99)),nonfinite_positions=int((~np.isfinite(lp)).any(1).sum())))
    candidates=[]
    for candidate in row['candidates']:
        if not Path(candidate).exists():continue
        author=read(candidate);all_ap=np.array(author['positions']);ap=all_ap[np.unique(np.array(author['triangles'],int))];dist=tree.query(ap,workers=2)[0];back=cKDTree(ap).query(p,workers=2)[0]
        candidates.append(dict(file=candidate,sha256=sha(candidate),max_vertex_distance_cm=float(max(dist.max(),back.max())),triangle_count_difference=len(f)-len(author['triangles']),metadata_match=sha(candidate) in c['metadata'].values(),unused_author_vertices_excluded=len(all_ap)-len(ap)))
    report['source_candidates']=candidates
    rows.append(report);print('SAVED_MODEL',row['key'],len(f),'degenerate',report['degenerate_triangles'],flush=True)
summary=dict(completed=True,rows=rows,assets=len(rows),render_lods=sum('triangles' in l for r in rows for l in r['lods']),gameplay=False,poses='reference pose only')
(R/'saved-review.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print('SAVED_REVIEW_COMPLETE',len(rows),flush=True)
