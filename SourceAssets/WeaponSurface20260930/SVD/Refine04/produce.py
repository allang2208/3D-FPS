"""Author SVD finish data at the A762 R06 physical detail scale.

Technical RGBA PBR data only. Original structural normals, shallow magazine
pressings, part colours, roughness hierarchy and geometry remain the baseline.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

O = Path(__file__).parent
T = O / 'Textures'
T.mkdir(exist_ok=True)
C = json.loads((O / 'Input/current.json').read_text())
old = json.loads((O.parent / 'Refine03/recipe.json').read_text())
VERSION = 'SVD-Refine04-20261001'
ROOT = '/Game/Weapons/SVDDragunov20260922/SurfaceStandard20261001/Refine04'
rng = np.random.default_rng(12100104)


def band(n, low, high):
    f = np.fft.fftfreq(n) * n
    radius = np.maximum(np.hypot(f[:, None], f[None, :]), 1e-6)
    window = np.exp(-.5 * ((np.log(radius) - np.log(np.sqrt(low * high))) / (np.log(high / low) / 2.5)) ** 2)
    window[0, 0] = 0
    field = np.fft.ifft2(np.fft.fft2(rng.standard_normal((n, n))) * window).real
    return (field - field.mean()) / max(field.std(), 1e-9)


n = 1024
fine = np.clip(.5 + band(n, 80, 240) * .13, 0, 1)
small = np.clip(.5 + band(n, 18, 55) * .11, 0, 1)
polymer = np.clip(.375 + band(n, 65, 150) * .075, 0, 1)
pixels = np.stack((fine, small, np.zeros_like(fine), polymer), -1)
name = 'T_SVD_R04_FineGrain'
file = T / (name + '.png')
Image.fromarray(np.round(pixels * 255).astype(np.uint8)).save(file)
recipe = {'version': VERSION, 'textures': {name: {'source': str(file.resolve()), 'asset': ROOT + '/Textures/' + name,
    'sha256': hashlib.sha256(file.read_bytes()).hexdigest(), 'kind': 'grain', 'tile_cm': 4,
    'channels': 'R fine roughness (0.17-0.5mm); G finish variation (0.73-2.2mm); B no scratches; A polymer grain (0.27-0.62mm)'}},
    'targets': [], 'tested': False, 'mesh_changed': False, 'wet_table_changed': False}

for prev in old['targets']:
    path = prev['material']
    current = C['materials'][path]
    family = prev['category']
    scalar = {'WS_GrainTileCm': 4., 'WS_GrainRoughness': .012, 'WS_MottleRoughness': .005,
        'WS_MottleColor': 0., 'WS_Stipple': 0., 'WS_ScratchAmount': 0.,
        'WS_EdgeHighlight': .040, 'WS_EdgeWear': .018,
        'WS_CavityDarken': .020, 'WS_CavityRoughness': .015}
    if family == 'moving steel':
        scalar.update(WS_GrainRoughness=.009, WS_MottleRoughness=.004, WS_EdgeHighlight=.030)
    elif family == 'magazine satin':
        scalar.update(WS_GrainRoughness=.009, WS_MottleRoughness=.004,
            WS_EdgeHighlight=.020, WS_EdgeWear=.012)
    elif family == 'recess':
        scalar.update(WS_EdgeHighlight=.015, WS_EdgeWear=0.)
    # Only the mixed original handguard/stock atlas gets a dielectric pass.
    # Authored markings, rubber and warm cheek pad keep their original response.
    mixed = prev['mesh'] == 'SVD' and prev['slot'] in ('SM_SVD_Body_001', 'SVD_FactoryStock')
    if mixed:
        scalar.update(R04_PolymerRoughness=.54, R04_PolymerGrain=.022,
            R04_PolymerColorCleanup=.30)
    recipe['targets'].append({'material': path, 'mesh': prev['mesh'], 'slot': prev['slot'],
        'parent': current['parent'], 'base': current['base'], 'sha256': current['sha256'],
        'category': family, 'mixed_polymer': mixed, 'scalars': scalar,
        'textures': {'WS_GrainTexture': name}})

(O / 'recipe.json').write_text(json.dumps(recipe, indent=2), encoding='utf-8')
print('SVD_R04_PRODUCED', len(recipe['targets']), 'finish instances; 1 physical-scale texture; 2 mixed furniture instances')
