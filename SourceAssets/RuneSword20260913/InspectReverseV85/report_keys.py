"""Summarise authoring_v85*.json: turn speeds vs the reversed reference, per-key hand side, clearance frames.

py report_keys.py [authoring json]
"""
import json
import sys
from pathlib import Path

P = Path(__file__).parent
REF = [0, 90, 180, 185, 212, 240, 265, 325, 360]  # reference f2288..f2280 reversed, 33.3 ms apart


def main():
    d = json.loads((P / (sys.argv[1] if len(sys.argv) > 1 else 'authoring_v85.json')).read_text(encoding='utf-8'))
    keys = d['keys']
    print('reference per-step deg/s:', [round((b - a) * 30) for a, b in zip(REF, REF[1:])], 'total 267 ms')
    print('V85 per-key deg/s       :', [round((b['phi'] - a['phi']) / (b['t'] - a['t'])) for a, b in zip(keys, keys[1:])],
          'total', round((keys[-1]['t'] - keys[0]['t']) * 1000), 'ms')
    s = d['samples']
    ph = [(r['seconds'], r['phi_deg']) for r in s]
    sp = [(round(b[0], 3), round((b[1] - a[1]) / (b[0] - a[0]))) for a, b in zip(ph, ph[1:]) if 0.40 <= b[0] <= keys[-1]['t'] + 0.01]
    print('peak', max(sp, key=lambda x: x[1]), 'last before stop', sp[-4:])
    print({k: d[k] for k in ('max_wrist_trim_r_deg', 'hand_roll_v9_r_range_deg', 'min_blade_in_view_depth_m',
                             'max_hilt_in_hand_free_mm', 'max_sword_in_forearm_mm', 'max_guard_in_hand_mm', 'seconds')})
    by_t = {round(r['seconds'] * 120): r for r in s}
    for k in keys:
        r = by_t.get(round(k['t'] * 120))
        if r and not r.get('idle_hold'):
            print(' ', k['name'], k['ref'], 'dorsum', r['dorsum_to_camera'], 'trim', r['wrist_trim_r_deg'],
                  'hilt_side', r['hilt_side_m'], 'cam', r['hilt_to_camera_m'])
    bad = []
    for r in s:
        if r.get('idle_hold'):
            continue
        f, h = r['clear_forearm'], r['clear_hand']
        m = max(f['hilt_max_mm'], f['guard_max_mm'])
        if m > 8 or h['guard_max_mm'] > 22:
            bad.append((round(r['seconds'], 3), round(r['phi_deg']), 'fore', m, 'guard_in_hand', h['guard_max_mm']))
    print('clearance frames (>8 mm forearm or >22 mm guard in hand):', len(bad))
    for b in bad:
        print('   ', b)


if __name__ == '__main__':
    main()
