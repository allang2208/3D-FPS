"""Extend the user-accepted Pit Viper left-primary production method.
Native arm roles exchange offline; physical firearm geometry remains native.
Attachment variations become sparse profiles on the new base clips.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation, Slerp
O=Path(__file__).parent
M=np.diag([-1.,1.,1.,1.])
def ease(x):
 x=np.clip(x,0.,1.);return x*x*(3.-2.*x)
def matrices(v):
 v=np.asarray(v);o=np.broadcast_to(np.eye(4),v.shape[:-1]+(4,4)).copy()
 scale=np.where(np.abs(v[...,7:10])<1e-8,1.,v[...,7:10])
 o[...,:3,:3]=Rotation.from_quat(v[...,3:7].reshape(-1,4)).as_matrix().reshape(v.shape[:-1]+(3,3))*scale[...,None,:]
 o[...,:3,3]=v[...,:3];return o
def rotations(m):
 return m[...,:3,:3]/np.linalg.norm(m[...,:3,:3],axis=-2)[...,None,:]
class Author:
 def __init__(self,key,row):
  self.key=key;self.row=row;h=row['hierarchy'];self.names=h['names']
  self.ix={n.lower():i for i,n in enumerate(self.names)};self.parents=[self.ix[p.lower()] if p else -1 for p in h['parents']]
  self.gun=self.ix['wpn_root'];self.ref=self.fk(matrices(h['reference']))
  self.ref_inv=np.linalg.inv(self.ref);self.bind=np.linalg.inv(self.ref[self.gun])@self.ref
  self.weapon=[i for i,n in enumerate(self.names) if n.lower().startswith('wpn_')]
  self.right=[self.ix['clavicle_r']]
  for i,p in enumerate(self.parents):
   if p in self.right:self.right.append(i)
  self.swap=[self.ix.get((n[:-2]+('_r' if n.endswith('_l') else '_l')).lower(),i) if n.endswith(('_l','_r')) and i not in self.weapon else i for i,n in enumerate(self.names)]
  self.cache={}
 def fk(self,local):
  o=local.copy()
  for i,p in enumerate(self.parents):
   if p>=0:o[...,i,:,:]=o[...,p,:,:]@local[...,i,:,:]
  return o
 def raw(self,path):
  if path not in self.cache:self.cache[path]=json.loads((O/self.row['raw'][path]).read_text())
  return self.cache[path]
 def source(self,role,family='base'):
  path=self.row['roles'][role]
  profile=self.row['profiles'].get(family)
  layer=profile['clips'].get(path) if profile else None
  if not layer and family!='base':
   base=self.row['profiles'].get('base');layer=base['clips'].get(path) if base else None
  data=self.raw(layer['retained'] if layer and layer['retained'] else path)
  frames=np.asarray(data['frames'],dtype=float).copy()
  if layer and not layer['retained']:
   times=np.arange(len(frames))/data['fps']
   for track in layer['tracks']:
    i=self.ix.get(track['bone'].lower())
    if i is None:continue
    ts=np.asarray(track['times']);v=np.asarray(track['values']).reshape(-1,10)
    if len(ts)==1:delta=np.broadcast_to(v[0],(len(times),10))
    else:
     t=np.clip(times,ts[0],ts[-1]);delta=np.empty((len(t),10))
     for c in [0,1,2,7,8,9]:delta[:,c]=np.interp(t,ts,v[:,c])
     delta[:,3:7]=Slerp(ts,Rotation.from_quat(v[:,3:7]))(t).as_quat()
    frames[:,i,:3]+=delta[:,:3]
    frames[:,i,3:7]=(Rotation.from_quat(delta[:,3:7])*Rotation.from_quat(frames[:,i,3:7])).as_quat()
    frames[:,i,7:10]+=delta[:,7:10]
  return dict(source=data['source'],rate=data['rate'],fps=data['fps'],length=data['length']),frames
 def relative_hand(self,pose,hand):
  gun=pose[...,self.gun,:,:]
  return np.einsum('...ji,...j->...i',rotations(gun),pose[...,hand,:3,3]-gun[...,:3,3])
 def bake(self,role,family='base',empty=False):
  data,frames=self.source(role,family);current=self.fk(matrices(frames));changed=current.copy()
  for i,j in enumerate(self.swap):
   if i not in self.weapon:changed[:,i]=M@current[:,j]@self.ref_inv[j]@M@self.ref[i]
  G=M@current[:,self.gun]@M;changed[:,self.gun]=G
  inverse=np.linalg.inv(current[:,self.gun])
  for i in self.weapon:
   if i==self.gun:continue
   if self.row['capacity']:
    # The cylinder still opens on its physical side. Do not mirror its hinge,
    # chamber numbering, ejector or loader; move the right operating arm to it.
    changed[:,i]=G@inverse@current[:,i]
   else:
    deformation=inverse@current[:,i]@np.linalg.inv(self.bind[i])
    changed[:,i]=G@M@deformation@M@self.bind[i]
  t=np.arange(len(frames))/data['fps'];length=data['length']
  reload=role.startswith(('reload','single_','speed_'))
  if self.row['capacity'] and reload:
   cyl=self.ix['wpn_cylinder'];native=inverse@current[:,cyl]
   motion=native@np.linalg.inv(self.bind[cyl])
   ideal=G@M@motion@M@self.bind[cyl];actual=changed[:,cyl]
   delta=actual@np.linalg.inv(ideal)
   weight=ease(t/.35)*(1.-ease((t-(length-.50))/.45))
   q=Rotation.from_matrix(rotations(delta)).as_rotvec()*weight[:,None]
   correction=np.broadcast_to(np.eye(4),delta.shape).copy()
   correction[:,:3,:3]=Rotation.from_rotvec(q).as_matrix()
   # Blend about the mirrored cylinder, not the world origin.
   pivot=ideal[:,:3,3]
   target=pivot+(actual[:,:3,3]-pivot)*weight[:,None]
   correction[:,:3,3]=target-np.einsum('nij,nj->ni',correction[:,:3,:3],pivot)
   for i in self.right:changed[:,i]=correction@changed[:,i]
  elif role=='reload_empty':
   release=self.ix['wpn_sliderelease']
   w=ease((t-1.34)/.13)*(1-ease((t-1.64)/.20))
   shift=(changed[:,release,:3,3]-(M@current[:,release])[:,:3,3])*w[:,None]
   for i in self.right:changed[:,i,:3,3]+=shift
  # Accepted 8 mm seating applies to the normal support grip, not a forward
  # grip's separately authored contact with its accessory.
  if family in ('base','drum'):
   references=[]
   for refrole in ['idle','aim']:
    _,v=self.source(refrole,family);p=self.fk(matrices(v))[0]
    references.append(self.relative_hand(p,self.ix['hand_l'])*[-1,1,1])
   hand=self.relative_hand(changed,self.ix['hand_r'])
   distance=np.min([np.linalg.norm(hand-ref,axis=-1) for ref in references],axis=0)
   weight=1.-ease((distance-1.)/2.)
   if reload:weight*=np.maximum(1.-ease(t/.18),ease((t-(length-.25))/.25))
   elif role.startswith('equip'):weight*=ease((t-(length-.20))/.20)
   axis=rotations(G)[:,:,0];shift=axis*(.8*weight[:,None])
   for i in self.right:changed[:,i,:3,3]+=shift
  if empty:
   _,emptyframes=self.source('idle_empty',family);e=self.fk(matrices(emptyframes))[0]
   for name in ['wpn_slide','wpn_rearsight','wpn_socket_eject','wpn_barrel','wpn_frontsight','wpn_bullet']:
    i=self.ix[name];deformation=np.linalg.inv(e[self.gun])@e[i]@np.linalg.inv(self.bind[i])
    changed[:,i]=G@M@deformation@M@self.bind[i]
  local=changed.copy()
  for i,p in enumerate(self.parents):
   if p>=0:local[:,i]=np.linalg.inv(changed[:,p])@changed[:,i]
  scale=np.linalg.norm(local[:,:,:3,:3],axis=-2)
  q=Rotation.from_matrix((local[:,:,:3,:3]/scale[:,:,None,:]).reshape(-1,3,3)).as_quat().reshape(len(frames),len(self.names),4)
  for k in range(1,len(q)):q[k]*=np.where(np.sum(q[k]*q[k-1],axis=-1)<0,-1.,1.)[:,None]
  for i,j in enumerate(self.swap):scale[:,i]=np.where(np.abs(frames[:,j,7:10])<1e-8,0.,scale[:,i])
  if empty:scale[:,self.ix['wpn_bullet']]=emptyframes[0,self.ix['wpn_bullet'],7:10]
  return data,np.concatenate([local[:,:,:3,3],q,scale],axis=-1)
def delta_tracks(names,base,target,fps):
 tracks=[]
 for i,bone in enumerate(names):
  p=target[:,i,:3]-base[:,i,:3];s=target[:,i,7:10]-base[:,i,7:10]
  r=Rotation.from_quat(target[:,i,3:7])*Rotation.from_quat(base[:,i,3:7]).inv()
  if np.max(np.abs(p))<1e-5 and np.max(np.abs(s))<1e-6 and np.max(r.magnitude())<1e-5:continue
  q=r.as_quat()
  for k in range(1,len(q)):
   if np.dot(q[k],q[k-1])<0:q[k]*=-1
  v=np.concatenate([p,q,s],axis=-1)
  constant=np.max(np.abs(p-p[0]))<1e-5 and np.max(np.abs(s-s[0]))<1e-6 and np.max((r*r[0].inv()).magnitude())<1e-5
  if constant:v=v[:1]
  tracks.append(dict(bone=bone,times=(np.arange(len(v))/fps).tolist(),values=v.ravel().tolist()))
 return tracks
inputs=json.loads((O/'inputs.json').read_text())
manifest=dict(root='/Game/Weapons/PistolLeftTwoHand20261020',weapons={},profiles=[])
for key,row in inputs.items():
 if not row.get('raw'):continue
 author=Author(key,row);dest=f"{manifest['root']}/{key}";folder=O/'Authored'/key;folder.mkdir(parents=True,exist_ok=True)
 clips={};baseline={}
 roles=list(row['roles'])
 if not row['capacity']:roles.append('quickcombat_empty')
 for role in roles:
  srcrole='quickcombat' if role=='quickcombat_empty' else role
  data,frames=author.bake(srcrole,empty=role=='quickcombat_empty')
  file=folder/(role+'.json');file.write_text(json.dumps(dict(**data,frames=frames.tolist()),separators=(',',':')))
  asset=f'{dest}/A_LeftTwoHand_{key}_{role}'
  clips[role]=dict(asset=asset,file=str(file.relative_to(O)),source=data['source'],duration=data['length'],frames=len(frames))
  baseline[role]=(data,frames)
 for family in row['profiles']:
  if family=='base':continue
  profile=dict(family=family,clips=[])
  for role in roles:
   srcrole='quickcombat' if role=='quickcombat_empty' else role
   data,frames=author.bake(srcrole,family,role=='quickcombat_empty')
   original,base=baseline[role]
   if frames.shape!=base.shape or abs(data['length']-original['length'])>.001:
    raise RuntimeError(f'Profile clock differs: {key} {family} {role}')
   tracks=delta_tracks(author.names,base,frames,data['fps'])
   if tracks:profile['clips'].append(dict(base=clips[role]['asset'],duration=data['length'],tracks=tracks))
  file=folder/(family+'-profile.json');file.write_text(json.dumps(profile,separators=(',',':')))
  manifest['profiles'].append(dict(asset=f'{dest}/DA_LeftTwoHand_{key}_{family}',file=str(file.relative_to(O)),clips=len(profile['clips'])))
 manifest['weapons'][key]=dict(definition=row['definition'],mesh=row['mesh'],names=author.names,clips=clips)
 (O/'manifest.json').write_text(json.dumps(manifest,indent=2))
 print('LONE_ROLLOUT_AUTHORED',key,len(clips),flush=True)
print('LONE_ROLLOUT_AUTHOR_COMPLETE',flush=True)
