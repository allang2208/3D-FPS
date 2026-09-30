"""Find pouch-holding hand orientations with low shoulder twist and wrist bend."""
import sys, json
import numpy as np
sys.path[:0] = [r'C:\Users\allan\AppData\Local\Temp\lmg201_work', r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44\Diagnostics']
import diag_lib as D, rig as K
import author_motion as AM

idle = json.loads((D.HERE / 'Inputs/201_idle.json').read_text())
W0 = D.worlds({n: np.array([v]) for n, v in zip(D.NAMES, idle['poses'][0])})[0]
arm = K.Arm('l', D.NAMES, D.PARENT, D.REST, W0)
sel = AM.BODY.parts['LMG201_Box']
pts = D.Skin(AM.BODY.pos[sel], (AM.BODY.bi[sel], AM.BODY.bw[sel])).pose(W0)
bc = pts.mean(0)
shape = AM.SHAPES['box']
lm = AM.landmark(shape, 'palm')
EYE = D.camera(1.0)[0]
contacts = {'under': (np.array([bc[0] - 1.5, bc[1] + .3, pts[:, 2].min() - 1.7]), np.array([0, 0, 1.0])),
            'left': (np.array([pts[:, 0].min() - 1.8, bc[1] + .3, bc[2] + .6]), np.array([1.0, 0, 0])),
            'left_low': (np.array([pts[:, 0].min() - 1.5, bc[1] + .3, bc[2] - 3.0]), unit := None)}
contacts['left_low'] = (contacts['left_low'][0], np.array([.8, 0, .6]) / 1.0)
rng = np.random.default_rng(3)
for name, (c, n) in contacts.items():
    n = n / np.linalg.norm(n)
    best = []
    for _ in range(1500):
        f = rng.normal(size=3)
        f -= n * (f @ n)
        f /= np.linalg.norm(f)
        R = AM.hand_rot(f, n)          # palm faces the pouch
        T = c - R @ lm
        for psi in np.radians(np.arange(-180, 180, 15)):
            ax = K.unit(T - arm.positions(T, arm.pole0)['A'])
            pole = K.axis_angle(ax, psi) @ np.array([-.85, .2, -.5])
            pos = arm.positions(T, pole)
            tau = np.degrees(arm.tau_of(pos, R)[0])
            Dh = R @ arm.Rrest['hand'].T
            bend = np.degrees(np.arccos(np.clip(K.unit(Dh @ arm.cF0) @ K.unit(pos['T'] - pos['E']), -1, 1)))
            eye = np.linalg.norm(pos['E'] - EYE)
            if pos['reach'] > .93:
                continue
            best.append((abs(tau) / 60 + max(0, bend - 40) / 20 + max(0, 20 - eye) / 10, tau, bend, np.round(f, 2), np.degrees(psi), np.round(pos['E'], 1)))
    best.sort(key=lambda x: x[0])
    print(name, 'contact', np.round(c, 1))
    for b in best[:5]:
        print('   cost %.2f tau %6.1f bend %5.1f finger %s psi %5.0f elbow %s' % b)
