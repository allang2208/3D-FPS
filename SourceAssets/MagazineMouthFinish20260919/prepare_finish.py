"""Fit each original UV0 surface to its own rifle; no receiver atlas projection."""
import json
import numpy as np
from PIL import Image
from pathlib import Path
O=Path(__file__).parent;S=O.parent
UV=json.loads((O/'uv_samples.json').read_text())
def image(p):return np.array(Image.open(p).convert('RGB'),dtype=float)/255
def linear(v):return np.where(v<=.04045,v/12.92,((v+.055)/1.055)**2.4)
def median(v,w):
 return np.array([a[np.searchsorted(np.cumsum(w[ix])/sum(w),.5)] for i in range(v.shape[1]) for ix in [np.argsort(v[:,i])] for a in [v[ix,i]]])
def sample(a,gun):
 uv=np.array([p['uv'] for p in UV[gun]]);w=np.array([p['area'] for p in UV[gun]])
 p=a[np.clip(((1-uv[:,1])*a.shape[0]).astype(int),0,a.shape[0]-1),np.clip((uv[:,0]*a.shape[1]).astype(int),0,a.shape[1]-1)]
 return median(p,w)
paths={'M4':S/'M4Infima/SK_M4_Infima.fbm/Magazine Light_BaseColor.png','AKM':S/'AKMSoviet20260911/Source/ak47fbx_extracted/textures/AK_Base_color.png','QBZ':S/'QBZ191ContactWear20260913/Textures/T_QBZ191_Wear_Magazine_BaseColor.png'}
source={g:sample(linear(image(p)),g) for g,p in paths.items()}
akref=np.median(linear(image(S/'AKMArmSupport20260911/Metal/T_AKM_Mount_Base_color.png')).reshape(-1,3),axis=0)
m4ref=np.median(linear(image(S/'WeaponAttachmentFinish20260913/Textures/T_M4_Receiver_BaseColor.png')).reshape(-1,3),axis=0)
# QBZ's active receiver tint is a material parameter, not a texture filename.
r=json.loads((O/'material_sources.json').read_text())
qbbody=next(v for k,v in r['materials'].items() if 'Unified_M_QBZ191_Wear_Body_metal.' in k)
qbref=np.array(qbbody['parameters']['vector']['QBZ_SurfaceTint'][:3])
targets={'AKM':akref,'M4':m4ref,'QBZ':qbref}
result={}
for gun in paths:
 result[gun]={'source_basecolor':str(paths[gun]),'source_uv0_linear_median':source[gun].tolist(),'target_linear_color':targets[gun].tolist(),'linear_color_multiplier':(targets[gun]/np.maximum(source[gun],.0001)).tolist(),'material_identity':'steel' if gun=='AKM' else 'polymer','roughness_center':float(np.median(image(S/'AKMArmSupport20260911/Metal/T_AKM_Mount_Roughness.png'))) if gun=='AKM' else (.56 if gun=='M4' else .57),'metallic':float(np.median(image(S/'AKMArmSupport20260911/Metal/T_AKM_Mount_Metallic.png'))) if gun=='AKM' else 0}
result['AKM']['source_roughness_median']=float(sample(image(S/'AKMSoviet20260911/Source/ak47fbx_extracted/textures/AK_Roughness.png'),'AKM')[0])
result['M4']['source_roughness_median']=float(sample(image(S/'M4Infima/SK_M4_Infima.fbm/Magazine Light_Roughness.png'),'M4')[0])
result['QBZ']['source_roughness_median']=float(sample(image(S/'QBZ191ContactWear20260913/Textures/T_QBZ191_Wear_Magazine_ORM.png'),'QBZ')[1])
(O/'finish_profiles.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
