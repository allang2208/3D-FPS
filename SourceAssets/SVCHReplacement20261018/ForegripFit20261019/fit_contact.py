"""SVCH root-space seat and accepted native-SVD attachment hand registration."""
from arm_math import *
import ast
ref=matrices(arms['reference'])
source=O.parent/'LeftBolt20261019/author_left_bolt.py'
solver_source=source.read_text(encoding='utf-8').replace('(L1+L2)*.94','(L1+L2)*max(.94,np.linalg.norm(H-A)/(L1+L2))')
solver_source=solver_source.replace('if shoulder_adjust>6.:','if shoulder_adjust>25.:')
tree=ast.parse(solver_source)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in
 ('rr','mixrot','mix','frame','twist','arm')],type_ignores=[]),str(source),'exec'),globals())
donors=load('donors');root=ids['WPN_root'];hi=ids['hand_l'];ui=ids['upperarm_l'];li=ids['lowerarm_l']
digits=[i for i,n in enumerate(names) if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
changed=[i for i,n in enumerate(names) if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky'))]
seat=np.eye(4);seat[:3,:3]=R.from_euler('y',-5.,degrees=True).as_matrix()
# The original package's underside is 3.65 cm above its root; the SVD saddle
# top is 1.47 cm. Preserve the accepted grip body and its hand relationship.
seat[:3,3]=seat[:3,:3]@np.array([-.305,0.,2.18])
contacts={}
for family,row in donors.items():
 if 'local' not in row:continue
 local=np.asarray(row['local']);p=comp(matrices(local));hand=seat@np.linalg.inv(rigid(p[root]))@p[hi]
 contacts[family]={'hand':hand,'digits':{i:local[i] for i in digits}}

def fit(p,target,weight=1.):
 shoulder=p[ui,:3,3].copy();axis=unit(target[:3,3]-shoulder)
 pole=unit(p[li,:3,3]-shoulder-axis*((p[li,:3,3]-shoulder)@axis))
 try:q,info=arm(p,'l',target,shoulder,pole,blend=1.)
 except ValueError:q,info=None,{'wrist_swing_deg':180.}
 if info['wrist_swing_deg']>30.:
  # Preserve the accepted palm orientation. Move elbow/shoulder support to a
  # natural wrist cone instead of bending the wrist around the attachment.
  support=q if q is not None else p
  A,E,H=[support[j,:3,3] for j in (ui,li,hi)];l1=np.linalg.norm(E-A);l2=np.linalg.norm(H-E)
  ideal=rigid(target)[:3,:3]@rigid(ref[hi])[:3,:3].T@unit(ref[hi,:3,3]-ref[li,:3,3])
  rotate=R.from_matrix(swing(ideal,unit(target[:3,3]-E))).as_rotvec()
  direction=R.from_rotvec(rotate*min(1.,np.deg2rad(30.)/max(np.linalg.norm(rotate),1e-9))).apply(ideal)
  elbow=target[:3,3]-l2*direction
  shoulder=elbow+l1*unit(A-elbow)
  q,info=arm(p,'l',target,shoulder,elbow-shoulder,blend=1.)
 return q,info

if __name__=='__main__':
 p=pose('idle',0)
 for family,contact in contacts.items():
  target=rigid(p[root])@contact['hand'];q,info=fit(p,target)
  print(family,info,'wrist_cm',target[:3,3].tolist(),flush=True)
 (O/'mount.json').write_text(json.dumps({'matrix_root_cm':seat.tolist(),'rotation_y_degrees':-5.,'local_translation_cm':seat[:3,3].tolist(),'source_saddle_top_cm':1.47,'target_underside_height_cm':3.65},indent=2))
