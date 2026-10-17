import bpy,json,sys,numpy as np
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;UC=O.parent/'M870UrbanAnimations20261015';sys.path.insert(0,str(UC))
from read_inputs import smd
d=json.loads((O/'reference_poses.json').read_text());a={n:Matrix(m) for n,m in d['rest'].items()};b=smd(UC/'Original/870/shotgun.smd')['rows'][0]
ns=[n for n in b if n in a and n.startswith('ValveBiped.')]
x=np.array([a[n].translation for n in ns]);y=np.array([b[n].translation for n in ns]);xc=x.mean(0);yc=y.mean(0)
uu,ss,vv=np.linalg.svd((x-xc).T@(y-yc));rr=vv.T@uu.T
if np.linalg.det(rr)<0:vv[-1]*=-1;rr=vv.T@uu.T
scale=np.sum((x-xc)@rr.T*(y-yc))/np.sum((x-xc)**2);t=yc-scale*rr@xc;C=np.eye(4);C[:3,:3]=scale*rr;C[:3,3]=t
report={'blend_to_smd':C.tolist(),'scale':float(scale),'rest_position_max_error_mm':float(np.max(np.linalg.norm(x@C[:3,:3].T+t-y,axis=1))*1000),'pose_samples':[]}
ss=smd(UC/'Original/870/anims/reloadinsert.smd')['rows']
for f in (0,6,12,20,26):
 p={n:Matrix(m) for n,m in d['clips']['reloadinsert']['rows'][f].items()}
 err={n:float(np.linalg.norm(C[:3,:3]@np.array(p[n].translation)+t-np.array(ss[f][n].translation))*1000) for n in ns}
 report['pose_samples'].append({'frame':f,'max_position_error_mm':max(err.values()),'right_hand_error_mm':err['ValveBiped.Bip01_R_Hand']})
fore=np.array(a['ValveBiped.Bip01_R_Hand'].translation)-a['ValveBiped.Bip01_R_Forearm'].translation
for n in ('Forearm','Ulna','Wrist','Hand'):
 p=np.array(a['ValveBiped.Bip01_R_'+n].translation)-a['ValveBiped.Bip01_R_Forearm'].translation
 print('SOURCE_STATION',n,float(p@fore/(fore@fore)),flush=True)
(O/'reference_registration.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
