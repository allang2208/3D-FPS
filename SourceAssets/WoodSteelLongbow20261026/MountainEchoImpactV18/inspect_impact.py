"""Read only the reported impact system and its material/render bindings."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
OUT = ROOT / 'SourceAssets/WoodSteelLongbow20261026/MountainEchoImpactV18'
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, LIB, ref, emitters

system = u.load_asset('/Game/Weapons/WoodSteelLongbow20261026/MountainEchoFXV14/NS_MountainEcho_GoldenImpact')
result = {'system': system.get_path_name(), 'emitters': [], 'materials': {}}
result['system_data'] = json.loads(API.call_method('GetSystemData', (system,)).get_editor_property('property_values'))
for name in emitters(system):
    renderer = json.loads(API.call_method('GetRendererData', (ref(system, name, renderer=0),)).get_editor_property('property_values'))
    data = json.loads(API.call_method('GetEmitterData', (ref(system, name),)).get_editor_property('property_values'))
    item = {'name': name, 'emitter_data': data, 'renderer': renderer, 'stacks': {}}
    for script in ['EmitterUpdateScript', 'ParticleSpawnScript', 'ParticleUpdateScript']:
        modules = API.call_method('GetScriptStackTopology', (ref(system, name, script),)).get_editor_property('modules')
        item['stacks'][script] = []
        for module in modules:
            module_name = str(module.get_editor_property('module_name'))
            values = {}
            for entry in module.get_editor_property('inputs'):
                key = str(entry.get_editor_property('name'))
                values[key] = u.RainAssetEditor.read_input(system, name, script, module_name, key)
            item['stacks'][script].append({'name': module_name, 'inputs': values})
    result['emitters'].append(item)
    path = renderer.get('Material')
    if isinstance(path, str) and path and path not in result['materials']:
        mat = u.load_asset(path)
        result['materials'][path] = {
            'blend_mode': str(mat.get_editor_property('blend_mode')),
            'depth_test_disabled': mat.get_editor_property('disable_depth_test'),
            'pass': str(mat.get_editor_property('translucency_pass')),
            'custom_code': [n.get_editor_property('code') for n in LIB.get_material_expressions(mat) if isinstance(n, u.MaterialExpressionCustom)]
        }
result['dirty_owned'] = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
                         if 'MountainEcho' in p.get_name()]
(OUT / 'before-inspection.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
u.log('MOUNTAIN_IMPACT_INSPECT ' + json.dumps({'emitters': [e['name'] for e in result['emitters']], 'dirty_owned': result['dirty_owned']}))
