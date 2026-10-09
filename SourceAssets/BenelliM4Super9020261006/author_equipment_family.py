"""Fit source garments to native rigs and existing equipment to the Super90 rig."""
import json,numpy as np
from pathlib import Path
O=Path(__file__).parent;X=O/'EquipmentSources';Y=O/'EquipmentAuthored';Y.mkdir(exist_ok=True)
a=json.loads((O/'authoring.json').read_text());C=np.diag([100.,-100.,100.,1.]);Ci=np.linalg.inv(C)
warp={n:C@np.array(m)@Ci for n,m in a['v7_to_native_warp'].items()}
ref=json.loads((X/'rig_M4.json').read_text());manifest=[]
def old_name(n):
 if n.startswith('lowerarm_aux_'):return 'lowerarm_'+n[-1]
 return n

def target_name(n,bones):
 # The source artist skins the elbow end of the forearm to twist station 1.
 # lowerarm itself is the hinge/controller, not the proximal sleeve skin bone.
 if n in ('lowerarm_l','lowerarm_r') and 'lowerarm_aux_'+n[-1] in bones:return 'lowerarm_aux_'+n[-1]
 if n in bones:return n
 if '_twist_' in n or n.startswith('lowerarm_aux_'):return n.split('_')[0]+'_'+n[-1]
 if '_metacarpal_' in n:return n.split('_')[0]+'_01_'+n[-1]
 if n.startswith('spine_'):return 'spine_03'
 return n

def frame(bones,n):
 p=np.array(bones[n]['position']);side=n[-1];nxt=None
 if n.startswith('clavicle'):nxt='upperarm_'+side
 elif n.startswith('upperarm'):nxt='lowerarm_'+side
 elif n.startswith('lowerarm'):nxt='hand_'+side
 elif n.startswith('hand_'):nxt='middle_01_'+side
 elif '_metacarpal_' in n:nxt=n.split('_')[0]+'_01_'+side
 elif n.split('_')[0] in ('thumb','index','middle','ring','pinky'):
  k=int(n.split('_')[1]);nxt=n.split('_')[0]+'_%02d_'%(k+1)+side if k<3 else None
 if nxt in bones:x=np.array(bones[nxt]['position'])-p
 elif '_03_' in n and n.replace('_03_','_02_') in bones:x=p-np.array(bones[n.replace('_03_','_02_')]['position'])
 else:x=np.array(bones[n]['axes'][0]);x=x/np.linalg.norm(x)*2.5
 width=np.array(bones['index_01_'+side]['position'])-bones['pinky_01_'+side]['position'];forward=np.array(bones['middle_01_'+side]['position'])-bones['hand_'+side]['position'];z=np.cross(forward,width);z/=max(np.linalg.norm(z),1e-8);length=max(np.linalg.norm(x),.5);x/=max(np.linalg.norm(x),1e-8);y=np.cross(z,x);y/=max(np.linalg.norm(y),1e-8);z=np.cross(x,y);m=np.eye(4);m[:3,:3]=np.column_stack([x,y,z]);m[:3,3]=p;return m,length,np.linalg.norm(width)

def fit(data,transforms,rename,binding,profile,item):
 ps=np.array(data['positions']);points=np.c_[ps,np.ones(len(ps))];matrices=[];weights=[]
 for i,row in enumerate(data['weights']):
  mixed=np.zeros((4,4));total=0.;wrow={}
  for n,w in row.items():
   key=old_name(n);dest=rename(n)
   if dest not in binding['bones']:continue
   m=transforms.get(n,transforms.get(key))
   if m is None:
    if w>.03:raise RuntimeError('Unmapped garment bone '+profile+' '+n)
    continue
   mixed+=m*w;total+=w;wrow[dest]=wrow.get(dest,0)+w
  if total<=1e-7:raise RuntimeError('Unbound garment vertex '+profile)
  matrices.append(mixed/total);weights.append({n:w/total for n,w in wrow.items()})
 matrices=np.array(matrices);output=np.einsum('nij,nj->ni',matrices,points)[:,:3]
 triangles=np.array(data['triangles'],dtype=int);normalm=np.linalg.inv(matrices[:,:3,:3]).transpose(0,2,1);ns=np.einsum('fcij,fcj->fci',normalm[triangles],np.array(data['normals']));ns/=np.maximum(np.linalg.norm(ns,axis=2,keepdims=True),1e-8)
 result={k:data[k] for k in ('triangles','uv','triangle_materials','materials','material_slots')};result.update(profile=profile,item=item,binding_source=binding['source'],positions=output.tolist(),normals=ns.tolist(),weights=weights)
 path=Y/(profile+'_'+item+'.json');path.write_text(json.dumps(result,separators=(',',':')));manifest.append({'profile':profile,'item':item,'file':str(path)});return result

# First transport each new source garment back to the accepted M4 anatomical frame.
source_rig=json.loads((X/'source_bare.json').read_text())
canonical={}
for role,item in [('gloves','ue_hardknuckle_gloves'),('shirt','ue_st6_sleeves')]:
 source=json.loads((X/('source_'+role+'.json')).read_text());canonical[item]=fit(source,{n:np.linalg.inv(m) for n,m in warp.items()},lambda n:target_name(old_name(n),ref['bones']),ref,'M4',item)
for file in sorted(X.glob('rig_*.json')):
 profile=file.stem[4:]
 if profile in ('M4','Super90'):continue
 target=json.loads(file.read_text());transforms={}
 for n in ref['bones']:
  k=target_name(n,target['bones'])
  if k not in target['bones'] or not n.endswith(('_l','_r')):continue
  side=k[-1]
  if 'hand_'+side not in target['bones']:continue
  r,rl,rw=frame(ref['bones'],n);t,tl,tw=frame(target['bones'],k);radial=tw/max(rw,1e-8);transforms[n]=t@np.diag([tl/rl,radial,radial,1])@np.linalg.inv(r)
 for item,data in canonical.items():fit(data,transforms,lambda n:target_name(n,target['bones']),target,profile,item)
# Existing clothing remains usable on this new weapon, with its own native bind.
for file in X.glob('ue_*.json'):
 item=file.stem;data=json.loads(file.read_text());fit(data,warp,lambda n:target_name(n,source_rig['bones']),source_rig,'Super90',item)
(O/'equipment_manifest.json').write_text(json.dumps(manifest,indent=2));print('SUPER90_EQUIPMENT_AUTHORED',len(manifest))
