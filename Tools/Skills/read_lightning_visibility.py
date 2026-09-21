"""Read authored lightning rendering inputs for the reported invisible arc."""
import json
from pathlib import Path
import unreal

api=unreal.get_default_object(unreal.NiagaraToolset_System)
system=unreal.load_asset('/Game/Skills/Lightning/NS_LightningChain')
out={}
for emitter in ('Currency','MainPower','Detail'):
    ref=unreal.NiagaraExt_StackItemReference()
    ref.set_editor_property('system',system)
    ref.set_editor_property('emitter_name',emitter)
    top=api.call_method('GetEmitterTopology',(ref,))
    rows=[]
    for prop,stage in [('emitter_update_script','EmitterUpdateScript'),('particle_spawn_script','ParticleSpawnScript'),('particle_update_script','ParticleUpdateScript')]:
        for module in top.get_editor_property(prop).get_editor_property('modules'):
            name=str(module.get_editor_property('module_name'))
            if name=='ShapeLocation':continue
            values={}
            for inp in module.get_editor_property('inputs'):
                key=str(inp.get_editor_property('name'))
                if not inp.get_editor_property('is_visible'):continue
                values[key]=unreal.RainAssetEditor.read_input(system,emitter,stage,name,key)
            rows.append({'stage':stage,'module':name,'script':str(module.get_editor_property('module_script')),'values':values})
    out[emitter]=rows
dest=Path(unreal.Paths.project_dir())/'Saved/LightningMigration/visibility-inputs.json'
dest.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(str(dest))
