"""Local thumb-root tissue clearance; retain the accepted bone weights and seam."""
import json,os
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';src=R/'ClearanceReview/A762_skin_before_thumb_web.json';target=R/'SkinCoverage/A762_review.json'
d=json.loads(src.read_text());p=np.asarray(d['positions']);normal=np.zeros_like(p);t=np.asarray(d['triangles'])
for k in range(3):np.add.at(normal,t[:,k],np.asarray(d['normals'])[:,k])
normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-12)
def smooth(a,b,v):x=np.clip((v-a)/(b-a),0,1);return x*x*(3-2*x)
thumb=np.array([w.get('thumb_02_l',0)+w.get('thumb_03_l',0) for w in d['weights']]);total=thumb+np.array([w.get('thumb_01_l',0) for w in d['weights']])
mask=smooth(.15,.30,thumb)*(1-smooth(.65,.95,thumb))*smooth(.50,.80,total)
depth=float(os.environ.get('FINGERLESS_THUMB_TRIM_CM','.25'));p-=normal*(depth*mask)[:,None];d['positions']=p.tolist();d['thumb_root_relief_cm']=depth
target.write_text(json.dumps(d,separators=(',',':')))
for path in (R/'FingerClearance').glob('A762__vertical*.json'):
    c=json.loads(path.read_text())
    if 'corrections' not in c:continue
    c['corrections'].pop('thumb_01_l',None);c['corrections'].pop('thumb_02_l',None);path.write_text(json.dumps(c,indent=2))
print('THUMB_ROOT_LOCAL_VOLUME',depth,int((mask>0).sum()))
