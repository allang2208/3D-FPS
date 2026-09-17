"""Remove the inherited rocket-flare renderer from the ice spike hover systems.

Evidence (read back through the Niagara toolset, Saved/IceSpike-Glare-Inspect.json):
the RocketTrail emitter of NS_RocketTrail has two sprite renderers, and every system
derived from it kept both. NS_FrostCrystals and NS_ColdMist therefore drew each ice
particle twice - once with the authored ice material and once with the example's
MI_RocketFlareCore, a bright warm flare core - which is the harsh red flame-like glow
reported on the ice spikes. Neither ice system needs a second renderer.

This pass removes only renderers whose material comes from the source example package
(/Game/NiagaraExamples/ or a RocketFlare material). The authored ice renderer, the
modules, the particle colours and the fireball's own flare keep their current look.

Run headless with the editor closed (the project module must load):
  & 'E:\\Program Files (x86)\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe' `
    'D:\\FPS3D\\FPSGAME\\FPSGAME.uproject' -run=pythonscript `
    '-script=D:\\FPS3D\\FPSGAME\\Tools\\Skills\\clear_ice_spike_flare_renderers.py' `
    -unattended -nosplash -NullRHI '-abslog=D:\\FPS3D\\FPSGAME\\Saved\\IceSpike-NoFlare.log'
"""
import json
import sys
from pathlib import Path

import unreal as u

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fireball_assets import API, ROOT, emitters, ref, save  # noqa: E402

SYSTEMS = ['/Game/Skills/IceSpike/FrostV2/NS_FrostCrystals',
           '/Game/Skills/IceSpike/FrostV2/NS_ColdMist']
SOURCE_LEFTOVERS = ('/Game/NiagaraExamples/', 'RocketFlare')
RECEIPT = ROOT / 'SourceAssets/IceSpike5080_20260915/FlareCore20260916/authoring.json'


def renderer_data(system, emitter, index):
    data = API.call_method('GetRendererData', (ref(system, emitter, renderer=index),))
    values = data.get_editor_property('property_values')
    return json.loads(values) if values else {}


def material_path(values):
    material = values.get('Material') or {}
    return str(material.get('refPath') or '') if isinstance(material, dict) else str(material)


def renderers(system):
    """(emitter, index, class, material path, enabled) for every renderer on every emitter."""
    found = []
    for emitter in emitters(system):
        topology = API.call_method('GetEmitterTopology', (ref(system, emitter),))
        for renderer in topology.get_editor_property('renderers'):
            index = renderer.get_editor_property('renderer_index')
            values = renderer_data(system, emitter, index)
            found.append((emitter, index, renderer.get_editor_property('renderer_class').get_name(),
                          material_path(values), bool(values.get('bIsEnabled', True))))
    return found


def strip(system):
    """Drop leftover source-example renderers, highest index first."""
    removed = []
    for emitter, index, class_name, material, enabled in sorted(
            renderers(system), key=lambda entry: -entry[1]):
        if not any(tag in material for tag in SOURCE_LEFTOVERS):
            continue
        values = renderer_data(system, emitter, index)
        API.call_method('RemoveRenderer', (ref(system, emitter, renderer=index),))
        removed.append({'emitter': emitter, 'renderer_index': index, 'renderer_class': class_name,
                        'material': material, 'was_enabled': enabled,
                        'removed_property_values': json.dumps(values, ensure_ascii=False)})
        u.log('ICE_SPIKE_FLARE_REMOVED %s %s renderer=%d material=%s'
              % (system, emitter, index, material))
    return removed


def main():
    receipt = {'status': 'inherited rocket-flare renderer removed; ice renderer and modules untouched',
               'game_tested': False, 'systems': {}}
    for path in SYSTEMS:
        system = u.load_asset(path)
        if not system:
            raise RuntimeError('Missing system ' + path)
        before = renderers(system)
        removed = strip(system)
        save(system)
        after = renderers(system)
        leftovers = [row for row in after if any(tag in row[3] for tag in SOURCE_LEFTOVERS)]
        if not removed:
            raise RuntimeError('No source-example renderer found on ' + path)
        if leftovers:
            raise RuntimeError('Source-example renderer survived on ' + path + ': ' + str(leftovers))
        receipt['systems'][path] = {
            'renderers_before': [list(row) for row in before],
            'removed': removed,
            'renderers_after': [list(row) for row in after]}
        u.log('ICE_SPIKE_FLARE_OK %s removed=%d remaining=%d' % (path, len(removed), len(after)))
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    u.log('ICE_SPIKE_FLARE_AUTHORED')


if __name__ == '__main__':
    main()
