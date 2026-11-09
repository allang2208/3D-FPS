"""M249 factory optic seat, in original art centimetres (X rear, Y right, Z up).

The rail is source island 54 on PKM_Cover; the optic sole is island 97.
Planes come from their actual horizontal contact faces, not whole-object bounds.
"""
import numpy as np

RAIL_PLANE=np.array([-.0141819599,.0000374318241,9.82525690])
SOLE_PLANE=np.array([.00877137,.00938903,6.36739089])
SOLE_ANCHOR=np.array([18.467339,.17427523,6.5270605])
SEAT_XY=np.array([6.,.18857792])
CONTACT_GAP_CM=.01
SOURCE_REAR=np.array([20.70,.14,9.775])
SOURCE_FRONT=np.array([12.59,.17,9.913])

def unit(v):return v/np.linalg.norm(v)
def frame(x,up):
    x=unit(x);y=unit(np.cross(up,x));return np.column_stack((x,y,np.cross(x,y)))
SOURCE_FRAME=frame(SOURCE_REAR-SOURCE_FRONT,np.array([0.,0.,1.]))
RAIL_FRAME=frame(np.array([1.,0.,RAIL_PLANE[0]]),np.array([-RAIL_PLANE[0],-RAIL_PLANE[1],1.]))
ROTATION=RAIL_FRAME@SOURCE_FRAME.T
SEAT=np.r_[SEAT_XY,np.r_[SEAT_XY,1.]@RAIL_PLANE+CONTACT_GAP_CM]

def transform(points):return (np.asarray(points)-SOLE_ANCHOR)@ROTATION.T+SEAT
def fit_sole(points):
    p=np.asarray(points);q=transform(p)
    # Conform only the low mounting shoe to the rail crown. Retain the source
    # clamp's hooks below the contact plane and the complete optical housing.
    sole=p.copy();sole[:,2]=np.c_[p[:,:2],np.ones(len(p))]@SOLE_PLANE
    mapped=transform(sole)
    delta=np.c_[mapped[:,:2],np.ones(len(p))]@RAIL_PLANE+CONTACT_GAP_CM-mapped[:,2]
    w=np.clip((7.28-p[:,2])/.58,0.,1.);w=w*w*(3-2*w)
    q[:,2]+=delta*w
    return q

def sights():
    return {'WPN_RearSight':transform(SOURCE_REAR).tolist(),'WPN_FrontSight':transform(SOURCE_FRONT).tolist()}
