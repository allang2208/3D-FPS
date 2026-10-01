"""Produce the original tileable density texture used by the black mist material."""
from pathlib import Path
import random
from PIL import Image

SIZE = 256
rng = random.Random(170110)
layers = [(n, w, [[rng.random() for _ in range(n)] for _ in range(n)])
          for n, w in [(4, .55), (8, .27), (16, .13), (32, .05)]]
pixels = []
for y in range(SIZE):
    for x in range(SIZE):
        value = 0.
        for n, weight, grid in layers:
            px, py = x * n / SIZE, y * n / SIZE
            ix, iy = int(px), int(py)
            fx, fy = px - ix, py - iy
            fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
            a = grid[iy % n][ix % n] * (1 - fx) + grid[iy % n][(ix + 1) % n] * fx
            b = grid[(iy + 1) % n][ix % n] * (1 - fx) + grid[(iy + 1) % n][(ix + 1) % n] * fx
            value += weight * (a * (1 - fy) + b * fy)
        pixels.append(round(value * 255))
image = Image.new('L', (SIZE, SIZE))
image.putdata(pixels)
image.save(Path(__file__).with_name('slag_density_noise.png'))
print('SLAG_MIST_DENSITY_TEXTURE_WRITTEN')
