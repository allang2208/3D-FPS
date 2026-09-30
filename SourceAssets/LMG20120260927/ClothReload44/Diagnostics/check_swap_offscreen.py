"""Old pouch must be out of view when hidden, new pouch out of view when shown."""
import sys
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import diag_lib as D

tracks = D.load_tracks(Path(sys.argv[1]))
old_hidden, new_visible = float(sys.argv[2]), float(sys.argv[3])
body = D.Body()
res = {}
for label, t, parts in (('old@hide', old_hidden, ['LMG201_Box'] + ['LMG201_Belt_%02d' % k for k in range(6)]),
                        ('new@show', new_visible, ['New_LMG201_Box'] + ['New_LMG201_Belt_%02d' % k for k in range(6)])):
    fr = int(round(t * 120))
    for f in (fr - 1, fr, fr + 1):
        W = D.worlds(tracks, [f])[0]
        eye, fw, r, u = D.camera(D.framing_alpha(f / 120))
        n = tot = 0
        for p in parts:
            sel = body.parts[p]
            pts = D.Skin(body.pos[sel], (body.bi[sel], body.bw[sel])).pose(W)
            ins, _ = D.view_metrics(pts, eye, fw, r, u)
            n += int(ins.sum())
            tot += len(pts)
        res.setdefault(label, []).append((round(f / 120, 3), n, tot))
for k, v in res.items():
    print(k, ' '.join('t=%.3f in-view %d/%d' % x for x in v))
