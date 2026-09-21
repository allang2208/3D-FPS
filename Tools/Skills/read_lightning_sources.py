"""Read only the imported lightning source's input and emitter contracts."""
import json
from pathlib import Path
import unreal

api = unreal.get_default_object(unreal.NiagaraToolset_System)
asset = unreal.load_asset('/Game/_SplineVFX/NS/NS_Spline_ElectricLightning')
out = {'asset': asset.get_path_name(), 'class': asset.get_class().get_name()}
out['users'] = api.call_method('GetUserVariables', (asset,)).export_text()
out['summary'] = api.call_method('GetSystemSummary', (asset,)).export_text()
out['emitters'] = []
for emitter in api.call_method('GetSystemSummary', (asset,)).get_editor_property('emitters'):
    name = str(emitter.get_editor_property('emitter_name'))
    ref = unreal.NiagaraExt_StackItemReference()
    ref.set_editor_property('system', asset)
    ref.set_editor_property('emitter_name', name)
    data = {'name': name, 'settings': api.call_method('GetEmitterData', (ref,)).export_text()}
    data['stacks'] = {}
    data['lifecycle'] = {n:unreal.RainAssetEditor.read_input(asset,name,'EmitterUpdateScript','EmitterState',n) for n in ['Life Cycle Mode','Loop Behavior','Loop Duration','Inactive Response']}
    data['initialize'] = {n:unreal.RainAssetEditor.read_input(asset,name,'ParticleSpawnScript','InitializeParticle',n) for n in ['Lifetime','Color','Ribbon Width']}
    for stage in ['EmitterUpdateScript', 'ParticleSpawnScript', 'ParticleUpdateScript']:
        ref.set_editor_property('script_name', stage)
        data['stacks'][stage] = [v.export_text() for v in api.call_method('GetScriptStackInputValues', (ref,))]
    out['emitters'].append(data)
dest = Path(unreal.Paths.project_dir()) / 'Saved/LightningMigration/source-contract.json'
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'file':str(dest), 'asset':out['asset'], 'users':out['users'], 'emitters':[e['name'] for e in out['emitters']]}))
