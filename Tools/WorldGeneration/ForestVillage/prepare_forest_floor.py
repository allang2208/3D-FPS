"""Prepare the linear AO / roughness / displacement texture for Quixel sfjmafua."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def prepare(source):
    meta = json.loads((source / 'sfjmafua.json').read_text())
    if meta['id'] != 'sfjmafua' or not any(m['physicalSize'] == '2x2' for m in meta['maps']):
        raise ValueError('Expected the 2 m Forest Floor sfjmafua scan')

    def channel(name):
        return Image.open(next(source.glob('*_4K_' + name + '.jpg'))).convert('L')

    height = channel('Displacement')
    masks = Image.merge('RGB', (channel('AO'), channel('Roughness'), height))
    masks.save(source / 'T_ForestFloor_ARH.png')
    # For a +Y-down image, a positive Y-slope correlated with green is a +Y-up normal.
    # Derive orientation from the scan's micro-height, before BC5 normal compression.
    bump = np.asarray(channel('Bump'), dtype=np.float32)[::2, ::2]
    normal = np.asarray(Image.open(next(source.glob('*_4K_Normal.jpg'))).convert('RGB'),
                        dtype=np.float32)[::2, ::2] - 127.5
    dy, dx = np.gradient(bump)
    x = float(np.mean(dx * normal[:, :, 0]))
    y = float(np.mean(dy * normal[:, :, 1]))
    if x >= 0 or abs(y) < 0.05:
        raise ValueError(f'Ambiguous scan normal orientation ({x}, {y})')
    settings = {'scan': meta['id'], 'tile_cm': 200, 'flip_green_for_ue': y > 0,
                'normal_strength': 0.55, 'relief_cm': 1.8,
                'native_displacement_scale': meta['displacementScale'],
                'native_displacement_bias': meta['displacementBias']}
    (source / 'placement.json').write_text(json.dumps(settings, indent=2) + '\n')
    return settings


if __name__ == '__main__':
    print(prepare(Path(sys.argv[1])))
