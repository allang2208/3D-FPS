"""Solve the visible sword and wrist paths on each installed Highland grip."""
from pathlib import Path
import json
import cv2
import numpy as np
from scipy.interpolate import PchipInterpolator

HERE = Path(__file__).resolve().parent
SWEEP = HERE.parent / 'HighlandBroadbladeSweep20261104'
FOCAL = 90 / np.tan(np.deg2rad(37.5))
FLIP = np.diag([1., -1., 1.])
MID = np.array([160, 90])
LENGTH = 88.

def unit(v):
    return v / max(np.linalg.norm(v), 1e-8)

def ray(uv):
    return np.array([(uv[0]-160)/FOCAL, 1., (90-uv[1])/FOCAL])

def screen(p):
    return MID + FOCAL * p[[0,2]] * [1,-1] / max(p[1], 2.)

def read_frames():
    keys = np.loadtxt(HERE/'screen.txt')
    frames = np.arange(int(keys[0,0]), int(keys[-1,0])+1)
    # A guard is a line; interpolation must cross the 180-degree seam continuously.
    keys[:,6] = np.rad2deg(np.unwrap(np.deg2rad(keys[:,6])*2)) / 2
    guide = PchipInterpolator(keys[:,0], keys[:,1:])(frames)
    cap = cv2.VideoCapture(str(SWEEP/'ReferenceV2/kubold-indexed.mp4'))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(frames[0]))
    for i,n in enumerate(frames):
        ok,im = cap.read()
        if not ok: raise RuntimeError(f'Missing source frame {n}')
        # Subpixel localization at 1280x720, using the first contiguous pale
        # steel pixels along the annotated blade. Ignore the screened-out tip.
        tip = guide[i,2:4]; axis = unit(guide[i,:2]-tip)
        if not (4 < tip[0] < 316 and 4 < tip[1] < 176): continue
        offsets = np.arange(-9., 10., .25)
        samples = np.rint((tip+offsets[:,None]*axis)*4).astype(int)
        pixels = im[samples[:,1].clip(0,719),samples[:,0].clip(0,1279)].astype(float)
        bright = (pixels.min(1)>90) & (pixels.mean(1)>135)
        runs = np.flatnonzero(np.convolve(bright.astype(float), np.ones(6), 'valid')==6)
        if len(runs): guide[i,2:4] += axis*offsets[runs[0]]
    cap.release()
    return frames,guide

if __name__=='__main__':
    # Image observations, then constrained fitting on the two native grips.
    import sys,runpy
    sys.path.insert(0,str(HERE/'Review'))
    from compare import reference
    from refit import solve
    reference()
    runpy.run_path(str(HERE/'Review/edge.py'),run_name='__main__')
    for grip in ('Standard','LongGrip'):
        solve(grip)
