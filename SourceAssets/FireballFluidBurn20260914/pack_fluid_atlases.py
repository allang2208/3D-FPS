"""Shade baked combustion fields into two looped runtime RGBA flipbooks.

This is the production volume-to-texture bake, not a preview or screenshot.
RGB is straight, sRGB-encoded emission color; alpha is independent optical
coverage. Atlas RGB is premultiplied only in the UE material after depth fade.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
FIRST, SAMPLES, LOOP, OVERLAP, TILE = 49, 96, 64, 32, 256


def shade(flame, axis):
    f = np.maximum(flame, 0)
    step = 2.0 / f.shape[axis]
    extinction = np.power(f, .78) * (6.0 * step)
    transmission = np.exp(-(np.cumsum(extinction, axis=axis) - extinction))
    weight = transmission * (-np.expm1(-extinction))
    coverage = np.sum(weight, axis=axis)
    # Art-directed heat ramp, not a claim that the flame grid is temperature.
    heat = np.clip(f * 1.02, 0, 1)
    knots = [0, .10, .28, .52, .78, 1]
    colors = np.array([[.48,.004,.0004],[.85,.035,.001],
                       [1,.16,.004],[1,.40,.025],[1,.72,.14],[1,.94,.53]])
    emission = np.stack([np.sum(weight * np.interp(heat, knots, colors[:, c]), axis=axis)
                         for c in range(3)], axis=-1)
    color = emission / np.maximum(coverage[..., None], 1e-7)
    linear = np.concatenate([color, coverage[..., None]], axis=-1).astype(np.float32)
    # Static physical crop: x/y [-.72,.72], z [-.42,1.02] in the 2 m domain.
    h, w = linear.shape[:2]
    linear = linear[round(.13*h):round(.85*h), round(.14*w):round(.86*w)]
    linear = np.flipud(linear)
    return np.stack([np.array(Image.fromarray(linear[..., c], mode='F').resize(
        (TILE, TILE), Image.Resampling.BICUBIC)) for c in range(4)], axis=-1)


def encode(frame):
    frame = np.clip(frame, 0, 1)
    rgb = frame[..., :3]
    srgb = np.where(rgb <= .0031308, 12.92 * rgb, 1.055 * np.power(rgb, 1/2.4) - .055)
    return np.round(np.concatenate([srgb, frame[..., 3:4]], axis=-1) * 255).astype(np.uint8)


def main():
    output = ROOT / 'Textures'
    output.mkdir(exist_ok=True)
    frames = [[], []]
    for index in range(SAMPLES):
        field = np.load(ROOT / 'Fields' / f'flame_{FIRST+index:04d}.npz')['flame']
        for view, axis in enumerate([1, 2]):
            frames[view].append(shade(field, axis))
        if index % 12 == 0:
            print('FIREBALL_VOLUME_BAKE_FRAME', FIRST + index, flush=True)
    for view, label in enumerate(['A', 'B']):
        atlas = Image.new('RGBA', (TILE * 8, TILE * 8))
        for index in range(LOOP):
            frame = frames[view][index]
            if index < OVERLAP:
                amount = .5 - .5 * np.cos(np.pi * index / (OVERLAP - 1))
                other = frames[view][LOOP + index]
                # Crossfade in premultiplied linear space to avoid dark seams.
                alpha = other[..., 3:4] * (1-amount) + frame[..., 3:4] * amount
                premul = (other[..., :3] * other[..., 3:4] * (1-amount)
                          + frame[..., :3] * frame[..., 3:4] * amount)
                frame = np.concatenate([premul / np.maximum(alpha, 1e-7), alpha], axis=-1)
            atlas.paste(Image.fromarray(encode(frame)), ((index % 8)*TILE, (index // 8)*TILE))
        atlas.save(output / f'T_FireballFluid_{label}.png')
        print('FIREBALL_ATLAS_WRITTEN', label, flush=True)
    (ROOT / 'atlas.json').write_text(json.dumps({
        'source': 'Original Mantaflow combustion cache produced by author_fluid.py',
        'textures': ['Textures/T_FireballFluid_A.png','Textures/T_FireballFluid_B.png'],
        'atlas_grid': [8,8], 'frame_pixels': TILE, 'frames': LOOP, 'fps': 24,
        'duration_seconds': LOOP/24, 'views': ['along Y', 'along X'],
        'encoding': 'straight sRGB emission RGB and independent linear optical coverage alpha',
        'loop': '32-frame cosine overlap in premultiplied linear space; seam follows original adjacent frames 112 and 113',
        'lighting': 'Art-directed heat palette from simulated flame concentration; no baked background or sphere mesh',
        'authoring': 'Beer-Lambert volume integration of simulated fields',
        'status': 'Production texture bake only; no visual/runtime testing',
    }, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
