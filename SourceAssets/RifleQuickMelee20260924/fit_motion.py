"""Offline whole-group and elbow-circle fitting for SVD/PKM quick melee.

Own idle palm/finger matrices remain rigidly attached to the gun. Fits include
wrist flexion, complete arm reach, forearm/receiver clearance and stock framing.
No physics timing, damage, mesh, finger pose or runtime camera is modified.
"""
import json,math,sys
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scipy.ndimage import gaussian_filter1d
O=Path(__file__).parent
sources=json.loads((O/'sources.json').read_text())
FPS=240
TIMES=np.array([0,.035,.075,.115,1/6,.205,.285,.43,.59,.72,.82,.9])
def smooth(t):
 t=np.clip(t,0,1);return t*t*t*(10+t*(-15+6*t))
def unit(v):return v/max(np.linalg.norm(v),1e-8)
def segment_distance(p,a,b):
 t=np.clip(np.dot(p-a,b-a)/max(np.dot(b-a,b-a),1e-9),0,1)
 return np.linalg.norm(p-a-t*(b-a))
results=json.loads((O/'motion.json').read_text()) if (O/'motion.json').exists() else {}
reports=json.loads((O/'design.json').read_text()) if (O/'design.json').exists() else {}
for key,data in sources.items():
 if len(sys.argv)>1 and key not in sys.argv[1:]:continue
 weapon,family=key.split('/')
 idle={n:np.array(m) for n,m in data['idle'].items()};rest={n:np.array(m) for n,m in data['rest'].items()}
 W0=idle['WPN_root'];stock=np.array(data['stock']);P0=(W0@np.r_[stock,1])[:3]
 grip={s:np.linalg.inv(W0)@idle['hand_'+s] for s in 'rl'}
 shoulder0={s:idle['upperarm_'+s][:3,3] for s in 'rl'}
 elbow0={s:idle['lowerarm_'+s][:3,3] for s in 'rl'}
 lengths={s:[np.linalg.norm(idle[b+'_'+s][:3,3]-idle[a+'_'+s][:3,3]) for a,b in [('upperarm','lowerarm'),('lowerarm','hand')]] for s in 'rl'}
 natural={s:rest['hand_'+s][:3,:3].T@unit(rest['hand_'+s][:3,3]-rest['lowerarm_'+s][:3,3]) for s in 'rl'}
 offset={'r':np.array([.29,.26,-.225]),'l':np.array([-.07,-.25,-.040])} if weapon=='SVD' else {'r':np.array([.29,.31,-.215]),'l':np.array([-.07,-.24,-.025])}
 # Stock stages are authored in first-person space: readable preparation,
 # forward contact, brief follow-through, then one continuous recovery.
 if weapon=='PKM':
  angles=np.array([[0,0,0],[-3,-3,24],[-8,-9,70],[-9,-12,112],[-10,-14,138],[-10,-14,140],[-9,-12,127],[-6,-9,94],[-3,-5,44],[-1,-2,12],[0,0,1],[0,0,0]],float)
  points=np.array([P0,[.15,-.23,-.125],[.22,-.06,-.015],[.19,.12,.035],[.055,.34,.065],[.035,.345,.062],[.075,.28,.04],[.18,.13,-.005],[.17,-.09,-.055],[.10,-.27,-.11],P0,P0])
 else:
  angles=np.array([[0,0,0],[-3,-4,22],[-9,-12,68],[-12,-20,105],[-14,-23,129],[-15,-23,132],[-12,-20,118],[-8,-15,82],[-4,-7,36],[-1,-2,10],[0,0,1],[0,0,0]],float)
  points=np.array([P0,[.13,-.135,-.14],[.21,.015,-.01],[.18,.155,.045],[.065,.34,.075],[.045,.35,.075],[.075,.28,.04],[.17,.14,-.02],[.16,-.01,-.09],[.09,-.14,-.16],P0,P0])
 curve_angles=PchipInterpolator(TIMES,angles,axis=0);curve_points=PchipInterpolator(TIMES,points,axis=0)
 previous=np.zeros(11);fits=[];bases=[]
 def pose_info(Q,P,theta,s,weight,shoulder_correction=None):
  H=grip[s];wr=Q@(H[:3,3]-stock)+P
  support=weight if s=='r' else smooth((t-.035)/.09)*(1-smooth((t-.40)/.42))
  sh=shoulder0[s]+offset[s]*support
  if s=='r' and shoulder_correction is not None:sh=sh+shoulder_correction
  a,b=lengths[s];v=wr-sh;d=np.linalg.norm(v);axis=unit(v);along=(a*a-b*b+d*d)/(2*max(d,1e-8));radius=math.sqrt(max(0,a*a-along*along))
  pole=elbow0[s]-sh;pole-=axis*np.dot(pole,axis);pole=unit(pole)
  desired=unit(Q@H[:3,:3]@natural[s]);ideal=unit(-desired+axis*np.dot(desired,axis))
  ideal_angle=math.atan2(np.dot(axis,np.cross(pole,ideal)),np.dot(pole,ideal))
  pole=Rotation.from_rotvec(axis*(ideal_angle*weight+theta)).apply(pole)
  el=sh+axis*along+pole*radius
  fore=unit(wr-el)
  return sh,el,wr,math.acos(np.clip(np.dot(desired,fore),-1,1)),d/(a+b)
 for frame in range(217):
  t=frame/FPS;weight=smooth(t/.09)*(1-smooth((t-.40)/.42))
  group_weight=smooth(t/.035)*(1-smooth((t-.32)/.34))
  Q=Rotation.from_euler('xyz',curve_angles(t),degrees=True).as_matrix()@W0[:3,:3];P=curve_points(t)
  contact=smooth((t-.07)/.09)*(1-smooth((t-.32)/.18))
  def residual(x):
   q=Rotation.from_rotvec(x[:3]).as_matrix()@Q;p=P+x[3:6];root=p-q@stock
   res=[];arms={}
   for j,s in enumerate('rl'):
    sh,el,wr,bend,reach=pose_info(q,p,x[6+j],s,weight,x[8:]);arms[s]=(sh,el,wr)
    # Keep the full arm triangle attainable. Favor comfortable flexion, but
    # do not roll an elbow through the receiver merely to minimize bend.
    res.extend([26*max(0,bend-math.radians(34)),.3*weight*bend,400*max(0,reach-.975),80*weight*max(0,.44-reach)])
    cross=max(0,(sh[0]-el[0])*(1 if s=='r' else -1)-.035)
    res.extend([22*weight*cross,12*weight*max(0,el[2]+.06)])
    # Receiver/barrel/stock are separate coarse capsules; the final hand-side
    # quarter is exempt, since contact at the grip is intentional.
    for along in [.12,.35,.58,.78]:
     probe=el+(wr-el)*along
     local=q.T@(probe-root)
     radius=.043 if weapon=='PKM' else .034
     clearance=min(segment_distance(local,np.array([0,-.23,.025]),np.array([0,.12,.025]))-radius,
                   segment_distance(local,np.array([0,.12,-.01]),stock)-.033)
     res.append(55*weight*max(0,.032-clearance))
     if s=='r':
      # The SVD thumbhole's lower rail and PKM buttstock have volume below
      # their centerlines. Keep the forearm outside the whole stock envelope.
      box_min=np.array([-.030,.10,-.115]);box_max=np.array([.030,stock[1]+.012,.020])
      outside=np.maximum(np.maximum(box_min-local,local-box_max),0)
      res.append(95*weight*max(0,.038-np.linalg.norm(outside)))
    if s=='r':
     # Shoulder opening stays beyond the right edge of the view frustum.
     res.append(60*weight*max(0,1.45*max(0,sh[1]+.10)+.065-sh[0]))
   # Separate forearm interiors across the stroke, excluding contact fingers.
   for a in [.0,.4,.7]:
    for b in [.0,.4,.7]:
     pr=arms['r'][1]*(1-a)+arms['r'][2]*a;pl=arms['l'][1]*(1-b)+arms['l'][2]*b
     res.append(30*weight*max(0,.075-np.linalg.norm(pr-pl)))
   res.extend(.8*x[:3]);res.extend(10*x[3:6]);res.extend(.10*x[6:8]);res.extend(6*x[8:])
   res.extend(.55*(x[:3]-previous[:3]));res.extend(6*(x[3:6]-previous[3:6]));res.extend(.18*(x[6:8]-previous[6:8]));res.extend(4*(x[8:]-previous[8:]))
   # Contact must stay in front of the eye with the buttplate clearly leading.
   res.extend([55*contact*max(0,.30-p[1]),40*contact*max(0,.035-p[2]),
               20*contact*max(0,abs(p[0])-.15),8*contact*max(0,.53-q[1,1]),
               12*weight*max(0,.78-q[2,2]),65*smooth((t-.30)/.10)*max(0,root[2]+.075)])
   return res
  if frame in (0,216):x=np.zeros(11)
  else:
   cap=np.array([.55,.55,.40,.075,.07,.075,1.2,1.2,.13,.14,.10])*max(weight,1e-5)
   cap[:6]=np.array([.55,.55,.40,.075,.07,.075])*max(group_weight,1e-5)
   x=least_squares(residual,np.clip(previous,-cap*.999,cap*.999),bounds=(-cap,cap),max_nfev=55,ftol=5e-5,xtol=5e-5,gtol=5e-5).x
  previous=x;fits.append(x);bases.append((Q,P,weight))
 # Smooth only tiny frame-to-frame optimizer changes; contact still reaches
 # its authored maximum on the original 1/6 second clock.
 fits=gaussian_filter1d(np.array(fits),1.0,axis=0,mode='nearest')
 rows=[];metrics=[]
 for frame,(Q,P,weight) in enumerate(bases):
  t=frame/FPS;x=fits[frame]*smooth(t/.035)*(1-smooth((t-.84)/.06))
  q=Rotation.from_rotvec(x[:3]).as_matrix()@Q;p=P+x[3:6];W=np.eye(4);W[:3,:3]=q;W[:3,3]=p-q@stock
  if frame in (0,216):W=W0.copy()
  # Smooth fitting is followed by a rigid reach projection. Neither arm is
  # allowed to lengthen at a difficult entry/recovery frame.
  for _ in range(16):
   for j,s in enumerate('rl'):
    sh,el,wr,bend,reach=pose_info(W[:3,:3],(W@np.r_[stock,1])[:3],x[6+j],s,weight,x[8:])
    maximum=sum(lengths[s])*.999
    if np.linalg.norm(wr-sh)>maximum:W[:3,3]+=(sh+unit(wr-sh)*maximum-wr)
  arms={};stats={}
  for j,s in enumerate('rl'):
   sh,el,wr,bend,reach=pose_info(W[:3,:3],(W@np.r_[stock,1])[:3],x[6+j],s,weight,x[8:])
   arms[s]={'shoulder':sh.tolist(),'elbow':el.tolist()};stats[s]={'bend':math.degrees(bend),'reach':reach}
  rows.append({'time':t,'root':W.tolist(),'arms':arms,'support_weight':weight})
  metrics.append({'time':t,'arms':stats,'stock':(W@np.r_[stock,1])[:3].tolist()})
 results[key]=rows
 reports[key]={'max_wrist':{s:max(r['arms'][s]['bend'] for r in metrics) for s in 'rl'},'max_reach':{s:max(r['arms'][s]['reach'] for r in metrics) for s in 'rl'},'contact':metrics[40],'shoulder_offsets':{s:v.tolist() for s,v in offset.items()},'times':TIMES.tolist(),'stock_points':points.tolist(),'angles':angles.tolist()}
 print('FITTED',key,json.dumps({k:v for k,v in reports[key].items() if k not in ['times','stock_points','angles']}),flush=True)
 (O/'motion.json').write_text(json.dumps(results));(O/'design.json').write_text(json.dumps(reports,indent=2))
