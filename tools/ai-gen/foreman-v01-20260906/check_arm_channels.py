import json,struct,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parent
def channels(file):
 raw=file.read_bytes();size=struct.unpack_from('<I',raw,12)[0];d=json.loads(raw[20:20+size]);b=raw[28+size:]
 def read(i):
  a=d['accessors'][i];v=d['bufferViews'][a['bufferView']];n={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]
  return np.frombuffer(b,dtype='<f4',count=a['count']*n,offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,n)
 out={}
 for anim in d['animations']:
  for c in anim['channels']:
   s=anim['samplers'][c['sampler']];k=(anim['name'],d['nodes'][c['target']['node']]['name'],c['target']['path']);out[k]=(read(s['input']),read(s['output']))
 return out
a=channels(R/'foreman-whip-v02.glb');b=channels(R/'foreman-arm-v03.glb');assert a.keys()==b.keys()
changed=[]
for k,(ta,va) in a.items():
 tb,vb=b[k];assert np.allclose(ta,tb),k
 if not np.allclose(va,vb,atol=1e-5):
  assert k[0]=='Attack' and k[1] in ['upper_arm.L','forearm.L','hand.L'],k
  assert np.allclose(va[[0,-1]],vb[[0,-1]],atol=1e-5),('endpoints',k)
  changed.append(k)
report={'unchanged_channels':len(a)-len(changed),'changed_channels':changed,'attack_endpoints_preserved':True}
(R/'arm-channel-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
