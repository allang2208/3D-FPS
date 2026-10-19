"""Author six sparse grip profiles, retaining native bones and source action clocks."""
import json,gzip,sys,copy
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy.spatial.transform import Rotation as Rot,Slerp
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KDrum20261018';OLD=P/'SourceAssets/Saiga12KInspect20261018'
sys.path.insert(0,str(P/'Tools/Saiga12KInspect'));from pose_math import matrix,rotation,pack,world,apply
sys.path.insert(0,str(P/'SourceAssets/PKMLowpoly20260922/GripLayer56'));import evaluate as AL
AH=AL.AH;arm=AH.BONES
d=json.loads((OLD/'Inputs/runtime-source.json').read_text());src=json.load(gzip.open(O/'Inputs/reload-source.json.gz','rt'));fit=json.loads((O/'Inputs/palm-fit.json').read_text());names=[b['name'] for b in d['bones']];parents={b['name']:names[b['parent']] if b['parent']>=0 else None for b in d['bones']};rest={b['name']:matrix(b['world']) for b in d['bones']}
# Reuse only the production key reducer, without executing the inspect author.
code=(P/'Tools/Saiga12KInspect/author_profiles.py').read_text();exec(code[code.index('def sparse_track'):code.index('\ntimes=np.asarray')])
bind=SimpleNamespace(R=np.array([rotation(rest[n]) for n in arm]),st={},off={});pos=np.array([rest[n][:3,3] for n in arm]);bind.U0=pos[4]-pos[1];bind.F0=pos[7]-pos[4];bind.FL0=AH.frame(bind.F0,np.cross(bind.U0,bind.F0))
for i,origin,axis in ((2,pos[1],bind.U0),(3,pos[1],bind.U0),(5,pos[4],bind.F0),(6,pos[4],bind.F0)):
 bind.st[i]=(pos[i]-origin)@axis/(axis@axis);bind.off[i]=pos[i]-origin-bind.st[i]*axis
left=[n for n in names if n in arm or n.endswith('_l') and n.startswith(('thumb_','index_','middle_','ring_','pinky_'))];keynames=left+['ik_hand_l']
smooth=lambda x:(lambda v:v*v*(3-2*v))(float(np.clip(x,0,1)))
baseprof=json.loads((OLD/'Profiles/DA_base.json').read_text());template=json.loads((OLD/'Profiles/DA_angled.json').read_text());report={'complete':False,'source':'AKMDrumFreeDrop20260920 PalmGripV3','fit':fit,'families':{},'runtime_tested':False}
for family in ('base','drum','angled','vertical','canted','prism'):
 if family in ('base','drum'):
  prof=copy.deepcopy(baseprof)
  for c in template['clips']:
   if not any(x['base']==c['base'] for x in prof['clips']):prof['clips'].append(dict(base=c['base'],duration=c['duration'],tracks=[]))
 else:prof=json.loads((OLD/'Profiles'/('DA_'+family+'.json')).read_text())
 prof['family']=family
 for role,clip in src['clips'].items():
  old=next((c for c in prof['clips'] if c['base']==clip['asset']),None)
  end=220 if role.endswith('empty') else 236;tail=256 if role.endswith('empty') else 278
  keys={n:[] for n in keynames};times=np.array([f['time'] for f in clip['frames']])
  for k,frame in enumerate(clip['frames']):
   original={n:matrix(v) for n,v in frame['local'].items()};local=apply(original,old,frame['time']);pose=world(local,parents)
   weight=smooth((k-48)/64)*smooth((tail-k)/(tail-end));target=pose['hand_l'].copy();mr=rotation(pose['WPN_SOCKET_Magazine'])
   clearance=2.0*np.sin(np.pi*np.clip((k-end)/(tail-end),0,1))**2
   shift=np.array(fit['translation_mag_cm'])*weight+np.array([0,0,-clearance]);target[:3,3]+=mr@shift
   dq=Rot.from_rotvec(np.deg2rad(fit['rotation_mag_deg'])*weight).as_matrix();target[:3,:3]=mr@dq@mr.T@target[:3,:3]
   if weight>0 or clearance>0:
    rs=np.array([rotation(pose[n]) for n in arm]);ps=np.array([pose[n][:3,3] for n in arm]);reach=target[:3,3]-ps[1];limit=np.linalg.norm(ps[4]-ps[1])+np.linalg.norm(ps[7]-ps[4])-.3;ps+=AH.unit(reach)*max(0,np.linalg.norm(reach)-limit);pole=ps[4]-ps[1]
    zr,zp,_=AL.layer_arm(rs,ps,rs[7],ps[7],0.,pole,bind,0.);nr,np_,_=AL.layer_arm(rs,ps,rotation(target),target[:3,3],0.,pole,bind,0.);desired={}
    for i,n in enumerate(arm):
     correction=nr[i]@zr[i].T;m=pose[n].copy();m[:3,:3]=correction@rs[i]*np.linalg.norm(m[:3,:3],axis=0);m[:3,3]=np_[i]+correction@(ps[i]-zp[i]);desired[n]=m
    desired['hand_l']=target;final={}
    for n in names:
     p=parents[n]
     if n in desired:final[n]=desired[n];local[n]=np.linalg.inv(final[p])@final[n] if p else final[n]
     else:final[n]=final[p]@local[n] if p else local[n]
    final['ik_hand_l']=final['hand_l']@np.linalg.inv(pose['hand_l'])@pose['ik_hand_l'];local['ik_hand_l']=np.linalg.inv(final[parents['ik_hand_l']])@final['ik_hand_l']
   for n in keys:
    a,b=pack(original[n]),pack(local[n]);q=(Rot.from_quat(b[3:7])*Rot.from_quat(a[3:7]).inv()).as_quat();keys[n].append(np.r_[b[:3]-a[:3],q,np.zeros(3)])
  tracks=[t for n,v in keys.items() if (t:=sparse_track(n,v,times)) is not None];prof['clips']=[c for c in prof['clips'] if c['base']!=clip['asset']];prof['clips'].append(dict(base=clip['asset'],duration=clip['duration'],tracks=tracks))
 (O/'Profiles'/('DA_'+family+'.json')).write_text(json.dumps(prof),encoding='utf8');report['families'][family]={'clips':len(prof['clips']),'drum_layers':2,'keeps_prior_inspect':True};print('SAIGA_DRUM_POSE_AUTHORED',family,flush=True)
report['complete']=True;(O/'Receipts/pose-authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
