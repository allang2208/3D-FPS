"""Read back saved material graphs and root-mask assets, without rendering or saving."""
from pathlib import Path
import json
import unreal as u

P = Path(__file__).resolve().parent
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
rows = []

def check(value, label):
    rows.append({'check': label, 'pass': bool(value)})

texture = u.load_asset('/Game/Weapons/AzureRunesword20260913/BladeFinishes20261031/T_RuneSword_FullBladeFinishMask')
check(texture is not None, 'saved packed coverage mask')
if texture:
    check(not texture.get_editor_property('srgb'), 'coverage is linear')
    check(texture.get_editor_property('compression_settings') == u.TextureCompressionSettings.TC_MASKS, 'coverage mask compression')

for path in ['/Game/Weapons/AzureRunesword20260913/M_AzureRunesword',
             '/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold']:
    mat = u.load_asset(path)
    check(mat is not None, path + ' saved master')
    if not mat:
        continue
    check(E.get_metadata_tag(mat, 'FullBladeFinishRevision') == 'FullBladeFinish20261101V1', path + ' revision')
    nodes = L.get_material_expressions(mat)
    finishes = [n for n in nodes if isinstance(n, u.MaterialExpressionCustom)
                and str(n.get_editor_property('desc')).startswith('BladeFinish20261031V1 ')]
    check(len(finishes) == 4, path + ' all PBR outputs')
    scopes = [n for n in nodes if isinstance(n, u.MaterialExpressionScalarParameter)
              and str(n.get_editor_property('parameter_name')) == 'BladeFinishGuardRoot']
    check(len(scopes) == 1 and scopes[0].get_editor_property('default_value') == 0., path + ' full blade default scope')
    for finish in finishes:
        inputs = dict(zip(map(str, L.get_material_expression_input_names(finish)), L.get_inputs_for_material_expression(mat, finish)))
        coverage = inputs.get('Mask')
        check(coverage is not None and str(coverage.get_editor_property('desc')) == 'FullBladeFinish20261101V1 CoverageAndInk',
              path + ' ' + str(finish.get_editor_property('desc')) + ' uses root coverage')
        if coverage:
            sources = dict(zip(map(str, L.get_material_expression_input_names(coverage)), L.get_inputs_for_material_expression(mat, coverage)))
            packed = sources.get('Packed')
            check(packed is not None and packed.get_editor_property('texture') == texture, path + ' packed texture linked')
    check(L.get_material_property_input_node(mat, u.MaterialProperty.MP_FRONT_MATERIAL) is not None, path + ' Substrate connected')
    check(L.get_material_property_input_node(mat, u.MaterialProperty.MP_EMISSIVE_COLOR) is not None, path + ' emission retained')

failures = sum(not row['pass'] for row in rows)
(P / 'saved-material-audit.json').write_text(json.dumps({'checks': rows, 'failures': failures,
    'rendered': False}, indent=2) + '\n', encoding='utf8')
print('BLADE_FINISH_SAVED_ASSET_AUDIT', len(rows), 'checks', failures, 'failures')
if failures:
    raise RuntimeError('Saved blade material audit failed')
