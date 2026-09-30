import sys
import numpy as np
from scipy.spatial import cKDTree
sys.path[:0] = [r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44\Diagnostics']
import diag_lib as D
import sim_belt_phys as S

tr = D.load_tracks(D.HERE / 'Tracks/base_tracks.json.gz')
for t in (3.70, 3.80, 3.90, 3.95, 4.00, 4.07, 4.15, 4.30, 4.50, 4.70):
    W = D.worlds(tr, [int(round(t * 120))])[0]
    hp = S.skin.pose(W, S.hand_v)
    eye, fw, r, u = D.camera(D.framing_alpha(t))
    row = []
    for n in S.NEW:
        V, F = S.new_skin[n].pose(W), S.new_tris[n]
        lo, hi = V.min(0) - .4, V.max(0) + .4
        m = np.all((hp > lo) & (hp < hi), 1)
        if not m.any():
            continue
        w = D.winding_number(hp[m], V, F)
        ins = np.where(m)[0][w > .5]
        if len(ins):
            d, _ = cKDTree(V).query(hp[ins])
            iv, _ = D.view_metrics(hp[ins], eye, fw, r, u)
            bones = {}
            for v in S.hand_v[ins]:
                b = D.NAMES[S.skin.dom[v]]
                bones[b] = bones.get(b, 0) + 1
            row.append('%s n=%d depth %.2f inview %d %s' % (n[-2:], len(ins), d.max(), iv.sum(), dict(sorted(bones.items(), key=lambda x: -x[1])[:3])))
    print('t=%.2f' % t, ' | '.join(row) if row else 'clear')
