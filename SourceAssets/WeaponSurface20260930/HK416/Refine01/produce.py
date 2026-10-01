"""HK416 finish recipe: authored markings, satin metals and coordinated polymer."""
import hashlib
import json
from pathlib import Path

O = Path(__file__).parent
C = json.loads((O / 'Input/current.json').read_text())
ROOT = '/Game/Weapons/HK416/SurfaceStandard20261001'
VERSION = 'HK416-AuthoredFinish-Refine01-20261001'
file = O / 'Textures/T_HK416_R01_FineGrain.png'
R = {'version': VERSION, 'root': ROOT, 'texture': {'source': str(file.resolve()),
    'asset': ROOT + '/Textures/' + file.stem, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
    'tile_cm': 4., 'channels': 'R fine roughness; G restrained variation; B no added wear; A unused'},
    'targets': {}, 'bindings': {}, 'retained': {}, 'geometry_changed': False, 'tested': False}


def role_for(mesh, slot):
    text = (mesh + ' ' + slot).lower()
    if 'magazine' in text or 'ext_mag' in text or 'large_drum' in text:
        return 'magazine'
    if any(k in slot.lower() for k in ('interface', 'adapter', 'collar', 'mount', 'saddle')):
        return 'mount'
    if any(k in text for k in ('stock', 'reargrip', 'factory_grip')):
        return 'furniture'
    if any(k in text for k in ('muzzle', 'barrel', 'suppressor', 'brake')):
        return 'muzzle'
    if any(k in text for k in ('holographic', 'lpvo', 'scope', 'panoramic', 'flashlight', 'laser')):
        return 'optic'
    if 'upper_body' in text or 'factory_sights' in text:
        return 'upper_receiver'
    if 'lower_body' in text or 'factory_trigger' in text:
        return 'lower_receiver'
    return 'accessory'


for mesh, row in C['meshes'].items():
    bindings, kept = [], []
    for s in row['slots']:
        source = s['material']
        m = C['materials'].get(source)
        text = (s['slot'] + ' ' + (source or '')).lower()
        protected = any(k in text for k in ('rubber', 'recess', 'glass', 'reticle', 'lens', 'manny', 'skin', 'drumindex', 'titanium'))
        if not m or protected or not any(k in m['blend'] for k in ('BLEND_OPAQUE', 'BLEND_MASKED')):
            kept.append(s)
            continue
        role = role_for(mesh, s['slot'])
        usage = 'skeletal' if row['skeletal'] else 'static'
        key = source + '|' + role + '|' + usage
        if key not in R['targets']:
            wet = C['weather']['mapping'].get(source)
            base = C['materials'][wet]['base'] if wet else m['base']
            # Native source graphs already carry their single wet contract.
            graph = C['graphs'][base]
            wet_outputs = []
            for channel in ('BASE_COLOR', 'ROUGHNESS', 'NORMAL'):
                name = graph['outputs'][channel][0]
                n = next((n for n in graph['nodes'] if n['name'] == name), {})
                wet_outputs.append(set(n.get('custom_inputs', [])) == {'Base', 'Data'} and 'Data.a' in n.get('code', ''))
            if any(wet_outputs) and not all(wet_outputs):
                raise RuntimeError('Incomplete source wet surface ' + source)
            if all(wet_outputs) and not wet:
                wet = source
            native = '/Reworked20260930/Materials/' in source
            rough = {'upper_receiver': .34, 'lower_receiver': .36, 'magazine': .30,
                'mount': .42, 'muzzle': .44, 'optic': .37, 'furniture': .39, 'accessory': .38}[role]
            polymer = .43 if role == 'magazine' else .49 if role in ('furniture', 'accessory') else .47
            scalars = {'R01_Roughness': rough, 'R01_SourcePivot': .34,
                'R01_SourceRoughnessWeight': .28, 'R01_Grain': .009 if role == 'magazine' else .010,
                'R01_Variation': .004, 'R01_Strength': 1., 'WeaponWetness': 0.,
                'R02_SourceColorContrast': .58,
                'R01_PolymerStrength': .55 if native else 1., 'R01_PolymerRoughness': polymer,
                'R01_PolymerPivot': .50 if native else .60, 'R01_PolymerSourceWeight': .35 if native else .22}
            vectors = {'R01_ToneScale': [.52, .55, .59], 'R01_PolymerTint': [.022, .023, .025]}
            suffix = hashlib.sha1(key.encode()).hexdigest()[:10]
            R['targets'][key] = {'source': source, 'wet_source': wet, 'base': base, 'role': role,
                'usage': usage, 'region': 'one', 'direct_override': False, 'scalars': scalars, 'vectors': vectors,
                'asset': ROOT + '/Materials/MI_HK416_R01_' + role + '_' + suffix}
        bindings.append({'slot': s['slot'], 'index': s['index'], 'before': s['material'], 'key': key})
    if bindings:
        R['bindings'][mesh] = bindings
    if kept:
        R['retained'][mesh] = kept
(O / 'recipe.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
print('HK416_R01_PRODUCED', len(R['targets']), 'instances', len(R['bindings']), 'meshes')
