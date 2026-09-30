import sys
import numpy as np
sys.path[:0] = [r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44\Diagnostics']
import diag_lib as D

tr = D.load_tracks(D.HERE / 'Tracks/base_tracks.json.gz')
body = D.Body()
names = ['New_LMG201_Belt_%02d' % k for k in range(6)]
fr = np.arange(int(3.70 * 120), int(4.80 * 120), 2)
W = D.worlds(tr, fr)
cs = {n: D.Skin(body.pos[body.parts[n]], (body.bi[body.parts[n]], body.bw[body.parts[n]])) for n in names}
C = np.array([[cs[n].pose(W[k]).mean(0) for n in names] for k in range(len(fr))])
step = np.linalg.norm(np.diff(C, axis=0), axis=2)
H = W[:, D.BI['hand_l'], :3, 3]
hs = np.linalg.norm(np.diff(H, axis=0), axis=1)
for k in np.argsort(step.max(1))[::-1][:6]:
    print('t=%.3f cell step %s  hand step %.2f  chord gaps %s' % (fr[k] / 120, np.round(step[k], 2), hs[k],
          np.round(np.linalg.norm(np.diff(C[k], axis=0), axis=1), 2)))
print('rest chord gaps', np.round(np.linalg.norm(np.diff(C[0], axis=0), axis=1), 2))
