"""Reuse accepted complete AKM drum motion; adapt only host contacts/returns."""
import json,gzip
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
O=Path(__file__).parent;S=json.loads((O/'sources.json').read_text());G=json.loads((O/'model.json').read_text());K=O/'Keys';K.mkdir(exist_ok=True)
def read(key):
 with gzip.open(S['clips'][key]['file'],'rt') as f:return json.load(f)
def mat(t):
 m=np.eye(4);m[:3,:3]=R.from_quat(t['q']).as_matrix()@np.diag(t['s']);m[:3,3]=t['p'];return m
def unpack(m):
 s=np.linalg.norm(m[:3,:3],axis=0);return {'p':m[:3,3].tolist(),'q':R.from_matrix(m[:3,:3]/s).as_quat().tolist(),'s':s.tolist()}
def ramp(t,a,b):
 x=float(np.clip((t-a)/(b-a),0,1));return x*x*x*(x*(x*6-15)+10)
def mixq(a,b,w):
 a=np.array(a);b=np.array(b);dot=np.dot(a,b)
 if dot<0:b=-b;dot=-dot
 if dot>.9995:q=a*(1-w)+b*w
 else:
  v=np.arccos(np.clip(dot,-1,1));q=(np.sin((1-w)*v)*a+np.sin(w*v)*b)/np.sin(v)
 return (q/np.linalg.norm(q)).tolist()
bones=S['rigs']['201']['bones'];names=[n for n in bones if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky'))]
offset=np.eye(4);v=G['donor_shell_offset_root_blender_m'];offset[:3,3]=[v[0],-v[1],v[2]]
out={'method':'Installed AKM PalmGripV3 complete native left-arm FK; donor magazine track and timing; current 201 right arm and mechanisms retained; only rigid shell contact offset and approach/return to each current 201 support pose','clips':{},'runtime_tested':False}
for key in ['reload','reload_empty']:
 donor=read('akm_base_'+key);empty=key.endswith('empty');release=220 if empty else 236;return_begin=release+(.4*(256-220 if empty else 278-236));return_end=286 if empty else 300
 for family in ['base','vertical','canted','prism','angled']:
  label='201_'+family+'_'+key;meta=S['clips'][label];rows=read(label);idle=read('201_'+family+'_idle')[0];tracks={n:[] for n in names+['WPN_SOCKET_Magazine']}
  rootidle=np.linalg.inv(mat(idle['WPN_root']['world']))@mat(idle['clavicle_l']['world'])
  for i,row in enumerate(rows):
   f=i*120*meta['seconds']/max(1,len(rows)-1);d=donor[min(i,len(donor)-1)];root=mat(row['WPN_root']['world']);par=bones['clavicle_l']['parent'];pinv=np.linalg.inv(mat(row[par]['world']))
   # Identical native reference bones. Preserve donor local rotations, including
   # every twist/helper/finger; only the whole chain's contact frame moves.
   contact=pinv@root@offset@np.linalg.inv(mat(d['WPN_root']['world']))@mat(d['clavicle_l']['world'])
   support=unpack(pinv@root@rootidle);goal=unpack(contact)
   enter=ramp(f,12,36);leave=ramp(f,return_begin,return_end);weight=enter*(1-leave)
   for n in names:
    a=support if n=='clavicle_l' else idle[n]['local'];b=goal if n=='clavicle_l' else d[n]['local'];w=weight
    # Fingers retain donor opening while the palm clears the drum; close on
    # the host support only near the end of the returning arm movement.
    if n.startswith(('thumb','index','middle','ring','pinky')):w=enter*(1-ramp(f,return_begin+12,return_end))
    value={'p':list(row[n]['local']['p']),'s':list(row[n]['local']['s']),'q':mixq(a['q'],b['q'],w)}
    if n=='clavicle_l':value['p']=(np.array(a['p'])*(1-w)+np.array(b['p'])*w).tolist()
    if tracks[n] and np.dot(tracks[n][-1]['q'],value['q'])<0:value['q']=(-np.array(value['q'])).tolist()
    tracks[n].append(value)
   tracks['WPN_SOCKET_Magazine'].append(d['WPN_SOCKET_Magazine']['local'])
  path=K/(family+'_'+key+'.json.gz')
  with gzip.open(path,'wt',encoding='utf8') as f:json.dump(tracks,f,separators=(',',':'))
  out['clips'][family+'/'+key]={'source':meta['asset'],'source_sha256':meta['sha256'],'donor':S['clips']['akm_base_'+key]['asset'],'donor_sha256':S['clips']['akm_base_'+key]['sha256'],'destination':f'/Game/Weapons/LMG201/Drum46/Animations/{family}/A_LMG201_{family}_drum_{key}','keys':str(path),'seconds':meta['seconds'],'count':meta['count'],'fps':meta['fps'],'return_120hz':[return_begin,return_end]}
  print('DRUM46_ANIMATION_AUTHORED',family,key,flush=True)
(O/'animations.json').write_text(json.dumps(out,indent=2))
