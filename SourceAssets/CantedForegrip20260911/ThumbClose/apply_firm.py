import bpy,json
from pathlib import Path
from mathutils import Matrix,Quaternion
O=Path(__file__).parent;f=json.loads((O/'fit_baseline.json').read_text());sol=json.loads((O/'fist_solution.json').read_text());D=__import__('numpy').load(O/'hand_lbs.npz');names=json.loads((O/'hand_lbs.json').read_text())['names'];parents=D['parents'];rest={n:Matrix(D['rest'][i].tolist()) for i,n in enumerate(names)};P={n:Matrix(m) for n,m in sol['pose'].items()};oldbasis=json.loads((O.parent/'FirmGrip/fit_final.json').read_text())['basis'];f['hand_in_root']=[list(row) for row in P['WPN_root'].inverted()@P['hand_l']]
for i,n in enumerate(names):
 if n.endswith('_l') and n.startswith(('index','middle','ring','pinky','thumb')):
  pn=names[parents[i]];lr=rest[pn].inverted()@rest[n];f['basis'][n]=[list(row) for row in lr.inverted()@P[pn].inverted()@P[n]]
(O/'fit_final.json').write_text(json.dumps(f,indent=2));release=json.loads((O.parent/'FirmGrip/release_profile.json').read_text())
for entry in release:
 t=min(1,entry['u']*1.5);fade=t*t*(3-2*t)
 for n,q in entry['basis'].items():
  if n in f['basis']:
   delta=Matrix(f['basis'][n]).to_quaternion()@Matrix(oldbasis[n]).to_quaternion().inverted();qq=delta.slerp(Quaternion(),fade)@Quaternion(q);entry['basis'][n]=list(qq)
(O/'release_profile.json').write_text(json.dumps(release,indent=2));print('FIRM_FIT_APPLIED')
