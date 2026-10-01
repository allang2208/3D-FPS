"""201 finish continuation: periodic technical texture and explicit part roles."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

O = Path(__file__).parent
C = json.loads((O / 'Input/current.json').read_text())
ROOT = '/Game/Weapons/LMG201/SurfaceStandard20261001'
VERSION = 'LMG201-SurfaceStandard-Refine01-20261001'
T = O / 'Textures'
T.mkdir(exist_ok=True)
rng = np.random.default_rng(2011001)


def band(n, low, high):
    f = np.fft.fftfreq(n) * n
    r = np.maximum(np.hypot(f[:, None], f[None, :]), 1e-6)
    w = np.exp(-.5 * ((np.log(r) - np.log(np.sqrt(low * high))) / (np.log(high / low) / 2.5)) ** 2)
    w[0, 0] = 0
    v = np.fft.ifft2(np.fft.fft2(rng.standard_normal((n, n))) * w).real
    return (v - v.mean()) / max(v.std(), 1e-9)


n = 1024
fine = np.clip(.5 + band(n, 80, 240) * .13, 0, 1)
small = np.clip(.5 + band(n, 18, 55) * .11, 0, 1)
poly = np.clip(.375 + band(n, 65, 150) * .075, 0, 1)
name = 'T_LMG201_R01_FineGrain'
file = T / (name + '.png')
Image.fromarray(np.round(np.stack((fine, small, np.zeros_like(fine), poly), -1) * 255).astype(np.uint8)).save(file)
R = {'version': VERSION, 'texture': {'source': str(file.resolve()), 'asset': ROOT + '/Textures/' + name,
    'sha256': hashlib.sha256(file.read_bytes()).hexdigest(), 'tile_cm': 4.,
    'channels': 'R fine metal roughness; G small finish variation; B no scratches; A polymer grain'},
    'targets': {}, 'bindings': {}, 'retained': {}, 'tested': False, 'geometry_changed': False}
ROLES = {
    'receiver': (.39, [.034, .035, .037], 1),
    'cover': (.36, [.030, .032, .035], 1),
    'front': (.44, [.027, .029, .031], 1),
    'muzzle': (.47, [.026, .028, .030], 1),
    'mount': (.45, [.020, .021, .022], 1),
    'optic': (.43, [.024, .026, .028], 1),
    'bipod': (.43, [.029, .031, .033], 1),
    'steel': (.33, [.044, .046, .048], 1),
    'fastener': (.36, [.038, .040, .042], 1),
    'stock_mount': (.40, [.032, .034, .036], 1),
    'magazine': (.42, [.030, .032, .034], 1),
    'polymer': (.55, [.020, .021, .022], 0),
    'grip': (.54, [.019, .020, .021], 0),
    'rubber': (.68, [.009, .011, .013], 0),
}


def role_for(mesh, slot, family):
    if family in ('polymer', 'grip', 'rubber', 'stock_mount'):
        return family
    text = (mesh.split('.')[-1] + ' ' + slot).lower()
    if family == 'satin':
        return 'fastener' if 'fastener' in text or 'hardware' in text else 'steel'
    if any(s in text for s in ('shoe', 'mount', 'adapter', 'interface', 'bridge')):
        return 'mount'
    if 'bipod' in text:
        return 'bipod'
    if any(s in text for s in ('suppressor', 'muzzle', 'brake', 'flash_hider')):
        return 'muzzle'
    if any(s in slot.lower() for s in ('lid', 'cover')):
        return 'cover'
    if 'magazine' in text:
        return 'magazine'
    if 'handguard' in text or 'front' in text:
        return 'front'
    if any(s in text for s in ('sight', 'scope', 'pso', 'lpvo', 'red_dot', 'holographic')):
        return 'optic'
    return 'receiver'


for mesh, row in C['meshes'].items():
    bindings = []
    kept = []
    for slot in row['slots']:
        source = slot['material']
        m = C['materials'].get(source, {})
        family = m.get('role')
        drum = '/Drum46/Materials/' in (source or '') or '/DrumJoint47/Materials/' in (source or '')
        if drum:
            family = 'polymer' if m['parameters']['scalar'].get('201Metallic', 1.) == 0 else 'satin' if 'Hardware' in source else 'coat'
        if not family or 'titanium_brake' in mesh or any(k in slot['slot'] for k in ('Manny', 'Cloth', 'Feed__', 'Inside', 'Interior', 'Lens', 'Glass')):
            kept.append(slot)
            continue
        role = role_for(mesh, slot['slot'], family)
        key = source + '|' + role
        if key not in R['targets']:
            rough, color, metallic = ROLES[role]
            scalars = {'R01_GrainRoughness': .012, 'R01_MottleRoughness': .005,
                'R01_PolymerStipple': 0., 'R01_EdgeHighlight': .035}
            if metallic == 0:
                scalars.update(R01_GrainRoughness=.018 if role == 'rubber' else .020,
                    R01_MottleRoughness=.006, R01_PolymerStipple=.025,
                    R01_EdgeHighlight=.010 if role == 'rubber' else .020)
            elif role in ('steel', 'fastener'):
                scalars.update(R01_GrainRoughness=.009, R01_MottleRoughness=.004, R01_EdgeHighlight=.025)
            elif role == 'magazine':
                scalars.update(R01_GrainRoughness=.009, R01_MottleRoughness=.004, R01_EdgeHighlight=.015)
            if drum:
                prefix = '201'
                scalars['201FinishRoughness'] = rough
                scalars['201Metallic'] = metallic
                vectors = {'201FinishTint': color}
                adapter = 'drum'
            else:
                prefix = 'F50' if 'F50_Roughness' in m['parameters']['scalar'] else 'G43'
                scalars[prefix + '_Roughness'] = rough
                scalars[prefix + '_Metallic'] = metallic
                vectors = {prefix + '_FinishTint': color}
                adapter = prefix
            suffix = hashlib.sha1(key.encode()).hexdigest()[:10]
            R['targets'][key] = {'source': source, 'base': m['base'], 'role': role,
                'family': family, 'adapter': adapter, 'scalars': scalars, 'vectors': vectors,
                'asset': ROOT + '/Materials/MI_LMG201_R01_' + role + '_' + suffix}
        bindings.append({'slot': slot['slot'], 'before': source, 'key': key})
    if bindings:
        R['bindings'][mesh] = bindings
    if kept:
        R['retained'][mesh] = kept

(O / 'recipe.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
print('201_R01_PRODUCED', len(R['targets']), 'instances', len(R['bindings']), 'bound meshes',
    len({t['base'] for t in R['targets'].values()}), 'source adapters')
