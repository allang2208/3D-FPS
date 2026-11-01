from pathlib import Path
exec(compile((Path(__file__).parent/'diagnose.py').read_text().split("\nif __name__=='__main__':")[0],'diagnose','exec'))
def rotate_root(row,degrees):
 out={n:m.copy() for n,m in row.items()};S,E,H=[row[n].translation for n in ('upperarm_l','lowerarm_l','hand_l')]
 normal=(E-S).cross(H-E).normalized();other=(S-E).normalized().cross(normal)
 # Minimal humeral swing toward the lower camera edge, without axial twist.
 axis=normal*math.cos(math.radians(-30))+other*math.sin(math.radians(-30));turn=Quaternion(axis,math.radians(degrees))
 moved=Matrix.LocRotScale(E+turn@(S-E),turn@row['upperarm_l'].to_quaternion(),row['upperarm_l'].to_scale())
 for n in names:
  if under(n,'upperarm_l') and not under(n,'lowerarm_l'):out[n]=moved@row['upperarm_l'].inverted()@row[n]
 out['clavicle_l']=moved@row['upperarm_l'].inverted()@row['clavicle_l'];return out
if __name__=='__main__':
 result={}
 for role in ('idle','sprint_loop'):
  e=entry('skeleton_base',role);row,_=compose(e,e['duration']*.5);result[role]={}
  for deg in (-12,-8,0,8,12,16,20):
   fixed=rotate_root(row,deg);X=skin(fixed);cp=np.c_[X,np.ones(len(X))]@C.T
   root=left&(np.linalg.norm(P-np.array(rest['upperarm_l'].translation),axis=1)<.17)
   near=(cp[:,0]>0)&root
   # Shoulder patch must lie below the lower frame with several cm of margin.
   margin=-cp[near,2]-cp[near,0]*math.tan(math.radians(37.5))
   result[role][deg]={'min_lower_clearance_cm':float(margin.min()),'visible_upper_points':int((margin<0).sum()),'S':list(C@np.r_[fixed['upperarm_l'].translation,1]),'shift_cm':(fixed['upperarm_l'].translation-row['upperarm_l'].translation).length*100}
 (O/'candidates.json').write_text(json.dumps(result,indent=2));print('ROOT_CANDIDATES',json.dumps(result),flush=True)
