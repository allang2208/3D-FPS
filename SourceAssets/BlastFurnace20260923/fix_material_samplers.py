"""Fix the furnace materials' sampler types and confirm they compile clean.

    & UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this> -unattended -nop4 -nosplash

The in-game white model turned out to be a shader compile failure, not a bad
texture: install set every non-BaseColor TextureSampleParameter2D to
SAMPLERTYPE_LINEAR_COLOR, while UE requires the sampler type to match the
texture's compression setting -- TC_NORMALMAP needs SAMPLERTYPE_NORMAL and
TC_MASKS needs SAMPLERTYPE_MASKS. Those four errors per material meant UE fell
back to an untextured shader.

Only the sampler_type on the expressions is changed; the graph wiring (R
channel of each mask map into Roughness / AO / Metallic) is untouched.
"""
import json
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
ROOT = '/Game/Props/BlastFurnace20260923'
SLOTS = ('Masonry', 'Firebrick', 'WroughtIron', 'ClayLuting',
         'SlagLining', 'EmberBed', 'OreLump')
SAMPLER_FOR = {
    'BaseColor': u.MaterialSamplerType.SAMPLERTYPE_COLOR,
    'Normal': u.MaterialSamplerType.SAMPLERTYPE_NORMAL,
    'Roughness': u.MaterialSamplerType.SAMPLERTYPE_MASKS,
    'AO': u.MaterialSamplerType.SAMPLERTYPE_MASKS,
    'Metallic': u.MaterialSamplerType.SAMPLERTYPE_MASKS,
}
LIB = u.MaterialEditingLibrary
report = {}


def save(asset):
    package = u.load_package(asset.get_path_name().split('.')[0])
    if not u.EditorLoadingAndSavingUtils.save_packages([package], False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())


for name in SLOTS:
    path = '%s/Materials/M_BlastFurnace_%s' % (ROOT, name)
    material = u.load_asset(path)
    if material is None:
        report[name] = {'loaded': False}
        continue

    # Before: what does a recompile say today?
    errors_before = [str(e) for e in LIB.recompile_material(material)]

    changed = []
    for expression in LIB.get_material_expressions(material) or []:
        if expression.get_class().get_name() != 'MaterialExpressionTextureSampleParameter2D':
            continue
        parameter = str(expression.get_editor_property('parameter_name'))
        texture = expression.get_editor_property('texture')
        if texture is None or parameter not in SAMPLER_FOR:
            continue
        wanted = SAMPLER_FOR[parameter]
        current = expression.get_editor_property('sampler_type')
        if current != wanted:
            expression.set_editor_property('sampler_type', wanted)
            # Read back immediately: a wrong enum name silently falls back.
            read_back = expression.get_editor_property('sampler_type')
            if read_back != wanted:
                raise RuntimeError('%s: sampler_type did not stick (%r -> %r)'
                                   % (parameter, wanted, read_back))
            changed.append('%s:%s->%s' % (parameter, current, wanted))

    errors_after = [str(e) for e in LIB.recompile_material(material)]
    report[name] = {'errors_before': len(errors_before), 'errors_after': len(errors_after),
                    'changed': changed,
                    'remaining': [str(e) for e in errors_after][:4]}
    if errors_after:
        raise RuntimeError('%s still fails to compile: %s' % (name, errors_after[:4]))
    save(material)
    print('SAMPLER_FIX %-12s errors %d -> %d, changed %s'
          % (name, len(errors_before), len(errors_after), changed), flush=True)

(HERE / 'sampler-fix.json').write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                       encoding='utf-8')
print('SAMPLER_FIX_DONE', flush=True)
