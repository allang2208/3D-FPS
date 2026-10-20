"""Small gun-side contact clearance; original hand shape remains immutable."""
import numpy as np
def smooth(x):
 x=np.clip(x,0,1);return x*x*(3-2*x)
def fit_surface(v,groups,part):
 p=np.asarray(v).copy();g=np.asarray(groups);factor=np.ones(len(p))
 if part=='KVInhibitor.smd':
  grip=g=='tag_pistolgrip_attach';factor[grip]=1-.31*smooth((1.46-p[grip,2])/.27)
 if part=='barrel.smd':
  guard=(g=='tag_barrel_attach')
  factor[guard]=1-.25*smooth((2.32-p[guard,2])/.33)*smooth((-.10-p[guard,0])/.8)*smooth((p[guard,0]+4.8)/.8)
 p[:,1]*=factor
 return p
