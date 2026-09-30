"""Change only current reload belt/link tracks. Preserve hand, pouch, gun and time."""
import sys,json,gzip,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as Rot
O=Path(__file__).parent;sys.path.insert(0,str(O.parent/'ClothReload44/Diagnostics'))
import diag_lib as D
S=json.loads((O/'source.json').read_text());L=json.loads((O/'layout.json').read_text())
def matrix(v):return D.mat(v['p']+v['q']+v['s'])
def unit(v):return v/max(np.linalg.norm(v),1e-12)
def rotation(m):return m[:3,:3]/np.maximum(np.linalg.norm(m[:3,:3],axis=0),1e-12)
def frame(c,y,z):
 z=unit(z);y=unit(y-z*(y@z));x=unit(np.cross(y,z));y=np.cross(z,x)
 m=np.eye(4);m[:3,:3]=np.array([x,y,z]).T;m[:3,3]=c;return m
def packed(m):
 s=np.linalg.norm(m[:3,:3],axis=0);return [*m[:3,3],*Rot.from_matrix(m[:3,:3]/np.maximum(s,1e-10)).as_quat(),*s]
centers=np.array(L['centers_root_m']);guide=np.array(L['guide_root_m']);slots=L['slot_by_cell']
baseframes=[frame(c,[0,1,0],guide[min(slot+4,len(guide)-1)]-guide[max(slot+2,0)]) for c,slot in zip(centers,slots)]
idle={n:D.mat(v) for n,v in S['idle'].items()};gun0=idle['WPN_root']
(O/'Tracks').mkdir(exist_ok=True)
report={'revision':'BeltFit53','modified_bones':[],'families':{},'source_clips':S['clips']}
main_order=[0,1,2,3,4,5,6,9,11,12,13]
main_dist=np.r_[0,np.cumsum(np.linalg.norm(np.diff(centers[main_order],axis=0),axis=1))]
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
def fixed_pitch(points,pitches):
 # Arc-length samples bunch together on the folded section. Advance to the
 # next sphere/polyline intersection so neighbouring rigid cases retain pitch.
 p=np.asarray(points);out=[p[0]];segment=0
 for pitch in pitches:
  origin=out[-1]
  while segment<len(p)-1:
   a=p[segment]-origin;v=p[segment+1]-p[segment];vv=v@v
   if vv<1e-16:segment+=1;continue
   disc=(a@v)**2-vv*(a@a-pitch*pitch)
   u=(-a@v+np.sqrt(max(0.,disc)))/max(vv,1e-15)
   if disc>=0 and 0<=u<=1:
    out.append(p[segment]+u*v);break
   segment+=1
  else:out.append(origin+np.array([0,0,-pitch]))
 return np.asarray(out)

def pouch_route(end):
 # The pouch is a reservoir: the mouth need not always coincide with cell 5.
 # A continuous tangent arc replaces the fixed-cell slack loop at release.
 p=end.copy();p[0]+=max(0.,.085-p[0])*smooth((.012-p[2])/.030)
 inside=.040;bottom=np.array([inside,centers[0,1],-.18]);zc=.003;dx=p[0]-inside
 if dx>.001:
  if p[2]<zc:
   radius=dx/2;theta=0.;head=[p,[p[0],p[1],zc]]
  else:
   radius=(dx*dx+(p[2]-zc)**2)/(2*dx);theta=np.arctan2(p[2]-zc,dx-radius);head=[p]
  arc=np.array([[inside+radius+radius*np.cos(a),p[1]+(centers[0,1]-p[1])*(a-theta)/max(np.pi-theta,1e-9),zc+radius*np.sin(a)] for a in np.linspace(theta,np.pi,80)])
  route=np.concatenate([head,arc,[bottom]])
 else:route=np.array([p,[inside,centers[0,1],-.015],bottom])
 pts=fixed_pitch(route,np.diff(main_dist))
 near=1-smooth(np.linalg.norm(p-centers[0])/.008)
 canonical=centers[main_order]+(p-centers[0])[None,:]*np.maximum(0,1-main_dist/main_dist[-1])[:,None]
 return pts*(1-near)+canonical*near

for family in (sys.argv[1:] or ['base','vertical','canted','prism','angled']):
 path=O.parent/'ClothReload44/Tracks'/(family+'_tracks.json.gz');tracks=D.load_tracks(path);W=D.worlds(tracks);out={n:v.copy() for n,v in tracks.items()};changed=set();diag=[]
 for fi in range(len(W)):
  G=W[fi,D.BI['WPN_root']];ig=np.linalg.inv(G);writes={}
  for side,prefix in enumerate(['','New_']):
   ids=[D.BI[prefix+'LMG201_Belt_%02d'%i] for i in range(14)]
   original=np.array([(ig@W[fi,ids[i]]@np.r_[L['centers_bone_local'][side][i],1])[:3] for i in range(6)])
   boxmove=ig@W[fi,D.BI[prefix+'LMG201_Box']]@np.linalg.inv(idle[prefix+'LMG201_Box'])@gun0
   ibox=np.linalg.inv(boxmove);end=(ibox@np.r_[original[0],1])[:3]
   regular=pouch_route(end)
   if max(np.linalg.norm(end-centers[0]),np.linalg.norm(original[5]-centers[5]))<1e-5:regular=centers[main_order].copy()
   allpoints=regular@boxmove[:3,:3].T+boxmove[:3,3];pts=allpoints[:6]
   local={}
   axis=rotation(boxmove)@np.array([0.,1.,0.])
   for j,i in enumerate(main_order):
    desired=frame(allpoints[j],axis,allpoints[min(j+1,len(main_order)-1)]-allpoints[max(j-1,0)])
    local[i]=desired@np.linalg.inv(baseframes[i])@matrix(L['idle_bone_local'][side][i])
    buried=(1-smooth((regular[j,0]-.055)/.015))*smooth((-.034-regular[j,2])/.016)
    visibility=max(1e-4,1-buried)
    center=allpoints[j];local[i][:3,3]=center+(local[i][:3,3]-center)*visibility;local[i][:3,:3]*=visibility
   t=fi/120;seat=smooth((t-4.38)/.40) if side else 1-smooth((t-1.60)/.14)
   if not side and t>5.95:seat=smooth((t-5.95)/.15)
   leading=[];tan=unit(allpoints[1]-allpoints[0])
   for j,i in enumerate([7,8]):
    free=allpoints[0]-tan*.0135*(j+1);seated=allpoints[0]+centers[i]-centers[0]
    pos=free*(1-seat)+seated*seat;leading.append(pos)
   for j,i in enumerate([7,8]):
    prev=allpoints[0] if j==0 else leading[0]
    desired=frame(leading[j],axis,prev-leading[j]);local[i]=desired@np.linalg.inv(baseframes[i])@matrix(L['idle_bone_local'][side][i])
   local[10]=boxmove@matrix(L['idle_bone_local'][side][10])
   # Hidden circulation cell does not remain as a loose cartridge during reload.
   local[10][:3,:3]*=1e-4
   for i in range(14):writes[ids[i]]=G@local[i]
   cp=np.array([(local[i]@np.r_[L['centers_bone_local'][side][i],1])[:3] for i in range(14)])
   for k,(a,b) in enumerate(L['pairs']):
    ca,cb=cp[a],cp[b];axis=rotation(local[a])@np.array(L['axis_bone_local'][side][a])+rotation(local[b])@np.array(L['axis_bone_local'][side][b])
    target=frame((ca+cb)/2,axis,cb-ca)
    ratio=np.linalg.norm(cb-ca)/L['link_lengths_root'][k]
    ratio*=min(np.linalg.norm(local[a][:3,0]),np.linalg.norm(local[b][:3,0]))
    if k>=12:ratio=1e-4
    target[:3,:3]*=ratio
    ref=frame((centers[a]+centers[b])/2,[0,1,0],centers[b]-centers[a])
    writes[D.BI[prefix+'LMG201_Belt_Link_%02d'%k]]=G@target@np.linalg.inv(ref)@matrix(L['link_idle_bone_local'][side][k])
   diag.append({'frame':fi,'side':side,'gaps_mm':(np.linalg.norm(np.diff(pts,axis=0),axis=1)*1000).tolist(),'tail_gap_mm':float(np.linalg.norm(cp[6]-cp[5])*1000),'anchor_error_mm':float(np.linalg.norm(pts[5]-original[5])*1000),'hand_error_mm':float(np.linalg.norm(pts[0]-original[0])*1000)})
  for i,m in writes.items():
   parent=D.PARENT[i];pm=writes.get(parent,W[fi,parent]) if parent>=0 else np.eye(4)
   name=D.NAMES[i];out[name][fi]=packed(np.linalg.inv(pm)@m);changed.add(name)
 with gzip.open(O/'Tracks'/(family+'_tracks.json.gz'),'wt') as f:json.dump({n:v.tolist() for n,v in out.items() if n in changed},f)
 unchanged=all(np.array_equal(out[n],tracks[n]) for n in tracks if n not in changed)
 report['families'][family]={'source_tracks_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'other_tracks_unchanged':unchanged,'changed_track_count':len(changed),'max_gap_mm':max(max(r['gaps_mm']) for r in diag),'max_legacy_cell5_displacement_mm':max(r['anchor_error_mm'] for r in diag),'max_held_end_adjustment_mm':max(r['hand_error_mm'] for r in diag)}
 report['modified_bones']=sorted(changed)
 with gzip.open(O/(family+'_points.json.gz'),'wt') as f:json.dump(diag,f)
 print('B53_MOTION',family,report['families'][family],flush=True)
(O/'motion.json').write_text(json.dumps(report,indent=2))
