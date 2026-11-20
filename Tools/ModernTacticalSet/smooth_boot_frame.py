"""Keep shoe construction rigid across the native foot and calf frames."""
import numpy as np
def positions(garment,target_bones):
    source={b['name']:b for b in garment['bones']};target={b['name']:b for b in target_bones}
    p=np.asarray(garment['positions']);result=p.copy()
    for side,sign in [('l',1),('r',-1)]:
        ids=np.flatnonzero(p[:,0]*sign>0);v=p[ids];frames=[]
        for joint in ['foot','calf']:
            a=source[joint+'_'+side];b=target[joint+'_'+side];sa=np.array(a['axes']);ta=np.array(b['axes']);sa/=np.linalg.norm(sa,axis=1)[:,None];ta/=np.linalg.norm(ta,axis=1)[:,None];rotation=np.linalg.inv(sa)@ta
            frames.append((v-a['position'])@rotation+b['position'])
        # The same smooth ankle transition drives every leather panel, lace,
        # eyelet and sole. Native skin patches are kept by the caller.
        t=np.clip((v[:,2]-12)/16.5,0,1);t=t*t*(3-2*t)
        bottom=v[:,2]<.8
        if bottom.any():frames[0][:,2]-=frames[0][bottom,2].min()
        result[ids]=frames[0]*(1-t[:,None])+frames[1]*t[:,None]
    return result.tolist()
