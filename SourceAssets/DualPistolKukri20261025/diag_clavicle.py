"""Clavicle/shoulder frames: our V7 left arm (bind clavicle, LS_REST root) vs the mirrored main-hand clip."""
import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import author_upper as U
A = U.A


def ang(a, b):
    return float(np.degrees(R.from_matrix(a @ b.T).magnitude()))


LR = A.LR
w0 = U.world_at(0)
mc0 = U.mir(w0['clavicle_r'])
mu0 = U.mir(w0['upperarm_r'])
print('LS_REST', np.round(U.LS_REST, 2), ' ours clav pos', np.round(LR['clavicle_l'][:3, 3], 2), ' ours upper bind pos', np.round(LR['upperarm_l'][:3, 3], 2))
print('clip SH0', np.round(U.SH0, 2), ' clip clav pos', np.round(mc0[:3, 3], 2))
print('clav->upper offset ours %s  clip %s' % (np.round(LR['upperarm_l'][:3, 3] - LR['clavicle_l'][:3, 3], 2), np.round(mu0[:3, 3] - mc0[:3, 3], 2)))
print('bind clavicle vs mirrored clip clavicle (frame 0): %.1f deg' % ang(LR['clavicle_l'][:3, :3], mc0[:3, :3]))
print('clavicle local X ours %s  clip %s' % (np.round(LR['clavicle_l'][:3, 0], 3), np.round(mc0[:3, 0], 3)))
ref_clip = {n: U.mat_of(t) for n, t in U.rig.world({n: U.rig.ref_local[n] for n in U.rig.names}).items()}
loc_ours = np.linalg.inv(LR['clavicle_l']) @ LR['upperarm_l']
loc_clip = np.linalg.inv(ref_clip['clavicle_r']) @ ref_clip['upperarm_r']
print('bind clav->upper local: ours vs mirrored clip ref %.1f deg' % ang(loc_ours[:3, :3], U.S3 @ loc_clip[:3, :3] @ U.S3))
for i in range(0, len(U.clip['frames']), 8):
    w = U.world_at(i)
    mc = U.mir(w['clavicle_r'])
    print('t=%.3f clip clav rot vs frame0 %.1f deg, pos shift %s' % (i / U.FPS, ang(mc[:3, :3], mc0[:3, :3]), np.round(mc[:3, 3] - mc0[:3, 3], 2)))
