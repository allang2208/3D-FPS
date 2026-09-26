"""Verify the authored Clearwater assets without opening the editor UI.

Reads back what author_clearwater_water.py produced: asset presence, material graph shape,
Custom node input counts against nodes.json, instance parameter values, level actor list.
Prints a report and writes Saved/ClearwaterWater20260926/verify.json.

    "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" \
        D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript \
        -script=D:/FPS3D/FPSGAME/Tools/Fluids/clearwater_verify.py \
        -unattended -noP4 -nosplash -NullRHI -abslog=.../clearwater_verify.log
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir())
ASSETS = ROOT / 'SourceAssets' / 'ClearwaterWater20260926'
OUT = ROOT / 'Saved' / 'ClearwaterWater20260926'
DEST = '/Game/Clearwater'

EXPECTED = [
    DEST + '/T_ClearwaterCaustics',
    DEST + '/T_ClearwaterRipples_N',
    DEST + '/M_ClearwaterWater',
    DEST + '/MI_ClearwaterWater',
    DEST + '/M_ClearwaterSeabed',
    DEST + '/MI_ClearwaterSeabed',
    DEST + '/M_ClearwaterUnderwater',
    DEST + '/MI_ClearwaterUnderwater',
    DEST + '/SM_ClearwaterPlane',
    DEST + '/SM_ClearwaterSeabed',
    DEST + '/L_ClearwaterWater',
]

report = {'assets': {}, 'materials': {}, 'level': {}, 'problems': []}


def custom_nodes(material):
    """Every Custom expression in the material, with its input pin names."""
    found = {}
    for expr in u.MaterialEditingLibrary.get_material_expressions(material):
        if not isinstance(expr, u.MaterialExpressionCustom):
            continue
        desc = str(expr.get_editor_property('description'))
        inputs = []
        try:
            for pin in expr.get_editor_property('inputs'):
                inputs.append(str(pin.get_editor_property('input_name')))
        except Exception as exc:
            report['problems'].append('cannot read inputs of %s: %s' % (desc, exc))
        found[desc] = inputs
    return found


def main():
    for path in EXPECTED:
        report['assets'][path] = u.EditorAssetLibrary.does_asset_exist(path)
        if not report['assets'][path]:
            report['problems'].append('missing asset ' + path)

    nodes_doc = json.loads((ASSETS / 'nodes.json').read_text(encoding='utf-8'))
    spec_by_desc = {v.get('description', k): v for k, v in nodes_doc['nodes'].items()}

    for mat_path in (DEST + '/M_ClearwaterWater', DEST + '/M_ClearwaterSeabed',
                     DEST + '/M_ClearwaterUnderwater'):
        mat = u.load_asset(mat_path)
        if mat is None:
            continue
        entry = {'nodes': {}, 'blend_mode': None, 'domain': None}
        try:
            entry['blend_mode'] = str(mat.get_editor_property('blend_mode'))
            entry['domain'] = str(mat.get_editor_property('material_domain'))
        except Exception:
            pass
        for desc, pins in custom_nodes(mat).items():
            entry['nodes'][desc] = {'pins': len(pins), 'first': pins[:4], 'last': pins[-3:]}
            spec = spec_by_desc.get(desc)
            if spec is None:
                # The seabed's albedo node is defined inline in the authoring script rather
                # than in nodes.json (it is a literal, not part of the ported maths), so it
                # is expected here and only its pin count is worth recording.
                if desc != 'seabed albedo':
                    report['problems'].append(
                        '%s: custom node %r not in nodes.json' % (mat_path, desc))
                continue
            if pins != spec['inputs']:
                report['problems'].append(
                    '%s: node %r pin mismatch (material %d vs spec %d)'
                    % (mat_path, desc, len(pins), len(spec['inputs'])))
        report['materials'][mat_path] = entry

    # Instance parameters: the values C++ will animate must exist.
    for mi_path, wanted in (
            (DEST + '/MI_ClearwaterWater',
             ['Wave01', 'Wave48', 'WaterHit0', 'WaterHit3', 'CausticShiftA', 'CausticShiftB',
              'CausticScale', 'CausticStrength', 'SunDirection', 'FineNormalMap', 'CausticMap']),
            (DEST + '/MI_ClearwaterSeabed',
             ['CausticShiftA', 'CausticShiftB', 'CausticScale', 'CausticStrength', 'CausticMap']),
            (DEST + '/MI_ClearwaterUnderwater',
             ['SunDirection', 'SigmaA', 'SigmaS'])):
        mi = u.load_asset(mi_path)
        if mi is None:
            continue
        present = set()
        # Scan the parent material's parameter expressions: the Python API exposes
        # single-value getters for instance parameters, not a list, so the parent is the
        # reliable place to confirm a parameter name exists at all.
        parent = mi.get_editor_property('parent')
        if parent is not None:
            for expr in u.MaterialEditingLibrary.get_material_expressions(parent):
                try:
                    name = str(expr.get_editor_property('parameter_name'))
                except Exception:
                    continue
                if name:
                    present.add(name)
        missing = [w for w in wanted if w not in present]
        report['materials'][mi_path] = {'parameters_expected': len(wanted),
                                        'missing': missing,
                                        'present_sample': sorted(present)[:10]}
        for m in missing:
            report['problems'].append('%s: missing parameter %s' % (mi_path, m))

    # Level contents.
    try:
        lev = u.get_editor_subsystem(u.LevelEditorSubsystem)
        actors = u.get_editor_subsystem(u.EditorActorSubsystem)
        lev.load_level(DEST + '/L_ClearwaterWater')
        labels = []
        for a in actors.get_all_level_actors():
            labels.append({'label': str(a.get_actor_label()),
                           'class': a.get_class().get_name(),
                           'tags': [str(t) for t in a.tags]})
        report['level'] = {'actors': labels, 'count': len(labels)}
        if not any('ClearwaterSeabed' in a['tags'] for a in labels):
            report['problems'].append('level has no actor tagged ClearwaterSeabed')
    except Exception as exc:
        report['problems'].append('level inspection failed: %s' % exc)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'verify.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    print('CLEARWATER_VERIFY problems=%d assets=%d materials=%d level_actors=%d -> %s'
          % (len(report['problems']), len(report['assets']), len(report['materials']),
             report['level'].get('count', 0), OUT / 'verify.json'))


if __name__ == '__main__':
    main()
