"""Read back the two field-glove materials after the grain/cuff rebuild."""
import json
from pathlib import Path

import unreal as u

AUTHOR = Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260925/FieldGlovesLeatherV1')
L = u.MaterialEditingLibrary
paths = [
    '/Game/Characters/ModularOutfit20260924/Materials/M_FieldGloves_Brown',
    '/Game/Characters/ModularOutfit20260924/Materials/M_FieldGloves_Black',
]
report = {}
for path in paths:
    mat = u.load_asset(path)
    if not mat:
        raise RuntimeError('Missing '+path)
    params = {}
    textures = {}
    for expr in L.get_material_expressions(mat):
        if isinstance(expr, u.MaterialExpressionScalarParameter):
            params[str(expr.get_editor_property('parameter_name'))] = float(expr.get_editor_property('default_value'))
        elif isinstance(expr, u.MaterialExpressionTextureSampleParameter2D):
            tex = expr.get_editor_property('texture')
            textures[str(expr.get_editor_property('parameter_name'))] = tex.get_path_name() if tex else None
        elif isinstance(expr, u.MaterialExpressionTextureObjectParameter):
            tex = expr.get_editor_property('texture')
            textures[str(expr.get_editor_property('parameter_name'))] = tex.get_path_name() if tex else None
    names = {str(n.get_name()) for n in L.get_material_expressions(mat)}
    report[path.split('/')[-1]] = {
        'class': mat.get_class().get_name(),
        'params': params,
        'textures': textures,
        'has_preskinned': any('PreSkinned' in n for n in names),
        'has_height': 'LeatherHeight' in textures or 'LeatherHeightCm' in params,
    }
(AUTHOR/'verify-v7.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('FIELD_GLOVES_LEATHER_VERIFY', json.dumps(report), flush=True)
