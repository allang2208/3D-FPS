"""Elbow41: extend the Elbow39 pronation repair to the PKM clips it missed.

Elbow39 fixed idle / reload / reload_empty.  A full re-scan with the same
validated surface-roll metric shows the identical defect is still present - and
worse - in the remaining left-arm-heavy clips:

    clip          as-authored step / RMS / TV      after the Elbow39 correction
    equip            281.1 / 115.9 / 251.3             33.5 /  39.1 / 217.0
    sprint_loop      114.0 / 244.2 / 541.7             17.5 /  37.0 / 209.3
    sprint_enter      96.9 / 171.1 / 346.0            306.5 /  38.1 / 218.9
    sprint_exit       96.9 / 171.1 / 346.0            306.5 /  38.1 / 218.9

Same rule, same per-frame guard, same export settings as Elbow39 - this script
only re-points that machinery at the remaining clips.  Every descendant's world
matrix is preserved, so grips, fingers, contacts, the weapon root and the clip's
duration / sample rate / key times are untouched.
"""
import importlib.util
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
E39 = ROOT / 'Elbow39'
HERE = ROOT / 'Elbow41'
EXPORT = HERE / 'Exports'
EDIT = HERE / 'Edit'
for d in (EXPORT, EDIT):
    d.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location('elbow39_author', E39 / 'author_elbow39.py')
E = importlib.util.module_from_spec(spec)
sys.modules['elbow39_author'] = E
spec.loader.exec_module(E)          # main loop is guarded, nothing runs here

E.EDIT = EDIT
E.SAVE_EDIT = True

CLIPS = (
    ('equip', ROOT / 'EquipCharge31' / 'PKM_base_EquipCharge_Editable.blend',
     'PKM31_base_equip', 120, EXPORT / 'A_PKM_equip.fbx', 'PKM_equip_Elbow41'),
    ('sprint_enter', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend',
     'PKM17_base_sprint_enter', 120, EXPORT / 'A_PKM_sprint_enter.fbx',
     'PKM_sprint_enter_Elbow41'),
    ('sprint_loop', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend',
     'PKM17_base_sprint_loop', 120, EXPORT / 'A_PKM_sprint_loop.fbx',
     'PKM_sprint_loop_Elbow41'),
    ('sprint_exit', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend',
     'PKM17_base_sprint_exit', 120, EXPORT / 'A_PKM_sprint_exit.fbx',
     'PKM_sprint_exit_Elbow41'),
)

ONLY = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if ONLY:
    CLIPS = tuple(c for c in CLIPS if c[0] in ONLY)

results = {}
for label, blend, action_name, fps, dest, edit_name in CLIPS:
    print('\n=== %s (%s) ===' % (label, action_name), flush=True)
    res = E.repair(blend, action_name, fps, dest, edit_name)
    scales = [r['scale'] for r in res['report']]
    results[label] = {
        'source_blend': str(blend), 'action': res['action'], 'fps': res['fps'],
        'frames': res['frames'], 'pairs': res['frames'] + 1,
        'max_hand_drift': res['max_hand_drift'],
        'scales': {str(s): scales.count(s) for s in sorted(set(scales))},
        'export': str(dest), 'edit': str(EDIT / (edit_name + '.blend')),
        'report': res['report'],
    }
    print('EXPORTED %s frames %d  max hand drift %.7f  scales %s' % (
        dest.name, res['frames'], res['max_hand_drift'],
        results[label]['scales']), flush=True)

(HERE / 'authoring_elbow41.json').write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
print('\nELBOW41_AUTHOR_DONE', [c[0] for c in CLIPS])