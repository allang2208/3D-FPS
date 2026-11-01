"""Shared physical coordinates for geometry, leather folds and PBR masks (metres)."""
import numpy as np
CX,CY=-.00045,-.00105
Z0,Z1=-.069,.355
R=.01522
PITCH=.026
TAU=np.pi*2
def delta(a):return (a+np.pi)%TAU-np.pi
def conduct(a,z):
    return np.minimum(np.abs(delta(a-TAU*(z-Z0)/.106+.8)),np.abs(delta(a+TAU*(z-Z0)/.106+.8)))*R
def seam(a,z):
    # Perpendicular distance to a real helical skived leather join.
    return ((z-Z0-PITCH*(a-.2)/TAU+PITCH/2)%PITCH-PITCH/2)/np.sqrt(1+(PITCH/(TAU*R))**2)
def leather_radius(a,z):
    s=seam(a,z);d=conduct(a,z)
    saddle=.00010*np.cos((z-Z0)*TAU/.109+.45*np.sin(a*2))
    fold=.00023*np.exp(-((s-.00075)/.00073)**2)-.00026*np.exp(-(s/.00033)**2)
    tuck=-.00006*np.exp(-((s+.0016)/.0008)**2)
    channel=.00025*np.exp(-(d/.00057)**4)
    return R+saddle+fold+tuck-channel
PROFILE=[(.348,.01530),(.350,.01548),(.351,.01645),(.352,.01715),(.354,.01775),(.356,.01805),(.357,.01815),(.3588,.01815),(.3593,.01780),(.360,.01775),(.362,.01775),(.363,.01800),(.365,.01805),(.388,.01805),(.390,.01795),(.391,.01760),(.392,.01760),(.393,.0178),(.395,.0178),(.396,.0173),(.398,.0160),(.400,.01545),(.401,.0153)]
def collar_radius(a,z):
    base=np.interp(z,[q[0] for q in PROFILE],[q[1] for q in PROFILE])
    # Shallow real engraving beds under the fitted interlace ribbons.
    knot=np.minimum(abs(z-(.377+.0057*np.sin(6*a))),abs(z-(.377-.0057*np.sin(6*a))))
    mask=np.exp(-(knot/.00076)**4)*((z>.369)&(z<.385))
    return base-.00016*mask
