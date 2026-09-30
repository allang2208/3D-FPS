"""Per-frame penetration breakdown (part x skin region) for a tracks file."""
import sys, json
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import diag_lib as D

tracks = D.load_tracks(Path(sys.argv[1]))
step = int(sys.argv[2]) if len(sys.argv) > 2 else 6
old_hidden, new_vis = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else (2.45, 2.80)
F = len(tracks['hand_l'])
frames = np.arange(0, F, step)
W = D.worlds(tracks, frames)
body = D.Body()
skin = D.load_json_mesh(D.SA / 'ChainmailReloadFit20260929/LMG201_skin.json')
reg = {}
for n, i in D.BI.items():
    for key in ('upperarm', 'lowerarm', 'hand', 'thumb', 'index', 'middle', 'ring', 'pinky'):
        if n.startswith(key):
            reg[i] = key + '_' + n[-1]
region = np.array([reg.get(b, 'other') for b in skin.dom])
for k, fi in enumerate(frames):
    t = fi / 120
    vg = {'gun', 'cover'} | ({'old_feed'} if t < old_hidden else set()) | ({'new_feed'} if t >= new_vis else set())
    sp = skin.pose(W[k])
    sd, part = body.signed(sp, W[k], vg)
    bad = sd < -.3
    if not bad.any():
        continue
    combos = {}
    for r, p, d in zip(region[bad], part[bad], sd[bad]):
        key = (r, p)
        c = combos.setdefault(key, [0, 0.0])
        c[0] += 1
        c[1] = max(c[1], -d)
    top = sorted(combos.items(), key=lambda kv: -kv[1][1])[:4]
    print('t=%.2f ' % t + ' | '.join('%s->%s n=%d d=%.1f' % (r, p, c[0], c[1]) for (r, p), c in top))
