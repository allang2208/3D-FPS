import json,gzip,numpy as np
from pathlib import Path
I=Path(__file__).parent/'Inputs'
for name in ('HK416','factory','extended','drum'):
 with gzip.open(I/(name+'_geometry.json.gz'),'rt',encoding='utf8') as f:d=json.load(f)
 idx=np.zeros((len(d['pos']),8),np.int32);w=np.zeros((len(d['pos']),8),np.float32)
 for i,rows in enumerate(d['weights']):
  for j,(bi,bw) in enumerate(sorted(rows,key=lambda x:-x[1])[:8]):idx[i,j]=bi;w[i,j]=bw
 np.savez_compressed(I/(name+'.npz'),pos=np.array(d['pos'],np.float32),tris=np.array(d['tris'],np.int32),bone_idx=idx,bone_w=w,bones=np.array(d['bones']))
 print('HK416_NATIVE_SOURCE_READY',name,len(d['pos']))
