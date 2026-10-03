"""Colour/texture probes on the user's screenshot to identify the oversized surface."""
from PIL import Image
import numpy as np

im = Image.open(r'D:\FPS3D\FPSGAME\SourceAssets\SVDReloadLeftArm20260925\user_report.png').convert('RGB')
a = np.asarray(im).astype(float)
print('image', a.shape)

def stats(name, x0, y0, x1, y1):
    r = a[y0:y1, x0:x1]
    g = r.mean(axis=2)
    hp = np.abs(np.diff(g, axis=0)).mean()
    hp2 = np.abs(np.diff(g, axis=1)).mean()
    print(f'{name:16s} mean RGB {np.round(r.reshape(-1,3).mean(0),1)} '
          f'std {r.reshape(-1,3).std(0).round(1)} gradV {hp:.2f} gradH {hp2:.2f}')

stats('hand-on-gun', 1290, 590, 1400, 700)
stats('mass-mid', 500, 500, 900, 800)
stats('mass-left', 60, 350, 380, 620)
stats('mass-far-edge', 900, 380, 1200, 520)
stats('floor', 1700, 780, 2000, 860)
stats('sky', 1500, 60, 1900, 200)
stats('building', 1450, 300, 1650, 340)

# silhouette extent of the pale mass: pink-ish pixels
r, g, b = a[..., 0], a[..., 1], a[..., 2]
pale = (r > 150) & (r > b + 12) & (g > 120) & (b < r - 10)
print('pale pixels', int(pale.sum()), 'of', pale.size)
rows = np.where(pale.any(axis=1))[0]
cols = np.where(pale.any(axis=0))[0]
print('pale bbox rows', rows.min(), rows.max(), 'cols', cols.min(), cols.max())
for y in range(200, 880, 80):
    line = pale[y]
    if line.any():
        xs = np.where(line)[0]
        print(f'  y={y:4d} pale x {xs.min():4d}..{xs.max():4d} count {line.sum()}')
