"""Overlay motion_profile.py outputs: py plot_profiles.py out.png label=prof.json [label=prof.json ...]"""
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

out = sys.argv[1]
runs = [(a.split('=')[0], json.load(open(a.split('=', 1)[1]))) for a in sys.argv[2:]]
panels = [('blade_screen_deg_s', 'blade line on screen (deg/s, + = CCW)'), ('WPN_root_deg_s', 'sword ang. speed (deg/s)'),
          ('hand_r_deg_s', 'hand_r ang. speed (deg/s)'), ('hand_r_m_s', 'hand_r speed (m/s)'),
          ('lowerarm_r_deg_s', 'lowerarm_r ang. speed (deg/s)'), ('hand_l_m_s', 'hand_l speed (m/s)')]
fig, axes = plt.subplots(len(panels), 1, figsize=(12, 2.3 * len(panels)), sharex=True)
for ax, (key, title) in zip(axes, panels):
    for label, r in runs:
        ax.plot(r['t'], r[key], label=label, lw=1.4)
    ax.set_title(title, fontsize=9, loc='left')
    ax.grid(alpha=0.3)
axes[0].legend(fontsize=8)
axes[-1].set_xlabel('time (s)')
fig.tight_layout()
fig.savefig(out, dpi=90)
for label, r in runs:
    sp = [abs(v) for v in r['blade_screen_deg_s']]
    peaks = [(round(r['t'][i], 3), round(sp[i])) for i in range(1, len(sp) - 1)
             if sp[i] >= sp[i - 1] and sp[i] > sp[i + 1] and sp[i] > 150]
    dips = [(round(r['t'][i], 3), round(sp[i])) for i in range(1, len(sp) - 1)
            if sp[i] <= sp[i - 1] and sp[i] < sp[i + 1] and sp[i] > 50]
    acc = [abs(b - a) * r['fps'] for a, b in zip(sp, sp[1:])]
    print(label, 'frames', r['frames'], 'peaks', peaks, 'dips', dips, 'max |accel| deg/s2', round(max(acc)))
