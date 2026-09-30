"""Magazine-locked grasp, native full arm FK and separated release/regrip."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
O=Path(__file__).parent;S=json.loads((O/'sources.json').read_text());C=json.loads((O/'contact.json').read_text());K=O/'Keys';K.mkdir(exist_ok=True)
bones=S['rigs']['201']['bones'];G=np.array(C['hand_in_mag']);fingers=C['finger_local']
def mat(t):
 m=np.eye(4);m[:3,:3]=R.from_quat(t['q']).as_matrix()@np.diag(t['s']);m[:3,3]=t['p'];return m
def unpack(m):
 s=np.linalg.norm(m[:3,:3],axis=0);return {'p':m[:3,3].tolist(),'q':R.from_matrix(m[:3,:3]/s).as_quat().tolist(),'s':s.tolist()}
def ramp(f,a,b):
 t=np.clip((f-a)/(b-a),0,1);return float(t*t*t*(t*(t*6-15)+10))
def mixq(a,b,w):
 a=np.array(a);b=np.array(b);dot=np.dot(a,b)
 if dot<0:b=-b;dot=-dot
 if dot>.9995:q=a*(1-w)+b*w
 else:
  angle=np.arccos(np.clip(dot,-1,1));q=(np.sin((1-w)*angle)*a+np.sin(w*angle)*b)/np.sin(angle)
 return (q/np.linalg.norm(q)).tolist()
names=[n for n in bones if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky'))]
report={'method':'Approved SVD partial wrap on native AKM full FK arm; fixed magazine-space contact; open fingers before outward retreat; preserve every bone length, scale, right arm, weapon and mechanism curve',
 'phases_120hz':{'approach':[12,44],'grasp':[44,237],'open_fingers':[237,252],'outward_retreat':[244,262],'return_to_support':[255,294]},'clips':{},'runtime_tested':False}
for key in ['reload','reload_empty']:
 donor=json.loads((O/'Sources'/('akm_base_'+key+'.json')).read_text())['poses']
 for family in ['base','vertical','canted','prism','angled']:
  spec=S['clips']['201_'+family+'_'+key];src=json.loads(Path(spec['file']).read_text());rows=src['poses'];tracks={n:[] for n in names}
  for i,row in enumerate(rows):
   f=spec['seconds']*i/(len(rows)-1)*120.;d=donor[min(i,len(donor)-1)]
   weight=ramp(f,12,44)*(1-ramp(f,255,294))
   # Whole native chain gets one rigid correction. There is no independent
   # wrist, elbow, shoulder or auxiliary-twist solve.
   target=mat(row['WPN_SOCKET_Magazine']['world'])@G
   away=np.eye(4);away[:3,3]=[.055*ramp(f,244,262),0,-.014*ramp(f,248,266)]
   target=mat(row['WPN_SOCKET_Magazine']['world'])@away@G
   delta=target@np.linalg.inv(mat(d['hand_l']['world']))
   parent=bones['clavicle_l']['parent']
   clav=unpack(np.linalg.inv(mat(row[parent]['world']))@delta@mat(d['clavicle_l']['world']))
   for n in names:
    old=row[n]['local'];goal=clav if n=='clavicle_l' else d[n]['local'];w=weight
    if n in fingers:
     # Fixed approved thumb; bounded grouped flex for the wider 201 shell.
     # Release follows the donor's natural open hand, before arm withdrawal.
     goal=dict(fingers[n]);opened=donor[264][n]['local']
     goal['q']=mixq(goal['q'],opened['q'],ramp(f,237,252))
    val={'p':list(old['p']),'s':list(old['s']),'q':mixq(old['q'],goal['q'],w) if w else list(old['q'])}
    if n=='clavicle_l' and w:val['p']=(np.array(old['p'])*(1-w)+np.array(goal['p'])*w).tolist()
    if tracks[n] and np.dot(tracks[n][-1]['q'],val['q'])<0:val['q']=(-np.array(val['q'])).tolist()
    tracks[n].append(val)
  file=K/(family+'_'+key+'.json');file.write_text(json.dumps(tracks,separators=(',',':')))
  destination=f'/Game/Weapons/LMG201/Magazine24/Animations/{family}/A_LMG201_{family}_{key}'
  report['clips'][family+'/'+key]={'source':spec['asset'],'source_sha256':spec['sha256'],'keys':str(file),'destination':destination,'count':spec['count'],'seconds':spec['seconds'],'fps':spec['fps'],'donor':S['clips']['akm_base_'+key]['asset']}
  print('MAGAZINE24_AUTHORED',family,key,flush=True)
(O/'authoring.json').write_text(json.dumps(report,indent=2))
