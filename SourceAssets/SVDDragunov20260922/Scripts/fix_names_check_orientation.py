"""Fix the two mis-cased material packages, then check the weapon forward-axis convention.

Part 1: UE asset paths are case-insensitive, so creating "M_SVD_ChargingHandle" resolved to
the existing "M_SVD_Charginghandle" package and kept the old file name. A case-only rename
is a no-op, so each asset is renamed to a temporary name and back.

Part 2: the SVD body's long axis lands on Y in UE (122.5 cm). Before rigging, compare that
with the project's existing weapon meshes to learn which axis a weapon is supposed to face,
so a wrong-facing import is caught now rather than in the hold.

Run:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
BASE = '/Game/Weapons/SVDDragunov20260922'
E = u.EditorAssetLibrary

report = {'renames': [], 'orientation': {}, 'stale': []}

CASE_FIXES = [
    (BASE + '/Materials/M_SVD_Charginghandle', BASE + '/Materials/M_SVD_ChargingHandle'),
    (BASE + '/Materials/M_SVD_Safetylever', BASE + '/Materials/M_SVD_SafetyLever'),
]
for old, new in CASE_FIXES:
    if not E.does_asset_exist(old):
        report['renames'].append({'old': old, 'result': 'absent'})
        continue
    tmp = new + '_TMPCASE'
    ok1 = E.rename_asset(old, tmp)
    ok2 = E.rename_asset(tmp, new) if ok1 else False
    report['renames'].append({'old': old, 'new': new, 'rename_to_tmp': bool(ok1), 'rename_back': bool(ok2),
                              'exists_after': bool(E.does_asset_exist(new))})

for stale in (BASE + '/Meshes/SM_SVD_Scope', BASE + '/Materials/M_SVD_Scope', BASE + '/Materials/MI_SVD_Scope'):
    if E.does_asset_exist(stale):
        if E.delete_asset(stale):
            report['stale'].append(stale)

# --- orientation convention: which axis does a weapon face in this project? ---
def describe(path, kind):
    asset = u.load_asset(path)
    if asset is None:
        return {'found': False}
    bounds = asset.get_bounds()
    ext = [round(float(bounds.box_extent.x) * 2, 2), round(float(bounds.box_extent.y) * 2, 2),
           round(float(bounds.box_extent.z) * 2, 2)]
    longest = 'XYZ'[ext.index(max(ext))]
    entry = {'found': True, 'size_cm': ext, 'longest_axis': longest,
             'origin_cm': [round(float(bounds.origin.x), 2), round(float(bounds.origin.y), 2),
                           round(float(bounds.origin.z), 2)]}
    if kind == 'skeletal':
        sk = asset.get_editor_property('skeleton')
        entry['skeleton'] = sk.get_path_name().split('.')[0] if sk else None
    if kind == 'static':
        entry['material_slots'] = len(asset.get_editor_property('static_materials'))
    return entry


CANDIDATES = [
    ('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416', 'skeletal'),
    ('/Game/Weapons/QBZ191/SK_QBZ191_Manny', 'skeletal'),
    (BASE + '/Meshes/SM_SVD_Body', 'static'),
]
for path, kind in CANDIDATES:
    report['orientation'][path] = describe(path, kind)

# per-part SVD bounds so the assembled length axis is unambiguous
parts = {}
for name in ('SM_SVD_Body', 'SM_SVD_Magazine', 'SM_SVD_Trigger', 'SM_SVD_ScopeBody'):
    asset = u.load_asset(BASE + '/Meshes/' + name)
    if asset:
        b = asset.get_bounds()
        parts[name] = {'origin': [round(float(b.origin.x), 2), round(float(b.origin.y), 2), round(float(b.origin.z), 2)],
                       'extent': [round(float(b.box_extent.x) * 2, 2), round(float(b.box_extent.y) * 2, 2),
                                  round(float(b.box_extent.z) * 2, 2)]}
report['svd_parts'] = parts

(ROOT / 'Receipts' / 'name_fix_and_orientation.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print('FIX_AND_ORIENT', json.dumps(report, default=str))
