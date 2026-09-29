from pathlib import Path
s=Path('SourceAssets/ChainmailReloadFit20260929/diagnose.py').read_text();exec(s.split('report=')[0])
R=Path('SourceAssets/SVDRuntimeDiagnosis20260929');poses=read(Path('SourceAssets/SVDOutfitSpike20260929/poses.json'));report={}
for file in R.glob('*LOD*.json'):
 d=read(file);data=prepare(d);f=np.array(d['triangles']);e=np.unique(np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0);worst={'rest_max_cm':float(np.linalg.norm(data[0][e[:,0]]-data[0][e[:,1]],axis=1).max())}
 for pose in poses:
  mat={n:matrix(t) for n,t in pose['bones'].items()};pp=posed(data,mat);length=np.linalg.norm(pp[e[:,0]]-pp[e[:,1]],axis=1);i=length.argmax();kind='reload' if 'reload' in pose['clip'] else 'ADS_idle';row=worst.get(kind,{'max_cm':0})
  if length[i]>row['max_cm']:worst[kind]=dict(max_cm=float(length[i]),edge=e[i].tolist(),clip=pose['clip'],time=pose['time'],positions=pp[e[i]].tolist(),weights=[d['weights'][j] for j in e[i]])
 report[file.stem]=worst;print(file.stem,worst['rest_max_cm'],[(k,v['max_cm']) for k,v in worst.items() if isinstance(v,dict)],flush=True)
 (R/'lod-spikes.json').write_text(json.dumps(report,indent=2))
