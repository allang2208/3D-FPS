"""Quantify the requested isolated solve; the metrics are not rendered acceptance."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/BlueMageRobe20261018/StairRepair20261019'
label=sys.argv[1];d=json.loads((O/('simulation-'+label+'.json')).read_text());rest=np.asarray(d['rest']);faces=np.asarray(d['indices']).reshape(-1,3);hem=np.flatnonzero(rest[:,2]<rest[:,2].min()+.1)
boot=json.loads((P/'SourceAssets/BlueMageSetAudit20261019/Read/ue_blue_mage_boots.json').read_text());bp=np.asarray(boot['positions']);selected=np.flatnonzero(bp[:,2]>19)[::max(1,int((bp[:,2]>19).sum()/900))];groups={}
for out_i,i in enumerate(selected):
 for n,w in boot['weights'][i].items():
  ids,weights=groups.setdefault(n,([],[]));ids.append(out_i);weights.append(w)
for n,(ids,w) in groups.items():
 ids=np.array(ids);b=boot['bones'][n];groups[n]=(ids,np.array(w)[:,None],(bp[selected[ids]]-b['position'])@np.asarray(b['axes']).T)
def contains(q,p):
 tris=p[faces];result=[]
 for x,y,z in q:
  poly=tris[(tris[:,:,2].min(1)<=z)&(tris[:,:,2].max(1)>z)];cross=[]
  for a,b in ((0,1),(1,2),(2,0)):
   aa=poly[:,a];bb=poly[:,b];hit=((aa[:,2]>z)!=(bb[:,2]>z));t=(z-aa[hit,2])/(bb[hit,2]-aa[hit,2]);cross.append((np.flatnonzero(hit),aa[hit,:2]+(bb[hit,:2]-aa[hit,:2])*t[:,None]))
  seg={}
  for ids,pts in cross:
   for i,v in zip(ids,pts):seg.setdefault(i,[]).append(v)
  count=0
  for v in seg.values():
   if len(v)!=2:continue
   a,b=v
   if (a[1]>y)!=(b[1]>y) and x<a[0]+(b[0]-a[0])*(y-a[1])/(b[1]-a[1]):count+=1
  result.append(bool(count%2))
 return np.array(result)
rows=[]
for s in d['samples']:
 p=np.asarray(s['particles']);skin=np.asarray(s['skin']);bones={b['name']:b for b in s['bones']};bootposed=np.zeros((len(selected),3))
 for n,(ids,w,local) in groups.items():
  b=bones[n];bootposed[ids]+=((local*np.asarray(b['s']))@Rotation.from_quat(b['q']).as_matrix().T+b['p'])*w
 inside=contains(bootposed,p)
 a=p[faces[:,1]]-p[faces[:,0]];b=p[faces[:,2]]-p[faces[:,0]];area=np.linalg.norm(np.cross(a,b),axis=1)
 delta=p-skin
 rows.append({'frame':s['frame'],'finite':bool(np.isfinite(p).all()),'hem_max_lift_cm':float(delta[hem,2].max()),'hem_min_drop_cm':float(delta[hem,2].min()),'max_displacement_cm':float(np.linalg.norm(delta,axis=1).max()),'boot_shaft_outside':int((~inside).sum()),'boot_shaft_samples':len(inside),'tiny_triangles':int((area<.01).sum())})
report={'label':label,'mesh':d['mesh'],'scope':d.get('scope','No rendered staircase acceptance'),'frames':rows,'max_hem_lift_cm':max(r['hem_max_lift_cm'] for r in rows),'max_shaft_outside':max(r['boot_shaft_outside'] for r in rows),'finite':all(r['finite'] for r in rows)}
(O/('analysis-'+label+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='frames'},indent=2))
