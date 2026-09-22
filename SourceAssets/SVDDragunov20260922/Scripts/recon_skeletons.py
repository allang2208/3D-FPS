"""Read the bone list of the existing weapon skeletons (what a new gun must bind to).

UE 5.8 does not expose `reference_skeleton.bone_names` to Python the way the older docs
suggest, so this probes the available API on the skeleton asset and prints the bone list
whichever way works.

Run:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/SVDDragunov20260922/Receipts')
SKELETONS = [
    '/Game/Weapons/M4HK416Replica/SK_M4_HK416_Skeleton',
    '/Game/Weapons/QBZ191/SK_QBZ191_Manny_Skeleton',
]
MESHES = [
    '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
    '/Game/Weapons/QBZ191/SK_QBZ191_Manny',
]

report = {}

for path in SKELETONS + MESHES:
    asset = u.load_asset(path)
    if asset is None:
        report[path] = {'found': False}
        continue
    entry = {'found': True, 'class': asset.get_class().get_name(),
             'bone_api': [m for m in dir(asset) if 'bone' in m.lower() or 'ref' in m.lower()]}
    bones = None
    for method in ('get_bone_names', 'get_reference_pose', 'bone_names'):
        if hasattr(asset, method):
            try:
                value = getattr(asset, method)()
                bones = [str(b) for b in value]
                entry['bone_source'] = method
                break
            except Exception as exc:  # noqa: BLE001
                entry.setdefault('errors', []).append('%s: %s' % (method, exc))
    if bones is None:
        try:
            tree = asset.get_editor_property('bone_tree')
            bones = [str(n.get_editor_property('name')) for n in tree]
            entry['bone_source'] = 'bone_tree'
        except Exception as exc:  # noqa: BLE001
            entry.setdefault('errors', []).append('bone_tree: %s' % exc)
        try:
            ref = asset.get_editor_property('reference_skeleton')
            bones = [str(n) for n in ref.get_editor_property('bone_names')]
            entry['bone_source'] = 'reference_skeleton.bone_names'
        except Exception as exc:  # noqa: BLE001
            entry.setdefault('errors', []).append('reference_skeleton: %s' % exc)
    entry['bones'] = bones
    entry['bone_count'] = len(bones) if bones else 0
    report[path] = entry

(OUT / 'skeleton_recon.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
for path, entry in report.items():
    print('ASSET', path, '->', json.dumps({k: v for k, v in entry.items() if k != 'bones'}, default=str)[:400])
    if entry.get('bones'):
        print('   bones:', entry['bones'])
