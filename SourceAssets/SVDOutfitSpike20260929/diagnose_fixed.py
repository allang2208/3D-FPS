from pathlib import Path
s=Path('SourceAssets/ChainmailReloadFit20260929/diagnose.py').read_text();exec(s.split('report=')[0]);R=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDOutfitSpike20260929');poses=read(R/'poses.json');report={}
for file in R.glob('*_fixed.json'):
 if file.stem=='native':continue
 d=read(file)
 if not isinstance(d,dict) or 'positions' not in d:continue
 data=prepare(d);f=np.array(d['triangles']);e=np.unique(np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0);worst={}
 for pose in poses:
  mat={n:matrix(t) for n,t in pose['bones'].items()};pp=posed(data,mat);length=np.linalg.norm(pp[e[:,0]]-pp[e[:,1]],axis=1);i=length.argmax();kind='reload' if 'reload' in pose['clip'] else 'ADS_idle';row=worst.get(kind,{'max_cm':0})
  if length[i]>row['max_cm']:worst[kind]=dict(max_cm=float(length[i]),edge=e[i].tolist(),clip=pose['clip'],time=pose['time'],positions=pp[e[i]].tolist(),weights=[d['weights'][j] for j in e[i]])
 report[file.stem]=worst;print(file.stem,[(k,v['max_cm']) for k,v in worst.items()],flush=True)
 (R/'fixed-spikes.json').write_text(json.dumps(report,indent=2))
