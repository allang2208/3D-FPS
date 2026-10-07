"""Azure Dragon claw V10.10 scale detail: a tiling height map of domed pebble scales.

Jittered hex cells (8 x 8 per tile, wrapped so the tile repeats seamlessly); each cell is a dome
from the Worley F2 - F1 border distance, so neighbouring scales meet in grooves.
R = height (0 groove .. 1 dome top), G = per-scale random, B = 0. Output Export/T_AzureDragonClawScaleDetail.png.
The claw material samples it triplanar on the rest pose and turns it into a derivative bump.
"""
from pathlib import Path
import numpy as np
from PIL import Image

SIZE, CELLS, JITTER, SEED = 512, 8, .28, 1006
OUT = Path(__file__).resolve().parent / 'Export' / 'T_AzureDragonClawScaleDetail.png'
rng = np.random.default_rng(SEED)
row = np.sqrt(3.) / 2.
rows = int(round(CELLS / row / 2.)) * 2  # even, so the hex offset wraps
centers, rand = [], []
for j in range(rows):
    for i in range(CELLS):
        cx = (i + .5 * (j % 2) + rng.uniform(-JITTER, JITTER)) / CELLS
        cy = (j + rng.uniform(-JITTER, JITTER) * row) / rows
        centers.append((cx % 1., cy % 1.))
        rand.append(rng.uniform())
centers, rand = np.array(centers), np.array(rand)
ys, xs = np.mgrid[0:SIZE, 0:SIZE] / SIZE
f1 = np.full((SIZE, SIZE), 9.)
f2 = np.full((SIZE, SIZE), 9.)
owner = np.zeros((SIZE, SIZE), int)
for k, (cx, cy) in enumerate(centers):
    dx = np.abs(xs - cx); dx = np.minimum(dx, 1. - dx) * CELLS
    dy = np.abs(ys - cy); dy = np.minimum(dy, 1. - dy) * rows * row
    d = np.sqrt(dx * dx + dy * dy)
    closer = d < f1
    f2 = np.where(closer, f1, np.minimum(f2, d))
    owner = np.where(closer, k, owner)
    f1 = np.where(closer, d, f1)
edge = np.clip((f2 - f1) / .55, 0., 1.)
height = np.sqrt(edge) * (.85 + .15 * rand[owner])  # domes, slightly uneven
img = np.zeros((SIZE, SIZE, 3), np.uint8)
img[..., 0] = np.clip(height * 255., 0, 255).astype(np.uint8)
img[..., 1] = np.clip(rand[owner] * 255., 0, 255).astype(np.uint8)
OUT.parent.mkdir(parents=True, exist_ok=True)
Image.fromarray(img, 'RGB').save(OUT)
print('AZURE_SCALE_DETAIL', OUT, 'cells', CELLS, 'x', rows)
