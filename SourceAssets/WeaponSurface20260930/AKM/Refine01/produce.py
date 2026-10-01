"""AKM authored-detail-preserving finish recipe and technical grain texture."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

O = Path(__file__).parent
C = json.loads((O / 'Input/current.json').read_text())
ROOT = '/Game/Weapons/AKMIntegration/SurfaceStandard20261001'
VERSION = 'AKM-AuthoredFinish-Refine01-20261001'
T = O / 'Textures'
T.mkdir(exist_ok=True)
rng = np.random.default_rng(471001)


def band(n, lo, hi):
    f = np.fft.fftfreq(n) * n
    r = np.maximum(np.hypot(f[:, None], f[None, :]), 1e-6)
    w = np.exp(-.5 * ((np.log(r) - np.log(np.sqrt(lo * hi))) / (np.log(hi / lo) / 2.5)) ** 2)
    w[0, 0] = 0
    v = np.fft.ifft2(np.fft.fft2(rng.standard_normal((n, n))) * w).real
    return (v - v.mean()) / max(v.std(), 1e-9)


fine = np.clip(.5 + band(1024, 80, 240) * .13, 0, 1)
small = np.clip(.5 + band(1024, 18, 55) * .11, 0, 1)
file = T / 'T_AKM_R01_FineGrain.png'
Image.fromarray(np.round(np.stack((fine, small, np.zeros_like(fine), np.ones_like(fine)), -1) * 255).astype(np.uint8)).save(file)
R = {'version': VERSION, 'root': ROOT, 'texture': {'source': str(file.resolve()),
    'asset': ROOT + '/Textures/' + file.stem, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
    'tile_cm': 4., 'channels': 'R fine roughness; G restrained variation; B zero added wear; A unused'},
    'targets': {}, 'bindings': {}, 'retained': {}, 'tested': False, 'geometry_changed': False}


def role_for(mesh, slot):
    text = (mesh + ' ' + slot).lower()
    if 'magazine' in text or 'extmag' in text or 'drum' in text:
        return 'magazine'
    if 'SK_AKM_MannyNative' in mesh:
        return 'furniture_metal' if 'Factory' in slot else 'receiver'
    if any(k in text for k in ('adapter', 'collar', 'mount', 'saddle')):
        return 'mount'
    if any(k in text for k in ('muzzle', 'suppressor', 'brake')):
        return 'muzzle'
    if any(k in text for k in ('optic', 'scope', 'pso1', 'lpvo', 'red_dot', 'tacticaldevice')):
        return 'optic'
    if 'stock' in text or 'reargrip' in text:
        return 'furniture_metal'
    return 'accessory'


for mesh, row in C['meshes'].items():
    bindings, kept = [], []
    for s in row['slots']:
        source = s['material']
        override = C['overrides'].get(mesh)
        direct = bool(override and override['slot'] == s['slot'])
        if direct:
            source = override['material']
        m = C['materials'].get(source)
        text = (s['slot'] + ' ' + (source or '')).lower()
        # The drum uses one regional PBR atlas for the shell and fasteners.
        drum = '/LargeDrumUpgrade20260920/AKM/' in (source or '')
        protected = any(k in text for k in ('rubber', 'recess', 'glass', 'reticle', 'red_dot', 'titaniumtrim', 'manny'))
        protected |= 'polymer' in text and not drum
        protected |= bool(source and '/Selected91727/M_StableAntiSlipRearGrip.' in source)
        if not m or protected or not any(k in m['blend'] for k in ('BLEND_OPAQUE', 'BLEND_MASKED')):
            kept.append(s)
            continue
        role = role_for(mesh, s['slot'])
        usage = 'skeletal' if row['skeletal'] else 'static'
        key = source + '|' + role + '|' + usage
        if key not in R['targets']:
            wet = C['weather']['mapping'].get(source)
            base = C['materials'][wet]['base'] if wet else m['base']
            region = 'one'
            if any(k in source for k in ('/OpticSteel/', '/CoreStock', '/RearGripFinish', '/TacticalDevices', '/AttachmentFinish')):
                graph = C['graphs'][m['base']]
                colour = next(n for n in graph['nodes'] if n['name'] == graph['outputs']['BASE_COLOR'][0])
                if colour['class'] == 'MaterialExpressionLinearInterpolate':
                    region = 'colour_lerp_alpha'
            if 'M_PSO1_AKM_Shell' in source:
                region = 'vertex_red'
            rough = {'receiver': .40, 'magazine': .38, 'mount': .43, 'muzzle': .45,
                'optic': .43, 'furniture_metal': .41, 'accessory': .42}[role]
            scalars = {'R01_Roughness': rough, 'R01_SourcePivot': .34,
                'R01_SourceRoughnessWeight': .75, 'R01_Grain': .009 if role == 'magazine' else .012,
                'R01_Variation': .004 if role == 'magazine' else .005,
                'R01_Strength': 1., 'WeaponWetness': 0.}
            # Current source's dark steel median .058 -> approximately .035.
            # Preserve the original colour sample and bright authored wear.
            vectors = {'R01_ToneScale': [.60, .60, .60]}
            suffix = hashlib.sha1(key.encode()).hexdigest()[:10]
            R['targets'][key] = {'source': source, 'wet_source': wet, 'base': base,
                'role': role, 'usage': usage, 'region': region, 'direct_override': direct,
                'scalars': scalars, 'vectors': vectors,
                'asset': source.split('.')[0] if direct else ROOT + '/Materials/MI_AKM_R01_' + role + '_' + suffix}
        bindings.append({'slot': s['slot'], 'index': s['index'], 'before': s['material'], 'key': key})
    if bindings:
        R['bindings'][mesh] = bindings
    if kept:
        R['retained'][mesh] = kept
(O / 'recipe.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
print('AKM_R01_PRODUCED', len(R['targets']), 'targets', len(R['bindings']), 'meshes',
    sum(t['direct_override'] for t in R['targets'].values()), 'runtime override materials')
