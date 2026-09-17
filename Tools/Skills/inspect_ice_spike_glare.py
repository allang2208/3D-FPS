"""Read-only inspection of the ice spike glare: renderers, renderer data and mist material.

Run headless with the editor closed:
  & 'E:\\Program Files (x86)\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe' `
    'D:\\FPS3D\\FPSGAME\\FPSGAME.uproject' -run=pythonscript `
    '-script=D:\\FPS3D\\FPSGAME\\Tools\\Skills\\inspect_ice_spike_glare.py' `
    -unattended -nosplash -NullRHI '-abslog=D:\\FPS3D\\FPSGAME\\Saved\\IceSpike-Glare-Inspect.log'
"""
import json
import sys
from pathlib import Path

import unreal as u

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fireball_assets import API, ROOT, ref  # noqa: E402

SYSTEMS = ['/Game/NiagaraExamples/FX_Weapons/Trails/NS_RocketTrail',
           '/Game/Skills/IceSpike/NS_IceMotes',
           '/Game/Skills/IceSpike/FrostV2/NS_FrostCrystals',
           '/Game/Skills/IceSpike/FrostV2/NS_ColdMist',
           '/Game/Skills/Fireball/NS_FireballTrail',
           '/Game/Skills/Fireball/NS_FireballVelocityTrail']
OUT = ROOT / 'Saved/IceSpike-Glare-Inspect.json'


def renderer_report(system):
    report = []
    summary = API.call_method('GetSystemSummary', (system,))
    for emitter in summary.get_editor_property('emitters'):
        name = str(emitter.get_editor_property('emitter_name'))
        classes = [c.get_name() for c in emitter.get_editor_property('renderer_classes')]
        row = {'emitter': name, 'enabled': emitter.get_editor_property('enabled'),
               'summary_renderer_classes': classes, 'renderers': []}
        topology = API.call_method('GetEmitterTopology', (ref(system, name),))
        for renderer in topology.get_editor_property('renderers'):
            index = renderer.get_editor_property('renderer_index')
            data = API.call_method('GetRendererData', (ref(system, name, renderer=index),))
            values = data.get_editor_property('property_values')
            try:
                parsed = json.loads(values) if values else None
            except ValueError:
                parsed = values
            row['renderers'].append({'index': index,
                                     'class': renderer.get_editor_property('renderer_class').get_name(),
                                     'data': parsed})
        report.append(row)
    return report


def material_report():
    report = {}
    for path in ['/Game/Skills/IceSpike/FrostV2/MI_ColdMist', '/Game/Skills/IceSpike/M_IceMote',
                 '/Game/NiagaraExamples/Materials/MI_RocketFlareCore']:
        instance = u.load_asset(path)
        if not instance:
            report[path] = 'missing'
            continue
        if not isinstance(instance, u.MaterialInstanceConstant):
            # Plain material: describe the emissive/base-colour wiring instead of parameters.
            entry = {'class': instance.get_class().get_name(), 'blend_mode': str(instance.get_editor_property('blend_mode')),
                     'shading_model': str(instance.get_editor_property('shading_model')), 'inputs': {}}
            for prop in [u.MaterialProperty.MP_EMISSIVE_COLOR, u.MaterialProperty.MP_BASE_COLOR]:
                node = u.MaterialEditingLibrary.get_material_property_input_node(instance, prop)
                entry['inputs'][str(prop)] = None if not node else node.get_class().get_name()
            report[path] = entry
            continue
        parent = instance.get_editor_property('parent')
        entry = {'parent': parent.get_path_name() if parent else None,
                 'parent_blend_mode': str(parent.get_editor_property('blend_mode')) if parent else None,
                 'parent_shading_model': str(parent.get_editor_property('shading_model')) if parent else None,
                 'parent_emissive_input': (u.MaterialEditingLibrary.get_material_property_input_node(
                     parent, u.MaterialProperty.MP_EMISSIVE_COLOR).get_class().get_name()
                     if parent and u.MaterialEditingLibrary.get_material_property_input_node(
                         parent, u.MaterialProperty.MP_EMISSIVE_COLOR) else None),
                 'scalars': {}, 'vectors': {}, 'textures': {}, 'static_switches': {}}
        for name in u.MaterialEditingLibrary.get_scalar_parameter_names(instance):
            entry['scalars'][str(name)] = u.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(instance, name)
        for name in u.MaterialEditingLibrary.get_vector_parameter_names(instance):
            entry['vectors'][str(name)] = str(u.MaterialEditingLibrary.get_material_instance_vector_parameter_value(instance, name))
        for name in u.MaterialEditingLibrary.get_texture_parameter_names(instance):
            texture = u.MaterialEditingLibrary.get_material_instance_texture_parameter_value(instance, name)
            entry['textures'][str(name)] = texture.get_path_name() if texture else None
        for name in u.MaterialEditingLibrary.get_static_switch_parameter_names(instance):
            entry['static_switches'][str(name)] = u.MaterialEditingLibrary.get_material_instance_static_switch_parameter_value(instance, name)
        report[path] = entry
    return report


def main():
    out = {'systems': {}, 'materials': material_report()}
    for path in SYSTEMS:
        system = u.load_asset(path)
        if not system:
            out['systems'][path] = 'missing'
            continue
        out['systems'][path] = renderer_report(system)
        u.log('ICE_GLARE_INSPECT ' + path)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    u.log('ICE_GLARE_INSPECT_WRITTEN ' + str(OUT))


if __name__ == '__main__':
    main()
