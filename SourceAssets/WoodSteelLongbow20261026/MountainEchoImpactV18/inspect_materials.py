import json
from pathlib import Path
import unreal as u
out = Path(u.Paths.project_dir()) / 'SourceAssets/WoodSteelLongbow20261026/MountainEchoImpactV18'
data = json.loads((out / 'before-inspection.json').read_text(encoding='utf-8'))
lib = u.MaterialEditingLibrary
for emitter in data['emitters']:
    path = emitter['renderer']['Material']['refPath']
    if path in data['materials']:
        continue
    mat = u.load_asset(path)
    data['materials'][path] = {
        'blend': str(mat.get_editor_property('blend_mode')),
        'pass': str(mat.get_editor_property('translucency_pass')),
        'code': [n.get_editor_property('code') for n in lib.get_material_expressions(mat) if isinstance(n, u.MaterialExpressionCustom)]}
effect = u.load_asset(data['system_data']['EffectType']['refPath'])
data['effect_scalability'] = effect.get_editor_property('system_scalability_settings').export_text()
(out / 'before-inspection.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
u.log('MOUNTAIN_IMPACT_MATERIALS ' + json.dumps({'materials': len(data['materials']), 'scalability': data['effect_scalability']}))
