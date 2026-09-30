"""Hand-local shift of the held cell (relative to the current authored pinch contact)
that keeps thumb/index on the cell surface instead of inside it."""
import sys
import numpy as np
from scipy.spatial import cKDTree
sys.path[:0] = [r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44', r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44\Diagnostics']
import diag_lib as D
import sim_belt_phys as S
import author_motion as AM

tr = D.load_tracks(D.HERE / 'Tracks/base_tracks.json.gz')
rot = lambda m: m[:3, :3] / np.linalg.norm(m[:3, :3], axis=0)
fing = {D.BI[n] for n in D.NAMES if n.endswith('_l') and n.startswith(('thumb', 'index', 'middle', 'ring'))}
fv = np.where(np.isin(S.skin.dom, list(fing)))[0]
tips = {D.BI[n] for n in ('thumb_03_l', 'index_03_l')}
tv = np.where(np.isin(S.skin.dom[fv], list(tips)))[0]
samples = [(1.68, 'LMG201_Belt_00'), (1.72, 'LMG201_Belt_00'), (4.20, 'New_LMG201_Belt_00'), (4.50, 'New_LMG201_Belt_00'), (4.70, 'New_LMG201_Belt_00')]
data = []
for t, n in samples:
    W = D.worlds(tr, [int(round(t * 120))])[0]
    if n in S.cells:
        V, F = S.cell_world(W, n, S.cells[n]['v']), S.cells[n]['f']
    else:
        V, F = S.new_skin[n].pose(W), S.new_tris[n]
    data.append((t, n, S.skin.pose(W, fv), V, F, rot(W[D.BI['hand_l']])))


def score(delta):
    pen, gap = 0.0, 0.0
    for t, n, P, V, F, Rh in data:
        Vs = V + Rh @ delta
        lo, hi = Vs.min(0) - .3, Vs.max(0) + .3
        m = np.all((P > lo) & (P < hi), 1)
        tree = cKDTree(Vs)
        if m.any():
            w = D.winding_number(P[m], Vs, F)
            ins = np.where(m)[0][w > .5]
            if len(ins):
                pen = max(pen, float(tree.query(P[ins])[0].max()))
        gap = max(gap, float(tree.query(P[tv])[0].min()))
    return pen, gap


base = score(np.zeros(3))
print('current: max finger depth %.2f cm, tip-to-cell gap %.2f cm' % base)
res = []
for a in np.arange(-.4, .81, .2):
    for b in np.arange(-.8, .81, .2):
        for c in np.arange(-.4, .41, .2):
            d = a * AM.F_LOC + b * AM.P_LOC + c * AM.ACROSS
            pen, gap = score(d)
            res.append((pen + max(0, gap - .12) * 3, pen, gap, a, b, c))
res.sort()
for r in res[:6]:
    print('cost %.2f depth %.2f gap %.2f  shift along-finger %.1f palmar %.1f across %.1f' % r)
