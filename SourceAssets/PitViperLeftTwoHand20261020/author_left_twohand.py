"""Bake left-dominant two-hand clips from current V9 native single-pistol tracks.
Arms exchange anatomical roles; gun geometry, UVs, bind and mechanism stay native.
No mesh mirroring, component negative scale or runtime reflection.
Original single/dual sources remain unchanged; only this task's clips are saved.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
O=Path(__file__).parent
H=json.loads((O/'hierarchy.json').read_text());names=H['names'];parents=H['parents'];idx={n.lower():i for i,n in enumerate(names)}
pi=[idx[p.lower()] if p else -1 for p in parents]
M=np.diag([-1.,1.,1.,1.])
def matrices(v):
 v=np.asarray(v);out=np.broadcast_to(np.eye(4),v.shape[:-1]+(4,4)).copy()
 out[...,:3,:3]=Rotation.from_quat(v[...,3:7].reshape(-1,4)).as_matrix().reshape(v.shape[:-1]+(3,3))*np.where(np.abs(v[...,None,7:10])<1e-8,1.,v[...,None,7:10])
 out[...,:3,3]=v[...,:3];return out
def fk(local):
 out=local.copy()
 for i,p in enumerate(pi):
  if p>=0:out[...,i,:,:]=out[...,p,:,:]@local[...,i,:,:]
 return out
ref=fk(matrices(H['reference']));ri=idx['wpn_root'];ref_inv=np.linalg.inv(ref);gunbind=np.linalg.inv(ref[ri])@ref
# Keep the mirrored native single-pistol frame. The component supplies the
# live mirrored PistolHipViewmodelLocation; do not rebase to the older akimbo
# left idle, whose lateral position and outward angle are different.
weapon=[i for i,n in enumerate(names) if n.lower().startswith('wpn_')]
right=[i for i,n in enumerate(names) if n.endswith('_r') and not n.startswith(('thigh','calf','foot','ball'))]
support_chain=[idx['clavicle_r']]
for i,p in enumerate(pi):
 if p in support_chain:support_chain.append(i)
SUPPORT_INSET_CM=.8
def hand_in_gun(pose,hand):
 gun=pose[...,ri,:,:]
 axes=gun[...,:3,:3]/np.linalg.norm(gun[...,:3,:3],axis=-2)[...,None,:]
 return np.einsum('...ji,...j->...i',axes,pose[...,hand,:3,3]-gun[...,:3,3])
# Normal primary-pistol support positions, mirrored into the left-primary rig.
support_references=[]
for role in ('idle','aim'):
 source=fk(matrices(json.loads((O/'Source'/f'{role}.json').read_text())['frames']))[0]
 support_references.append(hand_in_gun(source,idx['hand_l'])*np.array([-1.,1.,1.]))
def ease(x):
 x=np.clip(x,0,1);return x*x*(3-2*x)
def inset_support(pose,role,src):
 # User feedback: right support is too far out in both hip and ADS. Seat
 # it 8 mm along the gun's lateral axis toward the fixed left firing hand.
 # Carry the whole arm group so the wrist, fingers and bone lengths stay native.
 local_hand=hand_in_gun(pose,idx['hand_r'])
 distance=np.min([np.linalg.norm(local_hand-ready,axis=-1) for ready in support_references],axis=0)
 weight=1.-ease((distance-1.)/2.)
 t=np.arange(len(pose))/src['fps']
 if role.startswith('reload'):
  # No inset while taking/inserting a magazine or operating the slide stop.
  weight*=np.maximum(1.-ease(t/.18),ease((t-(src['length']-.25))/.25))
 elif role.startswith('equip'):
  weight*=ease((t-(src['length']-.20))/.20)
 axis=pose[:,ri,:3,0]
 axis=axis/np.linalg.norm(axis,axis=-1)[:,None]
 delta=axis*(SUPPORT_INSET_CM*weight[:,None])
 for i in support_chain:pose[:,i,:3,3]+=delta
def output(role,src,empty_quick=False):
 frames=np.asarray(src['frames']);current=fk(matrices(frames));n=len(current)
 changed=current.copy()
 for i,name in enumerate(names):
  if i in weapon:continue
  other=name[:-2]+('_r' if name.endswith('_l') else '_l') if name.endswith(('_l','_r')) else name
  j=idx.get(other.lower(),i)
  changed[:,i]=M@current[:,j]@ref_inv[j]@M@ref[i]
 G=M@current[:,ri]@M;changed[:,ri]=G
 # Mirror motion relative to the native mechanical bind, not the part itself.
 inverse=np.linalg.inv(current[:,ri])
 for i in weapon:
  if i==ri:continue
  deformation=inverse@current[:,i]@np.linalg.inv(gunbind[i])
  changed[:,i]=G@M@deformation@M@gunbind[i]
 if empty_quick:
  empty_frames=np.asarray(json.loads((O/'Source/idle_empty.json').read_text())['frames'])
  empty=fk(matrices(empty_frames))[0]
  for name in ['wpn_slide','wpn_rearsight','wpn_socket_eject','wpn_barrel','wpn_frontsight','wpn_bullet']:
   i=idx[name];changed[:,i]=G@(np.linalg.inv(empty[ri])@empty[i])
 if role=='reload_empty':
  # The slide release remains on the physical gun's original side. Move the
  # supporting right arm as a group onto that control during the contact window.
  t=np.arange(n)/src['fps'];w=ease((t-1.34)/.13)*(1-ease((t-1.64)/.20))
  release=idx['wpn_sliderelease']
  delta=(changed[:,release,:3,3]-(M@current[:,release])[:,:3,3])*w[:,None]
  for i in right:changed[:,i,:3,3]+=delta
 inset_support(changed,role,src)
 local=changed.copy()
 for i,p in enumerate(pi):
  if p>=0:local[:,i]=np.linalg.inv(changed[:,p])@changed[:,i]
 scale=np.linalg.norm(local[:,:,:3,:3],axis=-2)
 rot=local[:,:,:3,:3]/scale[:,:,None,:]
 q=Rotation.from_matrix(rot.reshape(-1,3,3)).as_quat().reshape(n,len(names),4)
 for k in range(1,n):q[k]*=np.where(np.sum(q[k]*q[k-1],axis=-1)<0,-1,1)[:,None]
 # Zero-scaled rounds are authored visibility, not singular skeleton bindings.
 for i,name in enumerate(names):
  other=name[:-2]+('_r' if name.endswith('_l') else '_l') if name.endswith(('_l','_r')) and i not in weapon else name
  j=idx.get(other.lower(),i)
  scale[:,i]=np.where(np.abs(frames[:,j,7:10])<1e-8,0.,scale[:,i])
 if empty_quick:
  scale[:,idx['wpn_bullet']]=empty_frames[0,idx['wpn_bullet'],7:10]
 data=np.concatenate([local[:,:,:3,3],q,scale],axis=-1)
 target={'role':role,'source':src['source'],'rate':src['rate'],'fps':src['fps'],'length':src['length'],'frames':data.tolist()}
 (O/'Authored'/f'{role}.json').write_text(json.dumps(target,separators=(',',':')),encoding='utf-8')
 return {'source':src['source'],'duration':src['length'],'frames':n,'file':f'Authored/{role}.json'}
(O/'Authored').mkdir(exist_ok=True)
manifest={'mesh':H['mesh'],'skeleton':H['skeleton'],'destination':'/Game/Weapons/PitViper2011/LeftTwoHand20261020','roles':{},'baseline':'Native right-primary single-pistol motion, mirrored symmetrically; evaluated R2 ADS retained','method':'native anatomical arm exchange, positive-scale rigid gun motion; original mechanical bind retained','framing':'native source mirrored across mesh X; runtime hip anchor mirrors camera Y of PistolHipViewmodelLocation, fades out for ADS'}
manifest['support_fit']={'inward_cm':SUPPORT_INSET_CM,'axis':'positive gun-local X toward fixed left firing hand','bones':'right clavicle subtree only','contact_reference':'mirrored native single idle/aim support hand','release_distance_cm':[1.,3.],'reload_fade_out_seconds':.18,'reload_regrip_seconds':.25,'equip_regrip_seconds':.20,'runtime_test':'not_run'}
for file in sorted((O/'Source').glob('*.json')):
 src=json.loads(file.read_text());role=src['role'];manifest['roles'][role]=output(role,src)
quick=json.loads((O/'Source/quickcombat.json').read_text());manifest['roles']['quickcombat_empty']=output('quickcombat_empty',quick,True)
(O/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('Authored',len(manifest['roles']),'clips; existing single and dual assets unchanged')
