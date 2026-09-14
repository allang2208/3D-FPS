"""Read local flame authoring inputs. Does not play effects or save UE assets."""
import json
from pathlib import Path
import unreal

API = unreal.get_default_object(unreal.NiagaraToolset_System)
OUT = Path(unreal.Paths.project_dir()) / 'SourceAssets/FireballBurn20260914'

def ref(system, emitter, script='', module='', renderer=-1):
    r = unreal.NiagaraExt_StackItemReference()
    for k, v in dict(system=system, emitter_name=emitter, script_name=script,
                     module_name=module, renderer_index=renderer).items():
        r.set_editor_property(k, v)
    return r

result = {}
for path in ['/Game/NiagaraExamples/FX_Misc/NS_Fire', '/Game/Skills/Fireball/NS_FireballCore']:
    system = unreal.load_asset(path)
    data = {}
    for summary in API.call_method('GetSystemSummary', (system,)).get_editor_property('emitters'):
        name = str(summary.get_editor_property('emitter_name'))
        top = API.call_method('GetEmitterTopology', (ref(system, name),))
        entry = {'topology': top.export_text(),
                 'data': json.loads(API.call_method('GetEmitterData', (ref(system, name),)).get_editor_property('property_values')),
                 'renderers': [], 'inputs': {}}
        for renderer in top.get_editor_property('renderers'):
            i = renderer.get_editor_property('renderer_index')
            entry['renderers'].append(json.loads(API.call_method('GetRendererData', (ref(system, name, renderer=i),)).get_editor_property('property_values')))
        for field in ['emitter_update_script', 'particle_spawn_script', 'particle_update_script']:
            stack = top.get_editor_property(field)
            script = str(stack.get_editor_property('script_name'))
            for module in stack.get_editor_property('modules'):
                module_name = str(module.get_editor_property('module_name'))
                entry['inputs'][script + '/' + module_name] = API.call_method('GetModuleInputValues', (ref(system, name, script, module_name),)).export_text()
        data[name] = entry
    result[path] = data
materials = {}
for name in ['MI_Flames', 'MI_FireRoil_8x8', 'MI_Sparks']:
    mat = unreal.load_asset('/Game/NiagaraExamples/Materials/' + name)
    lib = unreal.MaterialEditingLibrary
    materials[name] = {'parent': mat.get_editor_property('parent').get_path_name(),
                      'scalars': {str(k): lib.get_material_instance_scalar_parameter_value(mat, k) for k in lib.get_scalar_parameter_names(mat)},
                      'textures': {str(k): str(lib.get_material_instance_texture_parameter_value(mat, k)) for k in lib.get_texture_parameter_names(mat)}}
result['materials'] = materials
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'source-inputs.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
unreal.log('FIREBALL_FLAME_SOURCES_READ')
