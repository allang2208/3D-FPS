"""201 video phases using installed PKM whole FK chains, without an arm IK solve.

The new pouch feeds from the opposite side. Mirror the complete native working
chain (including twist/fingers), retain the opening chain, and fit contacts by
whole-chain translation. Never rotate a wrist independently of its forearm.
"""
import json,gzip
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
O=Path(__file__).parent;data=json.loads((O/'inputs.json').read_text());geo=json.loads((O/'props.json').read_text())
def mat(v):
 m=np.eye(4);m[:3,:3]=R.from_quat(v[3:7]).as_matrix()@np.diag(v[7:10]);m[:3,3]=v[:3];return m
def pack(m):
 s=np.linalg.norm(m[:3,:3],axis=0);return np.r_[m[:3,3],R.from_matrix(m[:3,:3]/s).as_quat(),s]
def mix(a,b,w):
 if w<=0:return a.copy()
 if w>=1:return b.copy()
 va,vb=pack(a),pack(b);v=va*(1-w)+vb*w;v[3:7]=Slerp([0,1],R.from_quat([va[3:7],vb[3:7]]))([w]).as_quat()[0];return mat(v)
def ramp(t,a,b):
 f=np.clip((t-a)/(b-a),0,1);return f*f*f*(f*(f*6-15)+10)
def move(p):
 m=np.eye(4);m[:3,3]=p;return m
def load(key):return json.loads(Path(data['clips'][key]['file']).read_text())
def setup(fam):
 d=data['meshes'][fam];ns=d['names'];pa={n:ns[i] if i>=0 else None for n,i in zip(ns,d['parents'])};rests={n:mat(v) for n,v in zip(ns,d['rest'])};return ns,pa,rests
tn,tp,tr=setup('201');sn,sp,sr=setup('pkm')
def world(local,parent,names):
 out={}
 for n in names:out[n]=out[parent[n]]@local[n] if parent[n] else local[n]
 return out
si={n:mat(v) for n,v in zip(sn,load('pkm_idle')['poses'][0])};sw0=world(si,sp,sn)
ti={n:mat(v) for n,v in zip(tn,load('201_idle')['poses'][0])};tw0=world(ti,tp,tn)
tb={n:np.linalg.inv(tr['WPN_root'])@m for n,m in tr.items()}
sl0={n:np.linalg.inv(sw0['WPN_root'])@m for n,m in sw0.items()}
tl0={n:np.linalg.inv(tw0['WPN_root'])@m for n,m in tw0.items()}
src=load('pkm_reload_empty');source=[]
for row in src['poses']:source.append(world({n:mat(v) for n,v in zip(sn,row)},sp,sn))
def sample(t):
 p=np.clip(t*120,0,len(source)-1);i=int(p);j=min(i+1,len(source)-1);w=p-i
 return {n:mix(source[i][n],source[j][n],w) for n in sn} if w>1e-7 else source[i]
def subtree(side):
 chosen={'clavicle_'+side}
 for n in tn:
  if tp[n] in chosen:chosen.add(n)
 return [n for n in tn if n in chosen]
arms={s:subtree(s) for s in ('l','r')};mirror=np.diag([-1.,1.,1.,1.])
weapon_bones={'WPN_root'}
for n in tn:
 if tp[n] in weapon_bones:weapon_bones.add(n)
mirror_bind={n:np.linalg.inv(sr[n[:-2]+'_r'])@mirror@tr[n] for n in arms['l']}
# Register the gun to the donor's right grip, not the old, rejected 201 wrist
# trajectory. This is a fixed rigid offset, never the old 28 cm per-frame shift.
grip_offset=sl0['hand_r'][:3,3]-tl0['hand_r'][:3,3];gunfit=move(grip_offset)
def palm(worlds,side):
 h=worlds['hand_'+side][:3,3];middle=worlds['middle_01_'+side][:3,3]
 return h+(middle-h)*.56
def ref_palm(t,side,prop):
 w=sample(t);return (np.linalg.inv(w[prop])@np.r_[palm(w,side),1])[:3]
open_ref=ref_palm(.65,'l','PKM_Cover');close_ref=ref_palm(4.82,'r','PKM_Cover')
centers=np.array(geo['belt_centers_root_ue']);bagcontact=np.array(geo['pouch_contact_root_ue'])
duration=6.2;fps=120;count=round(duration*fps)+1
phase={'duration':duration,'cover_open':.65*1.1,'box_out':1.7*1.1,'old_hidden':2.3*1.1,'new_visible':2.65*1.1,'box_seat':3.45*1.1,'belt_seat':4.2*1.1,'cover_close':4.82*1.1,'return_start':5.45,'cycle_begin':3.45*1.1,'ready':4.82*1.1}
baseframes=[]
for fi in range(count):
 t=fi/fps;st=min(t/1.1,4.95);sw=sample(st);sroot=sw['WPN_root'];invroot=np.linalg.inv(sroot);sl={n:invroot@m for n,m in sw.items()}
 wr=sroot@gunfit;C=wr@invroot;desired={n:(wr@tl0[n] if n in weapon_bones else tw0[n].copy()) for n in tn}
 desired['WPN_root']=wr
 # Right hand retains the accepted PKM support shape throughout the video-like
 # left-hand operation. Every helper bone and finger moves with the same frame.
 support=sroot@np.linalg.inv(sw0['WPN_root'])
 for n in arms['r']:desired[n]=support@sw0[n]
 direct={n:C@sw[n] for n in arms['l']}
 mirrored={n:wr@mirror@sl[n[:-2]+'_r']@mirror_bind[n] for n in arms['l']}
 # Cover rotates about its installed hinge/bind frame. No detached latch or
 # static cap is created, and the model's complete closed interior stays intact.
 cr=tb['LMG201_Cover'].copy();cr[:3,:3]=(sl['PKM_Cover'][:3,:3]@np.linalg.inv(sl0['PKM_Cover'][:3,:3]))@cr[:3,:3]
 desired['LMG201_Cover']=wr@cr
 for prefix in ('','New_'):
  sb=prefix+'PKM_Box';n=prefix+'LMG201_Box';base=sl0['PKM_Box'];now=sl[sb]
  deltaR=mirror[:3,:3]@now[:3,:3]@np.linalg.inv(base[:3,:3])@mirror[:3,:3]
  center=np.array([.00375,.1313,-.063]);p=center+.8*(mirror[:3,:3]@(now[:3,3]-base[:3,3]))
  g=move(p);g[:3,:3]=deltaR;deform=g@move(-center)
  desired[n]=wr@deform@tb[n];desired[prefix+'LMG201_BoxLid']=wr@deform@tb[prefix+'LMG201_BoxLid']
  for bi in range(6):
   n=prefix+'LMG201_Belt_%02d'%bi;ss=prefix+'PKM_Belt_%02d'%bi;bs='PKM_Belt_%02d'%bi
   cur,ref=sl[ss],sl0[bs];dR=mirror[:3,:3]@cur[:3,:3]@np.linalg.inv(ref[:3,:3])@mirror[:3,:3]
   p=centers[bi]+.8*(mirror[:3,:3]@(cur[:3,3]-ref[:3,3]));g=move(p);g[:3,:3]=dR
   desired[n]=wr@g@move(-centers[bi])@tb[n]
 # Contact adaptation is a rigid translation of the complete FK chain. Use
 # actual new-model surface anchors, rather than resurrecting the old motions.
 coveropen=np.linalg.inv(tb['LMG201_Cover'])@np.r_[geo['cover_open_contact_root_ue'],1]
 coverclose=np.linalg.inv(tb['LMG201_Cover'])@np.r_[geo['cover_close_contact_root_ue'],1]
 openpoint=(desired['LMG201_Cover']@coveropen)[:3]
 openweight=ramp(st,.27,.50)*(1-ramp(st,.88,1.16))
 shift=(openpoint-palm(direct,'l'))*openweight
 for n in direct:direct[n]=move(shift)@direct[n]
 # Follow the pouch's rigid grasp frame while withdrawing and seating it.
 oldcontact=(desired['LMG201_Box']@np.linalg.inv(tb['LMG201_Box'])@np.r_[bagcontact,1])[:3]
 newcontact=(desired['New_LMG201_Box']@np.linalg.inv(tb['New_LMG201_Box'])@np.r_[bagcontact,1])[:3]
 swap=ramp(st,2.22,2.73);boxpoint=oldcontact*(1-swap)+newcontact*swap
 boxweight=ramp(st,1.38,1.65)*(1-ramp(st,3.45,3.72))
 # Lay the short visible belt using the same mirrored complete hand pose.
 beltpoint=(desired['New_LMG201_Belt_00']@np.linalg.inv(tb['New_LMG201_Belt_00'])@np.r_[centers[0]+[.008,0,.008],1])[:3]
 beltweight=ramp(st,3.65,3.90)*(1-ramp(st,4.20,4.34))
 closepoint=(desired['LMG201_Cover']@coverclose)[:3]
 closeweight=ramp(st,4.28,4.43)*(1-ramp(st,4.82,4.95))
 origin=palm(mirrored,'l');shift=(boxpoint-origin)*boxweight+(beltpoint-origin)*beltweight+(closepoint-origin)*closeweight
 for n in mirrored:mirrored[n]=move(shift)@mirrored[n]
 # Blend LOCAL FK during the released handoff. World-matrix interpolation
 # would shorten the upper arm and forearm at the blend midpoint.
 mirrored_weight=ramp(st,1.03,1.50)
 local={n:np.linalg.inv(desired[tp[n]])@desired[n] if tp[n] else desired[n] for n in tn}
 for n in arms['l']:
  par=tp[n];a=np.linalg.inv(direct[par] if par in direct else desired[par])@direct[n]
  b=np.linalg.inv(mirrored[par] if par in mirrored else desired[par])@mirrored[n]
  local[n]=mix(a,b,mirrored_weight)
 baseframes.append(local)
 print('CLOTH33_KEYS',fi,count,flush=True) if fi%240==0 else None

report={'revision':'ClothFeed33','donor':src['asset'],'donor_sha256':src['sha256'],'donor_metadata':src['metadata'],'reference_video':r'C:\Users\allan\Videos\NVIDIA\Delta Force\Delta Force 2026.09.28 - 22.36.59.03.mp4','method':'complete FK mirrored working chain; left opening chain; local entry/exit; rigid prop contacts; no IK, wrist-only rotation or bone scaling','phases':phase,'clips':{},'runtime_tested':False}
for family in ('base','vertical','canted','prism','angled'):
 idle=load('201_idle' if family=='base' else '201_'+family+'_idle');endpoint={n:mat(v) for n,v in zip(tn,idle['poses'][0])}
 tracks={n:[] for n in tn}
 for fi,row in enumerate(baseframes):
  t=fi/fps;entry=ramp(t,0,.32);leave=ramp(t,phase['return_start'],duration)
  for n in tn:
   m=row[n]
   if n in arms['l']+arms['r']+['WPN_root']:
    m=mix(endpoint[n],m,entry);m=mix(m,endpoint[n],leave)
   elif n=='LMG201_Cover':m=mix(m,endpoint[n],leave)
   # Hidden old props reset during the authored return, before their idle
   # section becomes visible. New props stay seated until the action ends.
   elif n.startswith('LMG201_'):m=mix(m,endpoint[n],leave)
   v=pack(m)
   if tracks[n] and np.dot(v[3:7],tracks[n][-1][3:7])<0:v[3:7]*=-1
   tracks[n].append(v.tolist())
 file=O/(family+'_tracks.json.gz')
 with gzip.open(file,'wt',encoding='utf8') as f:json.dump(tracks,f,separators=(',',':'))
 for empty in (False,True):
  key=family+('_reload_empty' if empty else '_reload');name='A_LMG201_'+key
  report['clips'][key]={'destination':'/Game/Weapons/LMG201/ClothFeed33/Animations/'+family+'/'+name,'source':idle['asset'],'source_sha256':idle['sha256'],'keys':str(file),'fps':fps,'frames':count,'seconds':duration,'empty':empty}
 print('CLOTH33_FAMILY_AUTHORED',family,flush=True)
(O/'motion.json').write_text(json.dumps(report,indent=2))
print('CLOTH33_MOTION_AUTHORED',len(report['clips']),flush=True)
