"""Where do sweater vertices sink into the skin (r442 base)? Dominant bones and the
garment/skin weights of the worst vertices."""
import sys
import numpy as np
from scipy.spatial import cKDTree
sys.path[:0] = [r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44\Diagnostics']
import diag_lib as D

skin = D.load_json_mesh(D.SA / 'ChainmailReloadFit20260929/LMG201_skin.json', 'skin')
if skin is None:
    import diagnose  # noqa
skin_n0 = D.vertex_normals(skin.p, skin.tris)
stree = cKDTree(skin.p)
g = D.load_json_mesh(D.SA / 'FieldSweaterKnit20260929/Authored/LMG201.json', 'sweater')
d, j = stree.query(g.p, distance_upper_bound=4.0)
okg = np.isfinite(d)
h0 = np.full(len(g.p), np.nan)
h0[okg] = np.einsum('ij,ij->i', g.p[okg] - skin.p[j[okg]], skin_n0[j[okg]])
ok = okg & (h0 > .05) & (h0 < 3.0)
names = D.NAMES
for label, f in (('r442', 'Tracks/base_tracks.json.gz'), ('r44', 'Diagnostics/r44_base_prev_tracks.json.gz')):
    p = D.HERE / f
    if not p.exists():
        continue
    tr = D.load_tracks(p)
    for t in (1.10, 5.30):
        W = D.worlds(tr, [int(t * 120)])[0]
        sp = skin.pose(W)
        gp = g.pose(W)
        sn = D.vertex_normals(sp, skin.tris)
        h = np.full(len(g.p), np.nan)
        h[ok] = np.einsum('ij,ij->i', gp[ok] - sp[j[ok]], sn[j[ok]])
        bad = np.where(ok & (h < -.1))[0]
        eye, fw, r, u = D.camera(D.framing_alpha(t))
        ins, _ = D.view_metrics(gp[bad], eye, fw, r, u) if len(bad) else (np.zeros(0, bool), None)
        print(label, 't=%.2f' % t, 'sinking', len(bad), 'max %.2f' % (-np.nanmin(h)), 'in view', int(ins.sum()))
        if len(bad):
            w = bad[np.argsort(h[bad])[:5]]
            for v in w:
                gi, gw = g.idx[v], g.w[v]
                si, sw = skin.idx[j[v]], skin.w[j[v]]
                fmt = lambda I, Wt: ', '.join('%s %.2f' % (names[a], b) for a, b in sorted(zip(I, Wt), key=lambda x: -x[1]) if b > .02)
                print('   h %.2f  garment[%s]  skin[%s]' % (h[v], fmt(gi, gw), fmt(si, sw)))
