"""Produce an authored-PBR M4 recipe without changing geometry or source maps."""
import hashlib
import json
from pathlib import Path

O = Path(__file__).parent
P = O.parents[3]
C = json.loads((O / 'Input/current.json').read_text())
ROOT = '/Game/Weapons/M4/SurfaceStandard20261001'
VERSION = 'M4-AuthoredFinish-Refine01-20261001'
grain = O / 'Textures/T_M4_R01_FineGrain.png'
R = {'version': VERSION, 'root': ROOT, 'texture': {'source': str(grain.resolve()),
    'asset': ROOT + '/Textures/' + grain.stem, 'sha256': hashlib.sha256(grain.read_bytes()).hexdigest(),
    'tile_cm': 4.}, 'targets': {}, 'bindings': {}, 'retained': {},
    'pbr_textures': {}, 'geometry_changed': False, 'tested': False}

for name in ('Body', 'Keymod material', 'Magazine Light', 'Flash Hider', 'Grip Default', 'Classic Stock'):
    for kind in ('Metallic', 'Roughness'):
        file = P / 'Content/m4noskel.fbm' / (name + '_' + kind + '.png')
        key = name.replace(' ', '_') + '_' + kind
        R['pbr_textures'][key] = {'file': str(file.resolve()),
            'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
            'asset': ROOT + '/Textures/T_M4_R01_' + key}
R['linear_coat'] = {'source': '/Game/Weapons/AttachmentFinish20260913/M4/Textures/T_M4_Receiver_Roughness',
    'asset': ROOT + '/Textures/T_M4_R01_Receiver_Roughness'}


def role_for(mesh, slot):
    text = (mesh + ' ' + slot).lower()
    if 'magazine' in text or 'extmag' in text or 'largedrum' in text:
        return 'magazine'
    if any(k in slot.lower() for k in ('interface', 'adapter', 'collar', 'mount', 'saddle')):
        return 'mount'
    if any(k in text for k in ('stock', 'reargrip', 'grip_default')):
        return 'furniture'
    if any(k in text for k in ('muzzle', 'flash_hider', 'suppressor', 'brake')):
        return 'muzzle'
    if any(k in text for k in ('holographic', 'lpvo', 'scope', 'panoramic', 'flashlight', 'laser')):
        return 'optic'
    if 'keymod' in slot.lower():
        return 'handguard'
    if 'M4HK416Replica' in mesh:
        return 'receiver'
    return 'accessory'


for mesh, row in C['meshes'].items():
    bindings, kept = [], []
    override = C['overrides'].get(mesh)
    for slot in row['slots']:
        direct = bool(override and slot['slot'] == override['slot'])
        source = override['material'] if direct else slot['material']
        material = C['materials'].get(source)
        text = (slot['slot'] + ' ' + (source or '')).lower()
        if (not material or any(k in text for k in ('rubber', 'recess', 'glass', 'reticle', 'lens', 'manny', 'skin', 'titaniumtrim'))
                or not any(k in material['blend'] for k in ('BLEND_OPAQUE', 'BLEND_MASKED'))):
            kept.append(slot)
            continue
        role = role_for(mesh, slot['slot'])
        usage = 'skeletal' if row['skeletal'] else 'static'
        key = source + '|' + role + '|' + usage
        if key not in R['targets']:
            wet = None if direct else C['weather']['mapping'].get(source)
            base = C['materials'][wet]['base'] if wet else material['base']
            graph = C['graphs'][base]
            nodes = {n['name']: n for n in graph['nodes']}
            wet_outputs = [set(nodes.get(graph['outputs'][channel][0], {}).get('custom_inputs', [])) == {'Base', 'Data'}
                           for channel in ('BASE_COLOR', 'ROUGHNESS', 'NORMAL')]
            if any(wet_outputs) and not all(wet_outputs):
                raise RuntimeError('Incomplete wet source ' + source)
            if all(wet_outputs) and not wet:
                wet = source
            # Native Phong instances retain their original colour/UV/normal but
            # restore the author's linear roughness and metallic textures.
            native_map = material['parameters']['texture'].get('DiffuseColorMap', '')
            native = '/M4InfimaV3/' in native_map
            texture_params = {}
            if native:
                name = native_map.rsplit('/', 1)[-1].split('.')[0].removesuffix('_BaseColor')
                texture_params = {'ShininessMap': R['pbr_textures'][name + '_Roughness']['asset'],
                                  'R01_AuthorMetallic': R['pbr_textures'][name + '_Metallic']['asset']}
            rough = {'receiver': .34, 'handguard': .36, 'magazine': .31, 'mount': .40,
                     'muzzle': .43, 'optic': .37, 'furniture': .39, 'accessory': .38}[role]
            nonmetal = .43 if role == 'magazine' else .38 if role == 'receiver' else .40 if role == 'handguard' else .49 if role in ('furniture', 'accessory') else .46
            scalars = {'R01_Roughness': rough, 'R01_SourcePivot': .50,
                'R01_SourceRoughnessWeight': .28, 'R01_Grain': .009 if role == 'magazine' else .010,
                'R01_Variation': .004, 'R01_Strength': 1., 'WeaponWetness': 0.,
                'R02_SourceColorContrast': .58, 'R01_PolymerStrength': .75 if native else 1.,
                'R01_PolymerRoughness': nonmetal, 'R01_PolymerPivot': .50,
                'R01_PolymerSourceWeight': .35 if native else .22}
            vectors = {'R01_ToneScale': [.54, .56, .59], 'R01_PolymerTint': [.026, .027, .029]}
            suffix = hashlib.sha1(key.encode()).hexdigest()[:10]
            R['targets'][key] = {'source': source, 'wet_source': wet, 'base': base, 'role': role,
                'usage': usage, 'region': 'one', 'direct_override': direct, 'native_pbr': native,
                'scalars': scalars, 'vectors': vectors, 'textures': texture_params,
                'asset': source.split('.')[0] if direct else ROOT + '/Materials/MI_M4_R01_' + role + '_' + suffix}
        bindings.append({'slot': slot['slot'], 'index': slot['index'], 'before': slot['material'], 'key': key})
    if bindings:
        R['bindings'][mesh] = bindings
    if kept:
        R['retained'][mesh] = kept
(O / 'recipe.json').write_text(json.dumps(R, indent=2), encoding='utf-8')
print('M4_R01_PRODUCED', sum(not t['direct_override'] for t in R['targets'].values()), 'instances',
      sum(t['direct_override'] for t in R['targets'].values()), 'runtime overrides', len(R['bindings']), 'meshes')
