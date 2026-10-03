"""Read only the smoke's assets and current instances for the reported loss."""
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
import sys
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, ref

asset = u.load_asset('/Game/Monsters/HundredEyedSlag/BodySmokeV20/NS_SlagBodySmoke')
report = {'asset_exists': bool(asset), 'live': []}
material = u.load_asset('/Game/Fluids/ImpactSmokeCorrosion20260924/M_RollingImpactSmoke')
if material:
    report['material'] = {'blend': str(material.get_editor_property('blend_mode')), 'nodes': []}
    for node in u.MaterialEditingLibrary.get_material_expressions(material):
        if isinstance(node, u.MaterialExpressionCustom):
            report['material']['nodes'].append({'description': str(node.get_editor_property('description')), 'code': str(node.get_editor_property('code'))})
if asset:
    report['system'] = str(API.call_method('GetSystemSummary', (asset,)).export_text())
    report['parameters'] = str(API.call_method('GetUserVariables', (asset,)).export_text())
    report['emitter'] = str(API.call_method('GetEmitterData', (ref(asset, 'BodyRisingSoot'),)).export_text())
    report['renderer'] = str(API.call_method('GetRendererData', (ref(asset, 'BodyRisingSoot', renderer=0),)).export_text())
    for stage, module, pin in [('EmitterUpdateScript', 'SpawnRate', 'SpawnRate'),
                                ('EmitterUpdateScript', 'EmitterState', 'Loop Behavior')]:
        report[pin] = str(u.RainAssetEditor.read_input(asset, 'BodyRisingSoot', stage, module, pin))
    report['stacks'] = {}
    for stage in ['ParticleSpawnScript', 'ParticleUpdateScript']:
        stack = API.call_method('GetScriptStackTopology', (ref(asset, 'BodyRisingSoot', stage),))
        report['stacks'][stage] = [
            {'module': str(m.get_editor_property('module_name')),
             'inputs': [str(v.get_editor_property('name')) for v in m.get_editor_property('inputs')]}
            for m in stack.get_editor_property('modules')]
world = u.EditorLevelLibrary.get_game_world()
if world:
    cls = u.load_class(None, '/Script/FPSGAME.SlagBlackMist')
    actors = u.GameplayStatics.get_all_actors_of_class(world, cls) if cls else []
    for actor in actors:
        record = {'actor': actor.get_name(), 'position': str(actor.get_actor_location()),
                  'radius': actor.get_editor_property('Radius'),
                  'hold': actor.get_editor_property('SmokeLifetime')}
        components = actor.get_components_by_class(u.NiagaraComponent)
        record['components'] = []
        for component in components:
            item = {'name': component.get_name(), 'active': component.is_active(),
                    'visible': component.is_visible(), 'location': str(component.get_world_location()),
                    'asset': str(component.get_asset()),
                    'available_reads': [n for n in dir(component) if any(s in n for s in ['variable', 'parameter', 'bounds', 'particle', 'culled'])]}
            record['components'].append(item)
        report['live'].append(record)
(OUT / 'smoke_chain_read.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
print(json.dumps({'asset_exists': bool(asset), 'stacks': report.get('stacks'), 'live': report['live']}, ensure_ascii=False))
