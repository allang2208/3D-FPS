import json,numpy as np
from pathlib import Path
O=Path(__file__).parent;C=json.loads((O/'inputs.json').read_text());result={}
for key,row in C['meshes'].items():
 with (O/'Input'/(key+'.bin')).open('rb') as f:
  h=json.loads(f.readline());nv=h['vertices'];nt=h['triangles']
  pos=np.fromfile(f,'<f4',nv*3).reshape(-1,3);tri=np.fromfile(f,'<i4',nt*3).reshape(-1,3);mids=np.fromfile(f,'<i4',nt)
  ns=np.fromfile(f,'<f4',nt*9).reshape(-1,3,3);uv=np.fromfile(f,'<f4').reshape(h['uv_sets'],nt,3,2)
 r={}
 for i,s in enumerate(h['slots']):
  selected=mids==i;u=uv[:,selected];a=u[:,:,1]-u[:,:,0];b=u[:,:,2]-u[:,:,0];det=a[:,:,0]*b[:,:,1]-a[:,:,1]*b[:,:,0]
  r[s]={'faces':int(selected.sum()),'uv_collapsed':[int(x) for x in (abs(det)<1e-12).sum(axis=1)],'zero_normals':int((np.linalg.norm(ns[selected],axis=2)<.5).sum()),'bounds':[pos[tri[selected]].min(axis=(0,1)).tolist(),pos[tri[selected]].max(axis=(0,1)).tolist()]}
 result[key]=r
(O/'source_diagnosis.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
for key in ['M16_stock','M16_balanced']:
 for p in C['meshes'][key]['materials']:
  print('\nMATERIAL',p)
  m=C['materials'][p]
  while m['class']!='Material':print('PARENT',m['parent']);m=C['materials'][m['parent']]
  print(json.dumps([n for n in m['nodes'] if 'texture' in n['properties'] or 'coordinate_index' in n['properties'] or n['class'].endswith('Custom')],indent=2))
