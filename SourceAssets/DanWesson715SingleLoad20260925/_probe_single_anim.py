"""In-editor (MCP bridge, read-only): single-load animation lengths.

The single-load cue table uses source-clock constants from DanWesson715WeaponAssets
plus a .37 s close offset that does not match any recorded contact.  This measures
the actual clips so cue times can be anchored to real contacts instead.

Read-only: loads assets, changes nothing.
"""
import json

import unreal as u

PALM = '/Game/Weapons/DanWesson715/PalmClearance20260915/Animations/'
LEFT = '/Game/Weapons/DanWesson715/LeftRecovery20260914/Animations/'
SPEED = PALM + 'A_DW715_speed_0.A_DW715_speed_0'

paths = [SPEED]
for n in range(0, 7):
    paths.append(PALM + 'A_DW715_single_0_%d.A_DW715_single_0_%d' % (n, n))
for start in (1, 2, 3, 4, 5):
    for n in range(start, 7):
        paths.append(LEFT + 'A_DW715_single_%d_%d.A_DW715_single_%d_%d' % (start, n, start, n))

rows = []
for p in paths:
    a = u.load_asset(p)
    if a is None:
        rows.append({'asset': p.split('/')[-1], 'loaded': False})
        continue
    rows.append({
        'asset': p.split('/')[-1],
        'loaded': True,
        'play_length': round(float(a.get_play_length()), 4),
        'rate_scale': round(float(a.get_editor_property('rate_scale')), 4),
    })

print('DW715_SINGLE_ANIM ' + json.dumps(rows, indent=2))