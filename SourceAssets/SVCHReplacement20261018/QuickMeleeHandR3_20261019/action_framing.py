"""Stationary SVCH action framing from UpdateViewmodel/QuickCombatRecovery.

The headless pose fixture captures the calibrated hip anchor. Gameplay blends
that anchor to M4ActionViewmodelLocation while the action is busy.
"""
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
def camera_for_frame(hip,frame):
    alpha=0.
    for f in range(1,max(0,frame)+1):
        alpha=1-(1-alpha)*np.exp(-16/120)
        t=np.clip((f/120/.9-.6)/.4,0,1)
        alpha=min(alpha,1-t*t*t*(10+t*(-15+6*t)))
    out=hip.copy();out[:3,3]=(1-alpha)*hip[:3,3]+alpha*np.array([10.,0.,-5.])
    rotation=Slerp([0,1],R.from_matrix([hip[:3,:3],R.from_euler('z',90,degrees=True).as_matrix()]))([alpha]).as_matrix()[0]
    out[:3,:3]=rotation
    return out
