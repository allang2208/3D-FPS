"""One clock for authored poses, blade tension and the generated camera timeline."""
import numpy as np
from scipy.interpolate import PchipInterpolator

FPS = 120
DURATION = 2.8
RELEASE = 1.64
TIME = np.array([0., .22, .58, .82, 1.40, 1.57, RELEASE, 1.82, 2.10, 2.50, 2.70, DURATION])
PHASE = np.array([0., .12, .32, .47, .60, .70, .745, .90, 1.10, 1.43, 1.61, 1.70])
SOURCE_TIME = PchipInterpolator(TIME, PHASE)

def ease(a, b, t):
    x = np.clip((t-a)/(b-a), 0., 1.)
    return x*x*x*(10.+x*(-15.+6.*x))

def tension(t):
    envelope = ease(.62, 1.08, t)*(1.-ease(1.45, 1.64, t))
    age = t-.62
    return envelope*(np.sin(2.*np.pi*8.*age)+.24*np.sin(2.*np.pi*11.5*age))

def recoil(t, start, hz, decay, end):
    age = max(0., t-start)
    return np.sin(age*2.*np.pi*hz)*np.exp(-decay*age)*(1.-ease(end-.12, end, t))
