"""Continuous torso frame for layered armor: no per-vertex region switching."""
import numpy as np
def positions(garment,target_bones):
    source={b['name']:np.array(b['position']) for b in garment['bones']}
    target={b['name']:np.array(b['position']) for b in target_bones}
    names=['pelvis','spine_01','spine_02','spine_03','spine_04','spine_05','neck_01','head']
    names=sorted(names,key=lambda n:source[n][2]);sz=np.array([source[n][2] for n in names]);tz=np.array([target[n][2] for n in names])
    p=np.asarray(garment['positions']);q=p.copy();z=p[:,2]
    q[:,2]=np.interp(z,sz,tz)
    width=np.clip(abs(target['upperarm_l'][0])/abs(source['upperarm_l'][0]),.88,1.05)
    q[:,0]*=width
    sy=np.interp(z,sz,[source[n][1] for n in names]);ty=np.interp(z,sz,[target[n][1] for n in names])
    q[:,1]=ty+(p[:,1]-sy)*.96
    return q.tolist()
