"""PKM fine-finish data texture and per-slot production recipe."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

O = Path(__file__).parent
C = json.loads((O / 'Input/current.json').read_text())
ROOT = '/Game/Weapons/PKMLowpoly20260922/SurfaceStandard20261001'
VERSION = 'PKM-SurfaceStandard-Refine01-20261001'
T = O / 'Textures'
T.mkdir(exist_ok=True)
rng = np.random.default_rng(7621001)


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
name = 'T_PKM_R01_FineGrain'
file = T / (name + '.png')
Image.fromarray(np.round(np.stack((fine, small, np.zeros_like(fine), poly), -1) * 255).astype(np.uint8)).save(file)
R = {'version': VERSION, 'root': ROOT, 'texture': {'source': str(file.resolve()),
    'asset': ROOT + '/Textures/' + name, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
    'tile_cm': 4., 'channels': 'R fine roughness; G small finish variation; B no scratches; A polymer grain'},
    'targets': {}, 'bindings': {}, 'retained': {}, 'tested': False, 'geometry_changed': False}
ROLES = {
    'receiver': (.39, [.034, .035, .037]),
    'steel': (.34, [.041, .043, .046]),
    'stock_metal': (.41, [.030, .032, .034]),
    'muzzle': (.45, [.026, .028, .030]),
    'mount': (.44, [.024, .026, .028]),
    'bipod': (.43, [.029, .031, .033]),
    'optic': (.43, [.024, .026, .028]),
    'accessory': (.41, [.031, .033, .035]),
    'paint': (.44, [.047, .065, .025]),
    'polymer': (.55, [.019, .020, .021]),
    'grip': (.54, [.019, .020, .021]),
    'rubber': (.68, [.010, .011, .012]),
}


def role_for(mesh, slot, source, family):
    text = (mesh + ' ' + slot + ' ' + source).lower()
    if family in ('paint', 'rubber'):
        return family
    if family == 'polymer':
        return 'grip' if 'grip' in text or 'prism_polymer' in text else 'polymer'
    if 'interface' in slot.lower() or 'optic_rail' in mesh:
        return 'mount'
    if 'bipod' in text:
        return 'bipod'
    if any(k in text for k in ('muzzle', 'suppressor', 'brake')):
        return 'muzzle'
    if 'qbz_steel' in text:
        return 'steel'
    if 'factorystock' in text or any(k in mesh for k in ('stock', 'skeleton', 'telescopic', 'qr_performance')):
        return 'stock_metal'
    if any(k in text for k in ('holographic', 'scope', 'lpvo', 'red_dot', 'flashlight', 'laser')):
        return 'optic'
    if 'SK_PKM_Manny' in mesh:
        return 'receiver'
    return 'accessory'


for mesh, row in C['meshes'].items():
    bindings, kept = [], []
    # Runtime PKMAttachments::MeshPath resolves the OpticMount23 rail instead.
    if '/Accessories14/Meshes/SM_PKM_optic_rail.' in mesh:
        R['retained'][mesh] = row['slots']
        continue
    for slot in row['slots']:
        source = slot['material']
        m = C['materials'].get(source, {})
        family = m.get('category', '')
        if 'M_PKM23_Mount_' in (source or ''):
            family = 'metal'
        if family not in ('metal', 'paint', 'polymer', 'rubber') or any(k in slot['slot'].lower() for k in ('belt', 'manny')) or 'titaniumtrim' in (source or '').lower():
            kept.append(slot)
            continue
        wet = C['weather']['mapping'].get(source)
        if not wet:
            raise RuntimeError('Missing source weather material ' + source)
        role = role_for(mesh, slot['slot'], source, family)
        # Static and skeletal source uses retain the appropriate material usage.
        usage = 'skeletal' if row['skeletal'] else 'static'
        key = source + '|' + role + '|' + usage
        if key not in R['targets']:
            rough, color = ROLES[role]
            scalars = {'R01_Roughness': rough, 'R01_GrainRoughness': .012,
                'R01_VariationRoughness': .005, 'R01_SourceRoughnessWeight': .12,
                'R01_ColorWeight': .90, 'R01_PolymerStipple': 0.,
                'PKM_MicroScratchStrength': 0., 'WeaponWetness': 0.}
            if family in ('polymer', 'rubber'):
                scalars.update(R01_GrainRoughness=.018 if family == 'rubber' else .020,
                    R01_VariationRoughness=.006, R01_SourceRoughnessWeight=.18,
                    R01_ColorWeight=.20, R01_PolymerStipple=.020)
            elif family == 'paint':
                scalars.update(R01_GrainRoughness=.009, R01_VariationRoughness=.004,
                    R01_SourceRoughnessWeight=.10, R01_ColorWeight=1.)
            elif role == 'steel':
                scalars.update(R01_GrainRoughness=.009, R01_VariationRoughness=.004)
            suffix = hashlib.sha1(key.encode()).hexdigest()[:10]
            R['targets'][key] = {'source': source, 'wet_source': wet,
                'base': C['materials'][wet]['base'], 'role': role, 'family': family, 'usage': usage,
                'scalars': scalars, 'vectors': {'R01_FinishTint': color},
                'asset': ROOT + '/Materials/MI_PKM_R01_' + role + '_' + suffix}
        bindings.append(dict(slot=slot['slot'], index=slot['index'], before=source, key=key))
    if bindings:
        R['bindings'][mesh] = bindings
    if kept:
        R['retained'][mesh] = kept
(O / 'recipe.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
print('PKM_R01_PRODUCED', len(R['targets']), 'instances', len(R['bindings']), 'meshes',
    len({(t['base'], t['usage']) for t in R['targets'].values()}), 'adapters')
