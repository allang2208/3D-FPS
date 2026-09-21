"""Read the owned Holy Spline emitter inputs needed for the migration."""
import json
from pathlib import Path
import unreal

api = unreal.get_default_object(unreal.NiagaraToolset_System)
asset = unreal.load_asset('/Game/_SplineVFX/NS/NS_Spline_Holy')
out = {'asset': asset.get_path_name(), 'users': api.call_method('GetUserVariables', (asset,)).export_text(), 'emitters': []}
for emitter in api.call_method('GetSystemSummary', (asset,)).get_editor_property('emitters'):
    name = str(emitter.get_editor_property('emitter_name'))
    ref = unreal.NiagaraExt_StackItemReference()
    ref.set_editor_property('system', asset)
    ref.set_editor_property('emitter_name', name)
    data = {'name': name, 'settings': api.call_method('GetEmitterData', (ref,)).export_text(), 'stacks': {}}
    for stage in ['EmitterUpdateScript', 'ParticleSpawnScript', 'ParticleUpdateScript']:
        ref.set_editor_property('script_name', stage)
        data['stacks'][stage] = [v.export_text() for v in api.call_method('GetScriptStackInputValues', (ref,))]
    out['emitters'].append(data)
dest = Path(unreal.Paths.project_dir()) / 'Saved/HolyLightMigration/source-contract.json'
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'file': str(dest), 'asset': out['asset'], 'users': out['users'], 'emitters': [e['name'] for e in out['emitters']]}))
