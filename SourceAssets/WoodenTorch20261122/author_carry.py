"""Bake both native arm chains together. UE samples each equipped side on its own clock."""
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

root = Path(os.environ["FPS_PROJECT_ROOT"])
source = root / "SourceAssets/WoodenTorch20261122"
sys.path.insert(0, str(root / "SourceAssets/DualKukriIdle20261025"))
from dual_rig import DualRig
from kmath import mesh_to_cam

rig = DualRig()
fps, raise_frames, breath_frames = 60, 30, 150

def fit(wrist, wanted_axis, initial):
    desired = np.array(wanted_axis) / np.linalg.norm(wanted_axis)
    def parameters(angles):
        return dict(W=wrist, phi=angles[0], psi=angles[1], de=angles[2], du=angles[3])
    def residual(angles):
        grip, elbow, _ = rig.arm(parameters(angles))
        axis = mesh_to_cam(grip.axis(2))
        return [*((axis-desired)*14.), max(0., 26. - abs(mesh_to_cam(elbow)[1]))*.2,
                (angles[0]-42.)*.006, angles[1]*.003, angles[2]*.011, angles[3]*.011]
    return least_squares(residual, initial, bounds=([-55,-115,-35,-27],[100,130,30,28])).x

# A hand rising from below the near plane turns the head up before settling.
# The top stays forward and a little outboard leaving the reticle clear.
low = np.array([15., 20., -47.])
high = np.array([34., 21., -17.])
rest = fit(high,(.29,.15,.95),(45,18,0,0))
entry = fit(low,(.86,.42,.10),(40,24,0,0))
sequence, previous = [], None
for i in range(raise_frames + breath_frames + 1):
    u = min(i/raise_frames,1.)
    s = u*u*u*(10.+u*(-15.+6.*u))
    wrist = low + (high-low)*s
    wrist[0] += 2.3*math.sin(math.pi*s)
    angles = entry + (rest-entry)*s
    # Both endpoints of the breathing loop have the same position and velocity.
    phase = 2.*math.pi*max(i-raise_frames,0)/breath_frames
    wrist += np.array([.12,.11,.22])*(1.-math.cos(phase))
    params = dict(W=tuple(wrist),phi=angles[0],psi=angles[1],de=angles[2],du=angles[3])
    pose, _, _, _ = rig.pose(params,params)
    keys = rig.R.local_keys(pose,previous)
    previous = {name: channel[1] for name,channel in keys.items()}
    sequence.append({name:[v.tolist() for v in channel] for name,channel in keys.items()})

(source/"Export/Carry.json").write_text(json.dumps(dict(fps=fps,raise_frames=raise_frames,
    bones=rig.R.rig.names,frames=sequence),separators=(",",":")),encoding="utf8")
