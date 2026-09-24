"""Author seamless surface/normal maps for the five tier crates (wood, stone, iron, gold, silver).
Background Blender run (numpy + bpy image save). Not preview renders.
"""
import bpy, numpy as np
from pathlib import Path

OUT = Path(__file__).parent / 'Textures'; OUT.mkdir(exist_ok=True)
N = 1024
stats = {}

def make_noise(rng, scale):
    data = rng.normal(size=(N, N))
    fy = np.fft.fftfreq(N)[:, None]; fx = np.fft.fftfreq(N)[None, :]
    data = np.fft.ifft2(np.fft.fft2(data) * np.exp(-(fx * fx + fy * fy) * scale * scale)).real
    return np.clip((data - data.mean()) / (data.std() * 5) + .5, 0, 1)

def write(name, rgb):
    stats[name] = [round(float(rgb[..., i].mean()), 3) for i in range(3)]
    pixels = np.concatenate([rgb, np.ones((N, N, 1))], axis=2).astype(np.float32)
    image = bpy.data.images.new(name, width=N, height=N, alpha=True)
    image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(pixels.ravel())
    image.filepath_raw = str(OUT / (name + '.png')); image.file_format = 'PNG'; image.save()
    bpy.data.images.remove(image)

def normal_from(height, strength):
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * strength
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * strength
    normal = np.stack((-dx, dy, np.ones_like(dx)), axis=2)
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    return normal * .5 + .5

def lines(axis, count, width):
    """Seamless repeating grooves along one axis (plank seams)."""
    t = np.arange(N)
    coord = t[None, :] if axis == 0 else t[:, None]
    d = np.abs((coord % (N // count)) - N // count // 2)
    return np.clip((d.astype(float) - width) / 3.0, 0, 1)

# --- Wood: stretched grain along U + plank seams + gouges
rng = np.random.default_rng(412024)
uy, ux = np.mgrid[0:N, 0:N]
stretched = make_noise(rng, 26)
fine = make_noise(rng, 2)
ring = np.clip((np.sin((ux * .55 + stretched * 90) * np.pi / 64) + 1) / 2, 0, 1)
gouges = np.zeros((N, N))
for _ in range(140):
    y = int(rng.integers(N)); x0 = int(rng.integers(N)); length = int(rng.integers(120, 700)); w = int(rng.integers(1, 3))
    for step in range(length):
        gouges[(y + int(rng.normal() * .6)) % N, (x0 + step) % N] = rng.uniform(.4, 1)
seam = lines(1, 6, 2.5)
height = ring * .18 + fine * .12 + stretched * .10 - gouges * .22 - (1 - seam) * .5
broad = np.clip(ring * .55 + stretched * .45, 0, 1) * (seam * .55 + .45)
rough = np.clip(.55 + fine * .25 - ring * .12 + gouges * .18 - (1 - seam) * .25, 0, 1)
write('T_Crate_Wood_Surface', np.stack((broad, fine, rough), axis=2))
write('T_Crate_Wood_Normal', normal_from(height, .5))

# --- Stone: blocky lumps, pits, cracks
rng = np.random.default_rng(777202)
lump = make_noise(rng, 14)
detail = make_noise(rng, 3)
pits = make_noise(rng, 6)
cracks = np.zeros((N, N))
for _ in range(60):
    x, y = int(rng.integers(N)), int(rng.integers(N)); angle = rng.uniform(0, 2 * np.pi)
    for step in range(int(rng.integers(30, 200))):
        angle += rng.normal() * .35
        x = int(x + np.cos(angle)) % N; y = int(y + np.sin(angle)) % N
        cracks[y, x] = 1
height = lump * .30 + detail * .18 + pits * .12 - cracks * .45
write('T_Crate_Stone_Surface', np.stack((lump, detail, np.clip(.72 + pits * .2 + cracks * .15, 0, 1)), axis=2))
write('T_Crate_Stone_Normal', normal_from(height, .42))

# --- Metals: iron (hard, pitted), gold (soft), silver (clean, bright)
for family, seed, pitted, scratchy, rmin in (('Iron', 92223, .45, .15, 0), ('Gold', 92224, .09, .13, .12), ('Silver', 92225, .06, .07, .22)):
    rng = np.random.default_rng(seed)
    broad = make_noise(rng, 90); grain = make_noise(rng, 3); pits = make_noise(rng, 10)
    scratches = np.zeros((N, N))
    for _ in range(350):
        x = int(rng.integers(N)); y = int(rng.integers(N)); length = int(rng.integers(4, 90)); slope = rng.uniform(-.25, .25)
        for step in range(length):
            scratches[(y + step) % N, (x + int(step * slope)) % N] = rng.uniform(.3, .9)
    height = (grain * .22 + pits * pitted - scratches * scratchy) if family == 'Iron' else grain * .09 + pits * pitted - scratches * scratchy
    rough = np.clip(grain * .3 + broad * .45 + scratches * .25 + rmin, 0, 1)
    write('T_Crate_' + family + '_Surface', np.stack((broad, grain, rough), axis=2))
    write('T_Crate_' + family + '_Normal', normal_from(height, .45))

print('CRATE_MAPS_WRITTEN ' + str(OUT))
import json
print('CRATE_MAP_STATS ' + json.dumps(stats))
