"""Finish the requested configuration diagnosis; read saved assets only."""
from pathlib import Path
import json
import sys
import unreal as u

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parents[2] / 'Tools/Skills'))
from build_fireball_assets import API, ref

path = '/Game/Monsters/HundredEyedSlag/SmokeVisibilityFixV21'
system = u.load_asset(path + '/NS_SlagBodySmoke')
material = u.load_asset(path + '/M_SlagPersistentBodySmoke')
if not system or not material:
    raise RuntimeError('Missing saved smoke assets')
emitter = json.loads(API.call_method('GetEmitterData', (ref(system, 'BodyRisingSoot'),))
                     .get_editor_property('property_values'))
renderer = json.loads(API.call_method('GetRendererData', (ref(system, 'BodyRisingSoot', renderer=0),))
                      .get_editor_property('property_values'))
density = [n for n in u.MaterialEditingLibrary.get_material_expressions(material)
           if isinstance(n, u.MaterialExpressionCustom)
           and str(n.get_editor_property('description')) == 'ImpactSmokeCorrosion20260924 Density']
report = {
    'system': system.get_path_name(), 'material': material.get_path_name(),
    'interpolated_spawn_mode': emitter['InterpolatedSpawnMode'],
    'bounds_mode': emitter['CalculateBoundsMode'],
    'local_space': emitter['bLocalSpace'], 'simulation_target': emitter['SimTarget'],
    'sprite_material': renderer['Material'],
    'density_source_matches_saved_asset': len(density) == 1 and
        str(density[0].get_editor_property('code')) == (OUT / 'PersistentBodySmoke.hlsl').read_text('utf-8'),
    'runtime_tested': False, 'rendered': False,
}
(OUT / 'saved_configuration.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
print('SLAG_SAVED_CONFIGURATION ' + json.dumps(report, ensure_ascii=False))
