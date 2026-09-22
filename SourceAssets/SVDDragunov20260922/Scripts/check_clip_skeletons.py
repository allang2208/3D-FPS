"""Which skeleton is each resolved clip actually on?

verify_asset_resolution.py reported that the idle clip the SVD would load sits on a different
skeleton than its mesh. The M4 viewmodel loads clips through the identical code path, so this
prints the skeleton of every relevant asset to tell a real SVD gap from a project-wide quirk.

Run:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
ASSETS = [
    ('mesh', '/Game/Weapons/SVDDragunov20260922/Viewmodel/SK_SVD_Manny'),
    ('mesh', '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416'),
    ('mesh', '/Game/Weapons/AKMIntegration/SovietFab/SK_AKM_MannyNative'),
    ('clip', '/Game/Weapons/M4ContactImpactFinal/A_AKM_idle'),
    ('clip', '/Game/Weapons/M4ContactImpactFinal/A_AKM_aim'),
    ('clip', '/Game/Weapons/M4ContactImpactFinal/A_AKM_fire'),
    ('clip', '/Game/Weapons/M4ContactImpactFinal/A_AKM_aim_fire'),
    ('clip', '/Game/Weapons/M4TacticalTossFinal/A_M4_HK416_reload'),
    ('clip', '/Game/Weapons/M4SlapImpactFinal/A_M4_HK416_reload_empty'),
    ('clip', '/Game/Weapons/M4WrapGripFinal/A_M4_HK416_equip_charge'),
]

rows = []
for kind, path in ASSETS:
    asset = u.load_asset(path)
    if asset is None:
        rows.append({'kind': kind, 'path': path, 'found': False})
        continue
    skeleton = None
    if isinstance(asset, u.SkeletalMesh):
        skeleton = asset.skeleton
    elif isinstance(asset, u.AnimSequence):
        skeleton = asset.get_editor_property('skeleton')
    rows.append({
        'kind': kind, 'path': path, 'found': True,
        'class': asset.get_class().get_name(),
        'skeleton': skeleton.get_path_name().split('.')[0] if skeleton else None,
    })

# what does the M4A1 path resolve to for "idle"? mirror LoadAKMAnimation's folder logic
report = {'rows': rows}
m4_skeleton = next((r['skeleton'] for r in rows if r['path'].endswith('SK_M4_FoldingSights_HK416')), None)
svd_skeleton = next((r['skeleton'] for r in rows if 'SVDDragunov' in r['path']), None)
report['same_skeleton'] = m4_skeleton == svd_skeleton
report['clips_on_m4_skeleton'] = [r['path'] for r in rows if r['kind'] == 'clip' and r.get('skeleton') == m4_skeleton]
report['clips_on_other_skeleton'] = {r['path']: r.get('skeleton') for r in rows
                                     if r['kind'] == 'clip' and r.get('skeleton') != m4_skeleton}
(ROOT / 'Receipts' / 'clip_skeletons.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print('CLIP_SKELETONS ' + json.dumps(report, default=str))
