"""Tune hand/arm material INSTANCE parameters only, without touching the shared baseline.

Scope (user decision 2026-09-23): only MI_Manny_01 / MI_Manny_02 instance parameters.
Parent materials (M_Manny_Sleeve_01, M_Manny_RolledCuff3cm_02), the HLSL shaders and all
baked textures stay byte-identical. Nothing is re-baked.

Why instances only: M_Manny_Sleeve_01 hosts the upper arm and M_Manny_RolledCuff3cm_02 hosts
the forearm+glove. MI_Manny_02 already overrides SkinScatterStrength/GloveCuffStart; every
other parameter is currently inherited. Setting a parameter here creates/updates a per-instance
override and leaves every other user of the parent material untouched.

SkinTint/SleeveTint are applied to BOTH instances together so the elbow seam cannot drift:
the sleeve/skin colour decision lives in two independently built materials.

Usage (args after the UE python -script switch):
    tune_instances.py -- apply --skin-detail 0.030 --leather-normal 0.85
    tune_instances.py -- apply --preset detail-up
    tune_instances.py -- baseline
    tune_instances.py -- inspect

Every scalar set is read back and saved with a bounded retry; UE 5.8 scalar setters are not
trusted on their own return value (see Docs/Weapons/hand-equipment-appearance.md).
"""
import json
import sys
import time
from pathlib import Path

import unreal as u

OUT = Path(__file__).parent
UE = '/Game/Weapons/M4InfimaV3'
INSTANCES = {
    'MI_Manny_01': '/Game/Characters/ArmsSkinSleeveCandidate/M_Manny_Sleeve_01',
    'MI_Manny_02': '/Game/Characters/ArmsGloveCuff3cmCandidate/M_Manny_RolledCuff3cm_02',
}

# Accepted baseline, 2026-09-12. Only the two scalars that instances already override.
BASELINE_SCALARS = {
    'MI_Manny_01': {'SkinScatterStrength': 0.18},
    'MI_Manny_02': {'SkinScatterStrength': 0.18, 'GloveCuffStart': 0.8899122968},
}
BASELINE_VECTORS = {
    'MI_Manny_01': {'SkinTint': (.36, .235, .185), 'SleeveTint': (.02, .024, .027)},
    'MI_Manny_02': {'SkinTint': (.36, .235, .185), 'SleeveTint': (.02, .024, .027)},
}

# Coherent parameter sets. These change instance overrides only.
PRESETS = {
    # Cheap, safe, visually meaningful: push fine detail up without touching colour.
    'detail-up': {
        'scalars': {'SkinDetailStrength': 0.030, 'LeatherNormalStrength': 0.85},
    },
    # Same idea, stronger, for judging the ceiling before backing off.
    'detail-strong': {
        'scalars': {'SkinDetailStrength': 0.050, 'LeatherNormalStrength': 1.05},
    },
    # Back off from the accepted values, in case the current read is "too noisy".
    'detail-down': {
        'scalars': {'SkinDetailStrength': 0.006, 'LeatherNormalStrength': 0.35},
    },
    # Skin only: isolate the waxy-skin problem from the leather problem.
    'skin-only': {
        'scalars': {'SkinDetailStrength': 0.035},
    },
    # Leather only: isolate the plastic-leather problem.
    'leather-only': {
        'scalars': {'LeatherNormalStrength': 0.95},
    },
}

MODES = ('inspect', 'apply', 'baseline')
# Engine switches that may still be present in sys.argv; dropped before parsing.
ENGINE_FLAGS = {
    'nullrhi', 'unattended', 'nosplash', 'stdout', 'nopause', 'silent',
    'ddc', 'modelcontextprotocolport', 'run', 'script', 'project', 'game',
    'windowed', 'fullscreen', 'resx', 'resy', 'log', 'abslog', 'exec',
}


def _norm(a):
    return a.lstrip('-').lower()


def _camel(a):
    """skin-detail / skindetail -> skindetail (single flat key)."""
    return _norm(a).replace('-', '').replace('_', '')


def parse_args(argv):
    """Tolerant of both `-- mode --k v` and pure `mode --k v` forms.

    The UE `-run=pythonscript -script=x.py -- ...` commandlet DISCARDS everything
    after -script= (verified: sys.argv == [script_path]). The editor-side MCP bridge
    may forward real args, so accept both rather than assume one.
    """
    if '--' in argv:
        argv = argv[argv.index('--') + 1:]
    toks = [a for a in argv if a != sys.argv[0]]
    mode = None
    opts = {}
    i = 0
    while i < len(toks):
        a = toks[i]
        key = _camel(a)
        if key in MODES and mode is None:
            mode = key
        elif a.startswith('-'):
            if key in ENGINE_FLAGS or key.startswith('ddc') or key.startswith('modelcontext'):
                # swallow "--k v" form for engine switches that carry a value
                if i + 1 < len(toks) and not toks[i + 1].startswith('-'):
                    i += 1
            else:
                nxt = toks[i + 1] if i + 1 < len(toks) else None
                if nxt is not None and not nxt.startswith('-'):
                    opts[key] = nxt
                    i += 1
                else:
                    opts[key] = 'true'
        i += 1
    # `label` is a display string, not a parameter name: keep it underscored.
    if 'label' in opts:
        opts['label'] = str(opts['label'])
    if mode is None:
        # Fallback channel: this commandlet drops argv, so accept request.json beside the script.
        req = OUT / 'request.json'
        if req.is_file():
            data = json.loads(req.read_text())
            mode = data.pop('mode', 'apply')
            opts = {k.replace('-', '').replace('_', ''): v for k, v in data.items()}
            print('HAND_MAT_REQUEST_FILE ' + req.name)
            return mode, opts
        raise SystemExit(
            'no mode given; argv was ' + repr(list(sys.argv)) +
            ' -- this commandlet drops args after -script=; write request.json beside the '
            'script (see README) or drive it via the MCP bridge')
    return mode, opts


def load_instances():
    out = []
    for name, parent in INSTANCES.items():
        mi = u.load_asset(f'{UE}/{name}')
        assert mi, f'missing instance {name}'
        got = mi.parent.get_path_name() if mi.parent else None
        assert got and got.split('.')[0].endswith(parent.split('/')[-1]), \
            f'{name} parent drifted: {got} != {parent}'
        out.append((name, mi))
    return out


def snapshot(mi):
    L = u.MaterialEditingLibrary
    row = {}
    for p in ('SkinDetailStrength', 'LeatherNormalStrength', 'SkinScatterStrength',
              'GloveCuffStart', 'LeatherTileRepeat'):
        row[p] = L.get_material_instance_scalar_parameter_value(mi, p)
    for p in ('SkinTint', 'SleeveTint'):
        c = L.get_material_instance_vector_parameter_value(mi, p)
        row[p] = [round(c.r, 6), round(c.g, 6), round(c.b, 6)]
    return row


def save(mi):
    for _ in range(10):
        if u.EditorAssetLibrary.save_loaded_asset(mi, False):
            return
        time.sleep(1)
    raise RuntimeError('material instance remains occupied: ' + mi.get_path_name())


def apply_rows(rows, before, label):
    """rows: {instance_name: {'scalars': {...}, 'vectors': {...}}}"""
    L = u.MaterialEditingLibrary
    report = []
    for name, mi in load_instances():
        want = rows.get(name)
        if not want:
            continue
        mi.modify()
        for k, v in want.get('scalars', {}).items():
            L.set_material_instance_scalar_parameter_value(mi, k, float(v))
        for k, v in want.get('vectors', {}).items():
            L.set_material_instance_vector_parameter_value(
                mi, k, u.LinearColor(float(v[0]), float(v[1]), float(v[2]), 1.0))
        L.update_material_instance(mi)
        save(mi)
        after = snapshot(mi)
        for k, v in want.get('scalars', {}).items():
            assert abs(after[k] - float(v)) < 1e-4, f'{name}.{k} did not stick: {after[k]}'
        for k, v in want.get('vectors', {}).items():
            got = after[k]
            assert all(abs(got[i] - float(v[i])) < 1e-4 for i in range(3)), \
                f'{name}.{k} did not stick: {got}'
        report.append({'instance': mi.get_path_name(), 'preset': label,
                       'before': before[name], 'after': after})
    (OUT / f'tuning_report_{label}.json').write_text(json.dumps(report, indent=2))
    return report


def same_value_for_both(key, value):
    return {n: {key: value} for n in INSTANCES}


def main():
    mode, opts = parse_args(sys.argv)
    instances = load_instances()
    before = {n: snapshot(mi) for n, mi in instances}

    if mode == 'inspect':
        def overridden(mi, prop):
            try:
                return sorted(str(e.parameter_info.name) for e in mi.get_editor_property(prop))
            except Exception as exc:  # never let inspection mask the real values
                return 'unreadable: ' + str(exc)

        state = {'instances': before, 'parents': {
            n: {'parent': mi.parent.get_path_name(),
                'overridden_scalars': overridden(mi, 'scalar_parameter_values'),
                'overridden_vectors': overridden(mi, 'vector_parameter_values')}
            for n, mi in instances}}
        (OUT / 'instance_state.json').write_text(json.dumps(state, indent=2))
        u.log('HAND_MAT_INSPECT_DONE')
        print('HAND_MAT_INSPECT', json.dumps(state, indent=2))
        return

    if mode == 'baseline':
        rows = {}
        for n in INSTANCES:
            rows[n] = {'scalars': dict(BASELINE_SCALARS[n]),
                       'vectors': dict(BASELINE_VECTORS[n])}
        apply_rows(rows, before, 'baseline')
        u.log('HAND_MAT_BASELINE_APPLIED')
        print('HAND_MAT_BASELINE_APPLIED')
        return

    if mode != 'apply':
        raise SystemExit('unknown mode: ' + mode)

    scalars, vectors = {}, {}
    if 'preset' in opts:
        p = PRESETS[opts['preset']]
        scalars.update(p.get('scalars', {}))
        vectors.update(p.get('vectors', {}))

    keymap = {
        'skindetail': 'SkinDetailStrength',
        'leathernormal': 'LeatherNormalStrength',
        'scatter': 'SkinScatterStrength',
        'cuffstart': 'GloveCuffStart',
        'tilerepeat': 'LeatherTileRepeat',
    }
    for opt, pname in keymap.items():
        if opt in opts:
            scalars[pname] = float(opts[opt])
    for opt, pname in (('skintint', 'SkinTint'), ('sleevetint', 'SleeveTint')):
        if opt in opts:
            val = opts[opt]
            parts = [float(x) for x in (val if isinstance(val, list) else str(val).split(','))]
            assert len(parts) == 3, f'{opt} needs r,g,b'
            vectors[pname] = tuple(parts)

    if not scalars and not vectors:
        raise SystemExit('nothing to apply; pass --preset or explicit --<param> values')

    # Tints and scatter must stay identical across both instances or the elbow seam drifts.
    rows = {}
    for n in INSTANCES:
        rows[n] = {'scalars': dict(scalars), 'vectors': dict(vectors)}
    # GloveCuffStart only exists on the rolled-cuff material (forearm+glove).
    if 'GloveCuffStart' in scalars:
        rows['MI_Manny_01']['scalars'].pop('GloveCuffStart', None)
        if not rows['MI_Manny_01']['scalars'] and not rows['MI_Manny_01']['vectors']:
            rows.pop('MI_Manny_01')

    label = opts.get('label') or opts.get('preset') or 'custom'
    report = apply_rows(rows, before, label)
    u.log('HAND_MAT_TUNE_APPLIED_' + label)
    print('HAND_MAT_TUNE_APPLIED', label)
    print(json.dumps(report, indent=2))


main()
