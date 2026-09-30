"""Belt49 cells vs the belt cell centroids ClothReload44 was authored against."""
import sys, json
import numpy as np
sys.path[:0] = [r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44', r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44\Diagnostics']
import diag_lib as D

z = np.load(D.HERE / 'Diagnostics/belt49_cells.npz')
pos, cell = z['pos'], z['cell']
idle = json.loads((D.HERE / 'Inputs/201_idle.json').read_text())
W0 = D.worlds({n: np.array([v]) for n, v in zip(D.NAMES, idle['poses'][0])})[0]
body = D.Body()
print('cell  old-centroid(idle)            Belt49-centroid(idle)          delta cm')
for k in range(6):
    n = 'LMG201_Belt_%02d' % k
    i = D.BI[n]
    sel = body.parts[n]
    old = D.Skin(body.pos[sel], (body.bi[sel], body.bw[sel])).pose(W0).mean(0)
    v = pos[cell == n]
    S = W0[i] @ D.REST_INV[i]
    new = (S[:3, :3] @ v.T).T.mean(0) + S[:3, 3]
    print('%d   %s   %s   %.3f   (verts old %d new %d)' % (k, np.round(old, 2), np.round(new, 2), np.linalg.norm(new - old), sel.sum() if sel.dtype == bool else len(sel), len(v)))
