"""Per action (worst over grip families): study.json -> table."""
import json, sys
from collections import defaultdict
from pathlib import Path

d = json.loads((Path(__file__).resolve().parent / (sys.argv[1] if len(sys.argv) > 1 else 'study.json')).read_text())
agg = defaultdict(lambda: defaultdict(float))
for r in d['rows']:
    a = agg[(r['gun'], r['act'])]
    for k, v in r.items():
        if isinstance(v, float):
            a[k] = max(a[k], v)
print('weights', d.get('weight_pos_cm'), d.get('weight_ang_deg'), 'rate', d.get('rate'))
print('%-4s %-26s %7s %7s | %6s %6s %6s | %6s %6s | %6s %6s | %6s %6s | %6s %6s | %6s %6s | %6s %6s | %5s %5s | %s'
      % ('gun', 'action', 'gun_cm', 'gun_deg', 'handG', 'handGd', 'handA', 'fingG', 'fingA', 'elbG', 'elbA',
         'spinL', 'spinF', 'elbvL', 'elbvF', 'uspL', 'uspF', 'fspL', 'fspF', 'upper', 'fore', 'recon'))
for (gun, act), a in sorted(agg.items()):
    print('%-4s %-26s %7.1f %7.1f | %6.2f %6.1f %6.1f | %6.1f %6.1f | %6.1f %6.1f | %6.0f %6.0f | %6.0f %6.0f | %6.0f %6.0f | %6.0f %6.0f | %5.0f %5.0f | %.1e'
          % (gun, act, a['gun_cm'], a['gun_deg'], a['hand_cm_grip'], a['hand_deg_grip'], a['hand_cm_all'],
             a['finger_deg_grip'], a['finger_deg_all'], a['elbow_cm_grip'], a['elbow_cm_all'], a['spin_layer'], a['spin_family'],
             a['elbow_speed_layer'], a['elbow_speed_family'], a['upper_spin_layer'], a['upper_spin_family'],
             a['fore_spin_layer'], a['fore_spin_family'], a['upper_roll_deg'], a['forearm_deg'], a['recon_deg']))
