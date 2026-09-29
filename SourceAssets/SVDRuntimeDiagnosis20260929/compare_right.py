from pathlib import Path
exec(Path('SourceAssets/ChainmailReloadFit20260929/diagnose.py').read_text().split('report=')[0])
from scipy.spatial import cKDTree
R=Path('SourceAssets/SVDRuntimeDiagnosis20260929');old=Path('SourceAssets/SVDOutfitSpike20260929')
a=read(old/'bare.json');b=read(R/'ue_chainmail_shirt_rig_meshes_LOD0.json');pa=prepare(a);pb=prepare(b)
idsa=np.array([i for i,w in enumerate(a['weights']) if sum(v for n,v in w.items() if n.endswith('_r'))>.5]);idsb=np.array([i for i,w in enumerate(b['weights']) if sum(v for n,v in w.items() if n.endswith('_r'))>.5]);out=[]
for pose in read(old/'poses.json'):
 mat={n:matrix(t) for n,t in pose['bones'].items()};p=posed(pa,mat);q=posed(pb,mat);dist,ids=cKDTree(p[idsa]).query(q[idsb]);j=dist.argmax();out.append(dict(clip=pose['clip'],time=pose['time'],max_distance=float(dist[j]),vertex=int(idsb[j]),position=q[idsb[j]].tolist(),nearest=p[idsa[ids[j]]].tolist(),weights=b['weights'][idsb[j]]))
out.sort(key=lambda x:x['max_distance'],reverse=True);(R/'right-arm-distance.json').write_text(json.dumps(out,indent=2));print(json.dumps(out[:3],indent=2))
