"""Author physical-scale finish data and ASH12-specific role/region recipes."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

O = Path(__file__).parent
T = O / 'Textures'
T.mkdir(exist_ok=True)
C = json.loads((O / 'Input/current.json').read_text())
ROOT = '/Game/Weapons/ASH12/SurfaceStandard20260930/Refine02'
VERSION = 'ASH12-Refine02-20261001'
rng = np.random.default_rng(121002)


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
poly = np.clip(.375 + band(n, 65, 150) * .075, 0, 1)
name = 'T_ASH12_R02_FineGrain'
file = T / (name + '.png')
Image.fromarray(np.round(np.stack((fine, small, np.zeros_like(fine), poly), -1) * 255).astype(np.uint8)).save(file)
R = {'version': VERSION, 'textures': {name: {'source': str(file.resolve()), 'asset': ROOT + '/Textures/' + name,
    'sha256': hashlib.sha256(file.read_bytes()).hexdigest(), 'tile_cm': 4.,
    'channels': 'R metal grain 0.17-0.5mm; G small finish variation 0.73-2.2mm; B no scratches; A polymer grain 0.27-0.62mm'}},
    'targets': [], 'tested': False, 'mesh_changed': False, 'wet_table_changed': False}

metal = {'GrainTileCm': 4., 'GrainRoughness': .012, 'MottleRoughness': .005,
    'MottleColor': 0., 'Stipple': 0., 'ScratchAmount': 0., 'HandlingPolish': 0.,
    'EdgeHighlight': .040, 'EdgeWear': .018, 'CavityDarken': .020, 'CavityRoughness': .015}
polymer = dict(metal, GrainRoughness=.020, MottleRoughness=.006, Stipple=.028,
    EdgeHighlight=.020, EdgeWear=0., CavityDarken=.030, CavityRoughness=.020)
rubber = dict(polymer, GrainRoughness=.018, Stipple=.025, EdgeHighlight=.010,
    CavityDarken=.040, CavityRoughness=.025)
roles = {
    'M_ASH12_Lower': (.39, [.034, .035, .037]),
    'M_ASH12_Upper': (.37, [.030, .032, .035]),
    'M_ASH12_Front': (.44, [.027, .029, .031]),
    'M_ASH12_Sights': (.45, [.020, .021, .022]),
    'M_ASH12_Flash_Hider': (.47, [.026, .028, .030]),
    'M_ASH12_Magazine': (.55, [.019, .019, .018]),
    'M_ASH12_Magazine_Base': (.58, [.017, .018, .018]),
    'ASH_GripMetal': (.42, [.032, .033, .035]),
    'ASH_OpticShoe': (.45, [.020, .021, .022]),
    'ASH12Tac_Shell': (.47, [.026, .028, .030]),
    'ASH12Tac_Mount': (.43, [.031, .033, .035]),
    'ASH_BrakeShell': (.44, [.028, .030, .032]),
    'ASH_BrakeMount': (.45, [.020, .021, .022]),
    'ASH12Cheek_Steel': (.42, [.032, .033, .035]),
}
region = {'RegionBoltRoughness': .32,
    'R02_RegionPolymerGrainRoughness': .020, 'R02_RegionPolymerMottleRoughness': .006,
    'R02_RegionPolymerStipple': .028, 'R02_RegionPolymerEdgeHighlight': .020,
    'R02_RegionPolymerCavityDarken': .030, 'R02_RegionPolymerCavityRoughness': .020,
    'R02_RegionBoltGrainRoughness': .009, 'R02_RegionBoltMottleRoughness': .004,
    'R02_RegionBoltEdgeHighlight': .030, 'R02_RegionBoltCavityDarken': .015,
    'R02_RegionBoltCavityRoughness': .012}

for path, current in C['materials'].items():
    preset = current['preset']
    scalars = dict(polymer if preset == 'CleanPolymer' else rubber if preset == 'Rubber' else metal)
    vectors = {}
    slot = current['slot']
    if slot in roles:
        scalars['Roughness'], vectors['FinishColor'] = roles[slot]
        if preset in ('CleanSatinSteel', 'CleanAnodized'):
            scalars['EdgeRoughness'] = max(.29, scalars['Roughness'] - .055)
            vectors['EdgeColor'] = [round(v * 1.6, 5) for v in vectors['FinishColor']]
    elif preset == 'CleanPolymer':
        scalars['Roughness'] = .55
    elif preset == 'Rubber':
        scalars['Roughness'] = .68
    if current['regional']:
        scalars.update(region)
        vectors['RegionBoltColor'] = [.040, .042, .044]
        if slot == 'M_ASH12_Upper':
            # Red is a butt pad in Upper, not the polymer grip in Lower.
            scalars.update(RegionPolymerRoughness=.68, R02_RegionPolymerGrainRoughness=.018,
                R02_RegionPolymerStipple=.025, R02_RegionPolymerEdgeHighlight=.010,
                R02_RegionPolymerCavityDarken=.040, R02_RegionPolymerCavityRoughness=.025)
    R['targets'].append({'material': path, 'mesh': current['mesh'], 'slot': slot,
        'preset': preset, 'regional': current['regional'], 'parent': current['parent'],
        'base': current['base'], 'sha256': current['sha256'], 'scalars': scalars,
        'vectors': vectors, 'textures': {'GrainTexture': name}})

(O / 'recipe.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
print('ASH12_R02_PRODUCED', len(R['targets']), 'instances; 1 physical-scale grain texture; separate region controls')
