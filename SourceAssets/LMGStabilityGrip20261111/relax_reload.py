"""Wrist36 fixed-palm solve for the mobile part of an LMG reload."""
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import minimize
from scipy.ndimage import gaussian_filter1d
import rig as G

def relax_reload(world, times, grip_weights):
    clavicle, shoulder, elbow, palm, _, _ = G.indices('l')
    # The contact solve owns the seated pose. Ease the pole and twist chain
    # only through free motion where the source bends the wrist sharply.
    bend = np.array([G.bend(frame) for frame in world])
    weights = (1-grip_weights) * G.ease((bend-17)/19)
    step = float(np.median(np.diff(times)))
    weights = np.minimum(1-grip_weights, gaussian_filter1d(weights, max(1,.07/step), mode='nearest'))
    stride = max(1,round(.10/step))
    keys = np.unique(np.r_[np.arange(0,len(times),stride), len(times)-1])
    params = []
    previous = np.zeros(4)
    for i in keys:
        frame = world[i]
        if weights[i] < .002:
            previous = np.zeros(4)
        else:
            length = np.linalg.norm(frame[shoulder,:3,3]-frame[elbow,:3,3])+np.linalg.norm(frame[elbow,:3,3]-frame[palm,:3,3])
            def cost(x):
                solved = G.solve(frame,x,station_weight=0)
                return 5*max(0,G.bend(solved)-20)**2 + .045*np.sum(np.degrees(x)**2) + .035*np.sum(np.degrees(x-previous)**2)
            def reach(x):
                solved = G.solve(frame,x,station_weight=0)
                return length*.992-np.linalg.norm(solved[palm,:3,3]-solved[shoulder,:3,3])
            fit = minimize(cost,previous,method='SLSQP',bounds=[(-.5,.5)]*3+[(-1.3,1.3)],constraints=[dict(type='ineq',fun=reach)],options=dict(maxiter=65,ftol=1e-5,eps=1e-5))
            previous = fit.x if reach(fit.x)>-.01 else np.zeros(4)
        params.append(previous.copy())
    curve = PchipInterpolator(times[keys],params)(times)
    output = world.copy()
    for i, weight in enumerate(weights):
        if weight < .0001:
            continue
        frame = world[i]
        x = curve[i]*weight
        # A blended pole may approach full extension between fit keys. Fade
        # shoulder movement back toward the source before solving that frame.
        length = np.linalg.norm(frame[shoulder,:3,3]-frame[elbow,:3,3])+np.linalg.norm(frame[elbow,:3,3]-frame[palm,:3,3])
        for _ in range(7):
            solved = G.solve(frame,x,station_weight=weight)
            if np.linalg.norm(solved[palm,:3,3]-solved[shoulder,:3,3]) < length*.9999:
                break
            x[:3] *= .5
        output[i] = solved
    print('Fixed-palm reload bend',round(max(bend),1),round(max(G.bend(frame) for frame in output),1),flush=True)
    return output
