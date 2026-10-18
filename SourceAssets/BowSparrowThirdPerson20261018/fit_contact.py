"""Fit the string landmark to the actual skinned Jason finger surfaces."""
import json
import numpy as np
from scipy.optimize import least_squares
from bow_math import *
d=read('retargeted.json.gz');a=read('authored.json.gz');skin=read('skin.json.gz')
w=fk(np.array(a['clips']['Hold']['frames'][0]),d['parents']);ix={n:i for i,n in enumerate(d['names'])}
hand=w[ix['hand_r'],:7];curves=a['clips']['Hold']['float_curves']
nock=np.array([curves['SparrowBowNock'+c][0] for c in 'XYZ'])
grip=np.array([curves['SparrowBowGrip'+c][0] for c in ['X','Y','Z','QX','QY','QZ','QW']])
bow=compose(w[ix['hand_l'],:7],grip);inhand=compose(inverse(hand),bow)
def point(pos,weights):
 result=np.zeros(3)
 for name,weight in weights.items():
  r=np.array(skin['rest'][name]);p=rot(inv(r[3:7]),np.array(pos)-r[:3])/r[7:];t=w[ix[name]]
  result+=weight*(t[:3]+rot(t[3:7],p*t[7:]))
 return rot(inv(hand[3:7]),result-hand[:3])
heads=json.loads((O.parents[1]/'SourceAssets/BowFlex20260927/body-authoring.json').read_text())['bone_heads_blender_cm']
chains=[]
for side in ('upper','lower'):
 chains.append(np.array([heads[side+'_'+(f'{i:02d}' if i<5 else 'tip')] for i in range(1,6)])*np.array([1.,-1.,1.]))
brace=np.array([-24.081,.123,1.5]);full=np.array([-52.581,.123,1.5])
def tips(angle):
 result=[]
 for side,chain in enumerate(chains):
  p=chain[0].copy()
  for i in range(1,5):p+=R.from_rotvec(np.array([0.,angle*(-1 if side==0 else 1)*(i/4)**1.15,0.])).apply(chain[i]-chain[i-1])
  result.append(p)
 return result
rest=sum(np.linalg.norm(chain[-1]-brace) for chain in chains);low=0.;high=np.deg2rad(38.)
for _ in range(14):
 mid=(low+high)*.5
 if sum(np.linalg.norm(t-full) for t in tips(mid))>rest:low=mid
 else:high=mid
endpoints=[inhand[:3]+rot(inhand[3:7],p) for p in tips((low+high)*.5)]
patches=[]
for digit in ('index','middle','ring'):
 ids=[i for i,weights in enumerate(skin['weights']) if sum(weights.get(f'{digit}_{j:02d}_r',0) for j in (2,3))>.65]
 patches.append(np.array([point(skin['positions'][i],skin['weights'][i]) for i in ids]))
def distances(delta):
 result=[]
 for points in patches:
  best=[]
  for end in endpoints:
   axis=unit(end-nock);along=np.clip((points-nock-delta)@axis,0,np.linalg.norm(end-nock))
   best.append(np.linalg.norm(points-(nock+delta+along[:,None]*axis),axis=1).min())
  result.append(min(best))
 return np.array(result)
before=distances(np.zeros(3))
fit=least_squares(lambda delta:np.r_[distances(delta)-.14,.025*delta],np.zeros(3),bounds=(-2.,2.),max_nfev=160)
previous=json.loads((O/'contact-correction.json').read_text()) if (O/'contact-correction.json').exists() else {}
old=np.array(previous.get('delta_in_right_hand_cm',[0.,0.,0.]))
result={'delta_in_right_hand_cm':(old+fit.x).tolist(),'finger_surface_gap_before_cm':before.tolist(),
 'finger_surface_gap_after_cm':distances(fit.x).tolist(),'fingers':['index','middle','ring'],
 'target_gap_cm':.14,'bow_flex_tip_positions_cm':[p.tolist() for p in tips((low+high)*.5)],
 'initial_unfitted_gap_cm':previous.get('initial_unfitted_gap_cm',previous.get('finger_surface_gap_before_cm',before.tolist())),
 'method':'Use the actual bent bow tips. Translate the contact landmark and compensate the wrist; keep native finger rotations and the thumb unchanged.',
 'game_run':False}
(O/'contact-correction.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
