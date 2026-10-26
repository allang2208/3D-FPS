"""Fast flat-shaded check of the candidate from the game eye (vertical FOV 75, 16:9) beside the reference hold.

Not a material preview: painter-sorted triangles, one key light. Output Work/quick_<name>.jpg.
"""
import sys, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import cv2

P = Path(__file__).resolve().parent
REF = Path('D:/FPS3D/FPSGAME/Saved/Reference/DualPistolKukriBV1hQnh6hEio20261025/idle_frames/f01525.png')
W, H = 960, 540
DEBUG_SIDES = '--sides' in sys.argv
TAG = '_ads' if '--ads' in sys.argv else ''
FOV = json.loads((P / ('candidate%s.json' % TAG)).read_text(encoding='utf-8'))['controls']['vertical_fov']
TAN = np.tan(np.radians(FOV / 2))


def layer(npz, colour):
    d = np.load(P / npz)
    X, T = d['X'], d['T']
    return X, T, np.array(colour)


def render(path):
    parts = [layer('arms_camera%s.npz' % TAG, (.78, .58, .46)), layer('gun_camera%s.npz' % TAG, (.22, .24, .27)), layer('kukri_camera%s.npz' % TAG, (.62, .64, .66))]
    if DEBUG_SIDES:
        X, T, col = parts[0]; left = np.load(P / 'Work/tri_left.npy')
        parts[0:1] = [(X, T[left], np.array((.45, .62, .85))), (X, T[~left], col)]
    polys, shade, depth = [], [], []
    light = np.array([-.5, -.3, .8]); light /= np.linalg.norm(light)
    for X, T, col in parts:
        tri = X[T]
        if 'kukri' in str(col): pass
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
        c = tri.mean(axis=1)
        n = np.where((np.einsum('ij,ij->i', n, c) > 0)[:, None], -n, n)   # face the eye
        ok = tri[:, :, 0].min(axis=1) > 2
        tri, n, c = tri[ok], n[ok], c[ok]
        sx = W / 2 + tri[:, :, 1] / (tri[:, :, 0] * TAN * 16 / 9) * W / 2
        sy = H / 2 - tri[:, :, 2] / (tri[:, :, 0] * TAN) * H / 2
        lam = np.clip(n @ light, 0, 1) * .75 + .25
        polys.append(np.stack([sx, sy], axis=2)); shade.append(lam[:, None] * col); depth.append(np.linalg.norm(c, axis=1))
    polys, shade, depth = np.concatenate(polys), np.concatenate(shade), np.concatenate(depth)
    order = np.argsort(-depth)
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100); ax = fig.add_axes([0, 0, 1, 1])
    ax.add_collection(PolyCollection(polys[order], facecolors=np.clip(shade[order], 0, 1), edgecolors='none'))
    ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.set_facecolor((.12, .13, .15)); ax.axis('off')
    ax.plot([W / 2 - 6, W / 2 + 6], [H / 2, H / 2], color='w', lw=.8); ax.plot([W / 2, W / 2], [H / 2 - 6, H / 2 + 6], color='w', lw=.8)
    fig.savefig(path, dpi=100, facecolor=(.12, .13, .15)); plt.close(fig)


def main(name):
    (P / 'Work').mkdir(exist_ok=True)
    out = P / 'Work' / ('quick_%s.png' % name)
    render(out)
    ours = cv2.imread(str(out))
    ref = cv2.imread(str(REF)); h, w = ref.shape[:2]; cw = int(h * 16 / 9); x0 = (w - cw) // 2
    ref = cv2.resize(cv2.convertScaleAbs(ref[:, x0:x0 + cw], alpha=1.5, beta=20), (W, H))
    cv2.putText(ref, 'reference 50.83 s (16:9 crop)', (10, 24), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 255, 255), 2)
    cv2.putText(ours, 'candidate, game eye vFOV %d' % FOV, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 255, 255), 2)
    cv2.imwrite(str(P / 'Work' / ('quick_%s.jpg' % name)), np.hstack([ref, ours]), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print('QUICK', out)


if __name__ == '__main__':
    main(next((a for a in sys.argv[1:] if not a.startswith('--')), 'v1'))
