"""Read Epic template authoring topology; no simulation or asset modification."""
import json, sys
from pathlib import Path
import unreal as u
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API, ref, emitters
out=ROOT/'SourceAssets/DragonBreath20261013/VolumeV8_20261014'
out.mkdir(parents=True,exist_ok=True)
data={}
for name in ['Grid3D_MovingGridFire','Grid3D_Gas_SimpleParticleSource','Grid3D_Gas_Fire']:
    system=u.load_asset('/NiagaraFluids/Templates/Gas/3D/Systems/'+name)
    if not system:raise RuntimeError(name)
    u.DragonBreathAuthorLibrary.prepare_fluid_stack(system)
    data[name]={'summary':API.call_method('GetSystemSummary',(system,)).export_text(),
                'emitters':{}}
    for en in emitters(system):
        top=API.call_method('GetEmitterTopology',(ref(system,en),))
        data[name]['emitters'][en]={'topology':top.export_text(), 'stacks':{}}
        for field in ['emitter_spawn_script','emitter_update_script','particle_spawn_script','particle_update_script']:
            stack=top.get_editor_property(field)
            script=str(stack.get_editor_property('script_name'))
            mods=[]
            for mod in stack.get_editor_property('modules'):
                mn=str(mod.get_editor_property('module_name'))
                mods.append({'name':mn,'topology':mod.export_text(),
                             'values':API.call_method('GetModuleInputValues',(ref(system,en,script,mn),)).export_text()})
            data[name]['emitters'][en]['stacks'][script]=mods
        data[name]['emitters'][en]['renderers']=[API.call_method('GetRendererData',(ref(system,en,renderer=r.get_editor_property('renderer_index')),)).get_editor_property('property_values') for r in top.get_editor_property('renderers')]
    data[name]['users']=API.call_method('GetUserVariables',(system,)).export_text()
    (out/(name+'-all-inputs.json')).write_text(u.DragonBreathAuthorLibrary.describe_fluid_inputs(system),encoding='utf-8')
    (out/(name+'.json')).write_text(json.dumps(data[name],indent=2),encoding='utf-8')
    print('FLUID_TEMPLATE_READ '+name+' '+str(emitters(system)))
