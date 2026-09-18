"""Check every texture sample in the ground materials against the sampler type it needs.

The material compiler fails a material when a TextureSample's sampler type does not
match what the texture's compression settings imply, and the only symptom in game is
"Default Material will be used" - the ground renders as the grey default checkerboard.
That check is graph level, so the offline HLSL compile cannot see it; this script walks
every sample node instead and reports the mismatch before anyone launches the game.
"""
import json
from pathlib import Path
import unreal as u

LIB = u.MaterialEditingLibrary
OUT = Path('D:/FPS3D/FPSGAME/Saved/GroundMaterialUpgrade20260918')
MATERIALS = ['/Game/WorldGeneration/TemperateHills/M_TemperateGround',
             '/Game/WorldGeneration/TemperateHills/PebbleShore/M_PebbleShoreGround']

# UTexture::GetMaterialType(): the sampler type a texture demands, by compression.
# Keys are upper case because the Python enum name is.
BY_COMPRESSION = {
    'TC_ALPHA': 'SAMPLERTYPE_Alpha',
    'TC_GRAYSCALE': 'SAMPLERTYPE_Grayscale',
    'TC_NORMALMAP': 'SAMPLERTYPE_Normal',
    'TC_MASKS': 'SAMPLERTYPE_Masks',
    'TC_DISPLACEMENTMAP': 'SAMPLERTYPE_Displacement',
    'TC_DISTANCEFIELDFONT': 'SAMPLERTYPE_DistanceFieldFont',
    'TC_HDR': 'SAMPLERTYPE_LinearColor',
    'TC_HDR_COMPRESSED': 'SAMPLERTYPE_LinearColor',
}


def canonical(name):
    """UE's display names ('Linear Color') and member names ('SAMPLERTYPE_LINEAR_COLOR')
    differ only in case and underscores, so compare on letters and digits alone."""
    return ''.join(ch for ch in str(name).upper() if ch.isalnum())


def enum_name(value):
    return str(value).split('.')[-1].split(':')[0].strip()


def required_sampler(texture):
    key = enum_name(texture.get_editor_property('compression_settings')).upper()
    mapped = BY_COMPRESSION.get(key)
    if mapped:
        return mapped
    return 'SAMPLERTYPE_Color' if texture.get_editor_property('srgb') else 'SAMPLERTYPE_LinearColor'


def texture_of(expr):
    if expr.__class__.__name__ == 'MaterialExpressionTextureObject':
        return expr.get_editor_property('texture')
    return expr.get_editor_property('texture')


report = {'materials': {}, 'textures': {}}
bad = []
for path in MATERIALS:
    mat = u.load_asset(path)
    if mat is None:
        report['materials'][path] = 'MISSING'
        continue
    rows = []
    for expr in LIB.get_material_expressions(mat) or []:
        kind = expr.__class__.__name__
        if kind not in ('MaterialExpressionTextureSample', 'MaterialExpressionTextureObject'):
            continue
        texture = texture_of(expr)
        if texture is None:
            rows.append({'node': kind, 'texture': None, 'problem': 'NO TEXTURE ASSIGNED'})
            bad.append((path, kind, None, 'NO TEXTURE ASSIGNED', None))
            continue
        want = required_sampler(texture)
        have = enum_name(expr.get_editor_property('sampler_type'))
        compression = enum_name(texture.get_editor_property('compression_settings'))
        srgb = bool(texture.get_editor_property('srgb'))
        row = {'node': kind, 'texture': texture.get_path_name().split('.')[0], 'compression': compression,
               'srgb': srgb, 'want': want, 'have': have, 'ok': canonical(want) == canonical(have)}
        rows.append(row)
        report['textures'][texture.get_path_name().split('.')[0]] = {'compression': compression, 'srgb': srgb}
        if row['ok'] is False:
            bad.append((path, kind, texture.get_path_name().split('.')[0], want, have))
    report['materials'][path] = {'samples': len(rows), 'mismatches': [r for r in rows if not r.get('ok')]}

report['verdict'] = 'OK' if not bad else 'MISMATCH'
report['bad'] = [{'material': b[0].split('/')[-1], 'node': b[1], 'texture': b[2], 'want': b[3], 'have': b[4]}
                 for b in bad]
(OUT / 'sampler_check.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
u.log('SAMPLER_CHECK verdict=%s mismatches=%d' % (report['verdict'], len(bad)))
for b in report['bad']:
    u.log('SAMPLER_CHECK BAD %s %s %s want=%s have=%s' % (b['material'], b['node'], b['texture'], b['want'], b['have']))
u.log('SAMPLER_CHECK textures=%d' % len(report['textures']))
