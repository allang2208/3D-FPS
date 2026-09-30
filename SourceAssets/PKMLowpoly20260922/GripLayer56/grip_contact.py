"""How far the base hand strays from the base grip (gun space) while the authored family hand is
still on its grip, and how far it is when the family hand has left. Sets the layer weight."""
import json, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from evaluate import HERE, IDLE, FAMS, load, base_key

index = json.loads((HERE / 'inputs.json').read_text())
for gun in sys.argv[1:] or ['PKM', '201']:
    clips = index[gun]['clips']
    cache = {}
    cl = lambda k: cache.setdefault(k, load(clips[k])[0])

    def gripdev(c, ref=None):
        Rw, Pw = c['WPN_root']
        Rg = np.einsum('nji,njk->nik', Rw, c['hand_l'][0])
        pg = np.einsum('nji,nj->ni', Rw, c['hand_l'][1] - Pw)
        if ref is None:
            ref = (Rg[0], pg[0])
        d = np.linalg.norm(pg - ref[1], axis=1)
        a = np.degrees(np.linalg.norm((Rot.from_matrix(np.broadcast_to(ref[0], Rg.shape)).inv() * Rot.from_matrix(Rg)).as_rotvec(), axis=1))
        return d, a, ref
    _, _, gb = gripdev(cl(IDLE[gun][0]))
    for fam in FAMS:
        _, _, gf = gripdev(cl(IDLE[gun][1].format(f=fam)))
        for key in clips:
            if f'/{fam}/' not in key or key.endswith('_idle'):
                continue
            bk, act = base_key(key, fam)
            bd, ba, _ = gripdev(cl(bk), gb)
            fd, fa, _ = gripdev(cl(key), gf)
            on = (fd < 1.0) & (fa < 6.0)
            off = (fd > 5.0) | (fa > 25.0)
            f = lambda x, m: '%5.1f' % x[m].max() if m.any() else '   - '
            g = lambda x, m: '%5.1f' % x[m].min() if m.any() else '   - '
            print('%-4s %-8s %-26s on %3.0f%%: base dev max %s cm %s deg | off %3.0f%%: base dev min %s cm %s deg'
                  % (gun, fam, act, 100 * on.mean(), f(bd, on), f(ba, on), 100 * off.mean(), g(bd, off), g(ba, off)))
