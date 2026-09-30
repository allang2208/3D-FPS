"""Anatomical shoulder opening and small cuff ease, never broad shoulder caps."""
import sys
from pathlib import Path
import numpy as np,bmesh
from mathutils import Vector
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
from author import read,write,recalc
from finish import rim
def ease_collar():
 d=read(R/'Authored/Body.json');p=np.array(d['positions']);q=p[:,:2]-np.array([0.,-1.5]);radius=np.linalg.norm(q,axis=1)
 amount=np.clip((p[:,2]-149)/4,0,1)*np.clip((14-radius)/3,0,1)
 p[:,:2]+=q/np.maximum(radius[:,None],1e-8)*amount[:,None]*.75
 d['positions']=p.tolist();recalc(d);d['contract']+='; 7.5 mm collar clearance blended into chest'
 write(R/'Authored/Body.json',d)
def trim():
 from author_traversal_loft import build
 build()
 d=read(R/'Authored/Body.json');p=np.array(d['positions'])
 for side in ['l','r']:
  a=np.array(d['bones']['upperarm_'+side]['position']);b=np.array(d['bones']['lowerarm_'+side]['position']);axis=(b-a)/np.linalg.norm(b-a);cut=np.linalg.norm(b-a)*.55;q=p-a;t=q@axis;radial=q-t[:,None]*axis
  amount=np.clip((t-(cut-5))/5,0,1);amount=amount*amount*(3-2*amount)
  selected=(p[:,0]*np.sign(a[0])>20)&(p[:,2]>115)&(t<cut+1)
  p[selected]+=radial[selected]/np.maximum(np.linalg.norm(radial[selected],axis=1)[:,None],1e-8)*amount[selected,None]*.45
 d['positions']=p.tolist();recalc(d);d['contract']+='; 4.5 mm cuff ease blended over distal 5 cm'
 write(R/'Authored/Body.json',d)
 ease_collar()
 print('CHARCOAL_EDGE_TRIM_DONE',flush=True)
if __name__=='__main__':trim()
