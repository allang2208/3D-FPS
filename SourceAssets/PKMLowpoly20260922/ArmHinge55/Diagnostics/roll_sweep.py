"""201 base reload: constant roll offset of the elbow pair (upper-arm helpers + elbow end of
the forearm, pure hinge kept) swept around the anatomical solution, for elbow close views."""
import sys, json, gzip
import numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE)]
import author as A

idx = json.loads((HERE / 'inputs.json').read_text())
key = '/Game/Weapons/LMG201/ClothReload44/Animations/base/A_LMG201_base_reload'
with gzip.open(idx['201']['clips'][key]['file'], 'rt') as f:
    d = json.load(f)
W = np.array([[A.mat(v) for v in fr] for fr in d['world']])
bind = A.Bind('201')
with gzip.open(HERE.parents[1] / 'LMG20120260927/ClothReload44/Tracks/base_b53_tracks.json.gz', 'rt') as f:
    full = json.load(f)
A.PRONATION_SHARE = {A.LO: 0.0, A.F2: 1 / 3, A.F1: 2 / 3}
for off in [float(x) for x in sys.argv[1:]]:
    A.ROLL_OFFSET = np.radians(off)
    out, info = A.solve(W, bind)
    tr, prev = {n: [] for n in A.WRITE}, {n: None for n in A.WRITE}
    for Wn in out:
        for n in A.WRITE:
            i, p = A.BONES.index(n), A.BONES.index(A.PARENT[n])
            row, prev[n] = A.pack(np.linalg.inv(Wn[p]) @ Wn[i], prev[n])
            tr[n].append(row)
    f2 = dict(full)
    f2.update(tr)
    with gzip.open(HERE / 'Diagnostics' / ('roll_%+03d.json.gz' % off), 'wt') as f:
        json.dump(f2, f, separators=(',', ':'))
    print('ROLL', off)
