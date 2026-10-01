"""Author periodic PBR data maps and the A762-only finish recipe (CPython)."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

O = Path(__file__).parent
T = O / 'Textures'
T.mkdir(exist_ok=True)
capture = json.loads((O / 'Input/current.json').read_text())
rng = np.random.default_rng(7621001)
VERSION = 'A762-Refine06-20261001'
ROOT = '/Game/Weapons/A762/SurfaceStandard08/Refine06/Textures/'
recipe = {'version': VERSION, 'textures': {}, 'targets': [], 'retained': [], 'tested': False}

def band(n, low, high):
    f = np.fft.fftfreq(n) * n
    radius = np.maximum(np.hypot(f[:, None], f[None, :]), 1e-6)
    window = np.exp(-0.5 * ((np.log(radius) - np.log(np.sqrt(low * high))) / (np.log(high / low) / 2.5)) ** 2)
    window[0, 0] = 0
    field = np.fft.ifft2(np.fft.fft2(rng.standard_normal((n, n))) * window).real
    return (field - field.mean()) / max(field.std(), 1e-9)

def write(name, pixels, kind, info):
    file = T / (name + '.png')
    Image.fromarray(np.round(np.clip(pixels, 0, 1) * 255).astype(np.uint8)).save(file)
    recipe['textures'][name] = {'source': str(file.resolve()), 'asset': ROOT + name,
        'sha256': hashlib.sha256(file.read_bytes()).hexdigest(), 'kind': kind, **info}

# Four-centimetre triplanar tile; grain occupies ~0.17-0.5 mm. The G channel
# contains only small finish variation, not the former 5-15 mm cloudy patches.
n = 1024
fine = np.clip(.5 + band(n, 80, 240) * .13, 0, 1)
small = np.clip(.5 + band(n, 18, 55) * .11, 0, 1)
stipple = np.clip(.375 + band(n, 65, 150) * .075, 0, 1)
write('T_A762_R06_Grain', np.stack((fine, small, np.zeros_like(fine), stipple), -1),
      'grain', {'tile_cm': 4., 'channels': 'R fine roughness; G fine variation; B no scratches; A shallow polymer grain'})

# Technical normal data, not painted colour. The weak, isotropic slopes add a
# finish only where the previous normal input was flat and the rebuilt UV0
# density is ~0.35 units/cm. Structural/atlas normals are never replaced.
for family, cycles, slope in [('Metal', (150, 220), .012),
                              ('Polymer', (70, 120), .040),
                              ('Rubber', (40, 85), .028)]:
    n = 512
    h = band(n, *cycles)
    du = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * .5
    dv = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * .5
    scale = slope / np.sqrt(np.mean(du * du + dv * dv))
    # DirectX/Y-down normal convention, imported with flip_green_channel=False.
    vec = np.stack((-du * scale, dv * scale, np.ones_like(h)), -1)
    vec /= np.linalg.norm(vec, axis=-1, keepdims=True)
    write('T_A762_R06_' + family + '_N', vec * .5 + .5, 'normal',
          {'convention': 'DirectX', 'flip_green_channel': False, 'rms_slope': slope,
           'nominal_uv_units_per_cm': .35, 'feature_mm': [round(10 / (.35 * cycles[1]), 3), round(10 / (.35 * cycles[0]), 3)]})

metal = {'GrainTileCm': 4., 'GrainRoughness': .012, 'MottleRoughness': .005,
         'MottleColor': 0., 'Stipple': 0., 'EdgeWear': .025, 'EdgeHighlight': .045,
         'CavityDarken': .025, 'CavityRoughness': .018, 'ScratchAmount': 0., 'HandlingPolish': 0.}
polymer = {'GrainTileCm': 4., 'GrainRoughness': .020, 'MottleRoughness': .008,
           'MottleColor': 0., 'Stipple': .028, 'EdgeWear': 0., 'EdgeHighlight': .020,
           'CavityDarken': .035, 'CavityRoughness': .025, 'ScratchAmount': 0., 'HandlingPolish': 0.}
rubber = dict(polymer, GrainRoughness=.018, MottleRoughness=.006, Stipple=.025,
              Roughness=.68, EdgeHighlight=.010, CavityDarken=.055)

# Explicit roles, not random per-slot colours. Values remain the project's
# dark treated-metal approximation; they are not measured bare-metal values.
roles = {
 'M_A762_Receiver': (.39, [.034, .035, .037]),
 'M_A762_UpperReceiver03': (.36, [.030, .032, .035]),
 'M_A762_Bolt': (.32, [.040, .042, .044]),
 'M_A762_Trigger': (.36, [.034, .035, .037]),
 'M_A762_FrontAssembly_Rebuilt': (.44, [.027, .029, .031]),
 'M_A762_Flash_Hider': (.47, [.026, .028, .030]),
 'M_A762_Rail': (.45, [.020, .021, .022]),
 'M_A762_RearSight03': (.40, [.031, .032, .034]),
 'M_A762_FrontSight_Rebuilt': (.40, [.031, .032, .034]),
 'M_A762_FactoryStock_Metal04': (.42, [.032, .033, .035]),
 'M_A762_FactoryStock_Socket03': (.42, [.032, .033, .035]),
 'M_A762_Magazine_Rebuilt': (.46, [.029, .031, .033]),
 'M_A762_MagazineEdge_Rebuilt': (.41, [.033, .035, .037]),
 'M_A762_Handguard03': (.53, [.019, .019, .018]),
 'M_A762_FactoryRearGrip': (.55, [.020, .020, .019]),
 'M_A762_FactoryStock_Seam04': (.58, [.012, .012, .012]),
}
micro_slots = {'M_A762_UpperReceiver03': 'Metal', 'M_A762_Flash_Hider': 'Metal',
    'M_A762_FactoryStock_Socket03': 'Metal', 'M_A762_FactoryStock_Metal04': 'Metal',
    'M_A762_Magazine_Rebuilt': 'Metal', 'M_A762_MagazineEdge_Rebuilt': 'Metal',
    'M_A762_Handguard03': 'Polymer', 'M_A762_FactoryStock_Seam04': 'Polymer',
    'M_A762_FactoryStock_Rubber04': 'Rubber'}
seen = set()
for key, mesh in capture['meshes'].items():
    for slot in mesh['slots']:
        path = slot['material']
        if path not in capture['materials'] or path in seen:
            continue
        seen.add(path)
        current = capture['materials'][path]
        preset = current['parent'].split('.')[-1].removeprefix('MI_WS_')
        if preset == 'Interior':
            recipe['retained'].append({'material': path, 'reason': 'interior'})
            continue
        s = dict(metal if preset in ('CleanSatinSteel', 'CleanAnodized') else polymer if preset == 'CleanPolymer' else rubber)
        if preset not in ('CleanSatinSteel', 'CleanAnodized', 'CleanPolymer', 'Rubber'):
            raise RuntimeError('Unplanned material family ' + preset)
        v, textures = {}, {'GrainTexture': 'T_A762_R06_Grain'}
        name = slot['slot']
        if name in roles:
            s['Roughness'], v['FinishColor'] = roles[name]
        elif preset == 'CleanAnodized':
            s['Roughness'] = .45
        elif preset == 'CleanPolymer':
            s['Roughness'] = .55
        elif preset == 'CleanSatinSteel':
            s['Roughness'] = .42
        if preset == 'CleanSatinSteel' and ('suppressor' in key or 'brake' in key):
            s['Roughness'] = .47 if 'suppressor' in key else .43
        if key == 'SM_A762_drum' and name in ('A762_drum_0', 'A762_drum_2', 'A762_drum_Neck'):
            s['Roughness'], v['FinishColor'] = roles['M_A762_Magazine_Rebuilt']
        # A curved magazine's bake includes surface curvature: retain disabled
        # edge sheen/wear on its broad panels, avoiding bright contour stripes.
        if name == 'M_A762_Magazine_Rebuilt' or (key == 'SM_A762_drum' and name in ('A762_drum_0', 'A762_drum_2', 'A762_drum_Neck')):
            s.update(EdgeHighlight=0., EdgeWear=0., GrainRoughness=.009, MottleRoughness=.004)
        elif name == 'M_A762_MagazineEdge_Rebuilt':
            s.update(EdgeHighlight=.025, EdgeWear=.015)
        if name in micro_slots and (key == 'A762' or key == 'SM_A762_ext_mag'):
            old_normal = current['parameters']['texture']['SurfaceNormal']
            if old_normal != '/Engine/EngineMaterials/DefaultNormal.DefaultNormal':
                raise RuntimeError('Preserve non-flat normal ' + path)
            textures['SurfaceNormal'] = 'T_A762_R06_' + micro_slots[name] + '_N'
        recipe['targets'].append({'material': path, 'mesh': key, 'slot': name,
            'parent': current['parent'], 'base': current['base'], 'sha256': current['sha256'],
            'family': preset, 'scalars': s, 'vectors': v, 'textures': textures})
(O / 'recipe.json').write_text(json.dumps(recipe, indent=2), encoding='utf-8')
print('A762_R06_PRODUCED', len(recipe['textures']), 'maps', len(recipe['targets']), 'finish instances; no UE asset writes')
