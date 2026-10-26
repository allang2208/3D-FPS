"""Kukri / left-hand contact on a posed candidate mesh (voxel SDF of the kukri, see grip_fit.py).

Usage: python -I contact_check.py [tag]   (tag '' = hip, '_ads' = ADS). Negative = skin inside the kukri.
"""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import grip_fit as G

tag = sys.argv[1] if len(sys.argv) > 1 else ''
P = G.P
c = json.loads((P / ('candidate%s.json' % tag)).read_text(encoding='utf-8'))
K = np.array(c['poses']['left']['hand_l']) @ np.array(c['kukri_in_hand'])
X = np.load(P / ('arms_camera%s.npz' % tag))['X'][G.HAND]
inv = np.linalg.inv(K)
d = G.sample(X @ inv[:3, :3].T + inv[:3, 3])
report = {g: round(float(d[G.HLAB == g].min()), 3) for g in G.DIGITS + ('palm',)}
report['deepest_cm'] = round(float(d.min()), 3)
report['vertices_deeper_than_voxel_error'] = int((d < -0.12).sum())
print(json.dumps(report))
