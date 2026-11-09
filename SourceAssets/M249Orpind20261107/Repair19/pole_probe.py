import pickle,numpy as np,sys
from pathlib import Path
from scipy.spatial.transform import Rotation as R
r=Path(__file__).parent;sys.path.insert(0,str(r.parent/'Repair10'));from motion import *
g=pickle.load(open(r/'geometry.pkl','rb'));d=pickle.load(open(r/'candidate_world.pkl','rb'))['reload_base'];ix={n:i for i,n in enumerate(g['names'])};B=np.array([matrix(v) for v in g['bind']]);w=d['world'][86]
ba,be,bh=[B[ix[n],:3,3] for n in ('upperarm_l','lowerarm_l','hand_l')];bn=unit(np.cross(be-ba,bh-be));bfore=frame(bh-be,bn)
a,e,h=[w[ix[n],:3,3] for n in ('upperarm_l','lowerarm_l','hand_l')];la=np.linalg.norm(e-a);lb=np.linalg.norm(h-e);axis=unit(h-a);dist=np.linalg.norm(h-a);along=(la*la-lb*lb+dist*dist)/(2*dist);c=a+axis*along;radius=np.sqrt(la*la-along*along);p=unit(e-c);out=[]
for degrees in range(-180,181,10):
    el=c+turn(axis,np.radians(degrees))@p*radius;normal=unit(np.cross(el-a,h-el));dl=frame(h-el,normal)@bfore.T;f=unit(h-el);q=R.from_matrix(rot(w[ix['hand_l']])@(dl@rot(B[ix['hand_l']])).T).as_quat();phi=np.degrees(2*np.arctan2(q[:3]@f,q[3]));phi=(phi+180)%360-180
    wrist=rot(w[ix['hand_l']])@rot(B[ix['hand_l']]).T@unit(bh-be);angle=np.degrees(np.arccos(np.clip(f@wrist,-1,1)))
    out.append((degrees,round(angle,1),round(phi,1)))
print(out)
