"""A762 factory-derived curve, metres in the authored WPN_root frame."""
import numpy as np

POINTS = np.array([[(-.132,.030),(-.144,-.025),(-.160,-.060),(-.209,-.087)],
                   [(-.064,.030),(-.063,-.031),(-.103,-.085),(-.173,-.136)]])
T = np.linspace(0., 1., 20001)
B = np.stack(((1-T)**3, 3*(1-T)**2*T, 3*(1-T)*T*T, T**3), 1)
AB = np.einsum('tk,akd->atd', B, POINTS)
C = AB.mean(0)
ARC = np.r_[0., np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]
L = float(ARC[-1])
KEEP = .080
EXTRA = .042
END = L + EXTRA
S = np.linspace(0., END, 30001)
q = np.clip((S-KEEP)/(END-KEEP), 0., 1.)
# Re-time tangent/section evolution, not vertex heights. Derivative is 1 at
# both ends, so the retained upper surface and moved end have C2 centreline
# joins. Cross ribs are independently placed by actual arc distance.
PHI = S - EXTRA*q*q*(3.-2.*q)
dC = np.gradient(C, ARC, axis=0)
theta = np.unwrap(np.arctan2(-dC[:,0], -dC[:,1]))
ANGLE = np.interp(PHI, ARC, theta)
tan = -np.stack((np.sin(ANGLE), np.cos(ANGLE)), 1)
NEW = np.vstack((C[0], C[0] + np.cumsum((tan[:-1]+tan[1:])*.5*np.diff(S)[:,None],axis=0)))
upper = S <= KEEP
NEW[upper] = np.stack([np.interp(S[upper], ARC, C[:,i]) for i in range(2)],1)
delta = AB[1] - AB[0]

def at(s):
    """Centre, front-to-back section direction and half-depth at arc s."""
    s = np.asarray(s)
    src = np.interp(s, S, PHI)
    centre = np.stack([np.interp(s, S, NEW[:,i]) for i in range(2)],-1)
    span = np.stack([np.interp(src, ARC, delta[:,i]) for i in range(2)],-1)
    half = np.linalg.norm(span,axis=-1)*.5
    return centre, span/(half[...,None]*2), half

def arc(t):
    return float(np.interp(t,T,ARC))

def extended_s(t):
    return float(np.interp(arc(t), PHI, S))

RIB_ORIGINAL = np.interp(np.linspace(.12,.925,10),T,ARC)
# Preserve the upper ribs. Continue their local pitch below the grip area,
# placing whole ribs; no stretched half-ribs at an extension cut.
RIBS = list(RIB_ORIGINAL[RIB_ORIGINAL <= KEEP])
PITCH = float(RIB_ORIGINAL[5]-RIB_ORIGINAL[4])
while RIBS[-1] + PITCH < END - .012:
    RIBS.append(RIBS[-1] + PITCH)

def report():
    q = np.clip((-AB[:,:,1]-.023)/.113,0,1)
    old = AB + np.stack((-.023*q*q*(3-2*q),-.044*q*q*(3-2*q)),2)
    return {'factory_length_mm':L*1000,'new_length_mm':END*1000,'extra_arc_mm':EXTRA*1000,
        'retained_upper_arc_mm':KEEP*1000,'factory_bottom_span_mm':float(np.linalg.norm(delta[-1])*1000),
        'old_extended_bottom_span_mm':float(np.linalg.norm(old[1,-1]-old[0,-1])*1000),
        'new_bottom_span_mm':float(at(END)[2]*2000),'cross_rib_centres_mm':[v*1000 for v in RIBS],
        'extension_pitch_mm':PITCH*1000,'new_bottom_centre':NEW[-1].tolist(),
        'factory_bottom_centre':C[-1].tolist(),'terminal_tangent_deg':float(np.degrees(ANGLE[-1]))}
